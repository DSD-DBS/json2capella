# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tool for importing JSON data into a Capella data package."""

import json
import pathlib
import re

from capellambse import decl, helpers

VALID_RANGE_PATTERN = re.compile(r"^(-?\d+)\.\.(-?\d+|\*)$")
VALID_CARD_PATTERN = re.compile(r"^(\d+)(?:\.\.(\d+|\*))?$")


class Importer:
    """Class for importing JSON data into a Capella data package."""

    def __init__(self, json_path: pathlib.Path) -> None:
        if json_path.is_dir():
            files = list(json_path.rglob("*.json"))
        else:
            files = [json_path]

        self.json = {
            "subPackages": [json.loads(file.read_text()) for file in files],
        }
        self._promise_ids: set[str] = set()
        self._promise_id_refs: set[str] = set()

    def _convert_package(self, pkg: dict) -> dict:
        associations = []
        classes = []
        for cls in pkg.get("structs", []):
            cls_yml, cls_associations = self._convert_class(pkg["prefix"], cls)
            classes.append(cls_yml)
            associations.extend(cls_associations)
        enums = [
            self._convert_enum(pkg["prefix"], enum_def)
            for enum_def in pkg.get("enums", [])
        ]
        packages = []
        for new_pkg in pkg.get("subPackages", []):
            if any(k not in new_pkg for k in ["prefix", "name"]):
                continue
            new_yml = {
                "find": {
                    "name": new_pkg["name"],
                }
            } | self._convert_package(new_pkg)
            packages.append(new_yml)

        sync = {}
        if classes:
            sync["classes"] = classes
        if enums:
            sync["enumerations"] = enums
        if packages:
            sync["packages"] = packages
        if associations:
            sync["owned_associations"] = associations

        yml: dict = {}
        if desc := _get_description(pkg):
            yml["set"] = {}
            yml["set"]["description"] = desc
        if sync:
            yml["sync"] = sync

        return yml

    def _convert_class(
        self, prefix: str, cls: dict
    ) -> tuple[dict, list[dict]]:
        promise_id = f"{prefix}.{cls['name']}"
        self._promise_ids.add(promise_id)
        attrs = []
        associations = []
        for attr in cls.get("attrs", []):
            attr_promise_id = f"{promise_id}.{attr['name']}"
            attr_yml = {
                "promise_id": attr_promise_id,
                "name": attr["name"],
                "description": _get_description(attr),
            }

            attr_yml["kind"] = (
                "ASSOCIATION" if "reference" in attr else "COMPOSITION"
            )
            match attr:
                case {"dataType": ref}:
                    ref = f"datatype.{ref}"
                case (
                    {"reference": ref}
                    | {"composition": ref}
                    | {"enumType": ref}
                ):
                    if "." not in ref:
                        ref = f"{prefix}.{ref}"

            attr_yml["type"] = decl.Promise(ref)
            self._promise_id_refs.add(ref)

            if "reference" in attr or "composition" in attr:
                associations.append(
                    {
                        "find": {
                            "name": attr_promise_id,
                        },
                        "set": {
                            "navigable_members": [
                                decl.Promise(attr_promise_id)
                            ],
                            "members": [
                                {
                                    "_type": "Property",
                                    "type": decl.Promise(promise_id),
                                    "kind": "ASSOCIATION",
                                    "min_card": decl.NewObject(
                                        "LiteralNumericValue", value="1"
                                    ),
                                    "max_card": decl.NewObject(
                                        "LiteralNumericValue", value="1"
                                    ),
                                }
                            ],
                        },
                    }
                )

            if value_range := attr.get("range"):
                if not (match := VALID_RANGE_PATTERN.match(value_range)):
                    raise ValueError(
                        f"Invalid value range, expected format A..B: {value_range}"
                    )
                min_val, max_val = match.groups()
                attr_yml["min_value"] = decl.NewObject(
                    "LiteralNumericValue", value=min_val
                )
                attr_yml["max_value"] = decl.NewObject(
                    "LiteralNumericValue", value=max_val
                )

            if multiplicity := attr.get("multiplicity"):
                if not (match := VALID_CARD_PATTERN.match(multiplicity)):
                    raise ValueError(
                        f"Invalid multiplicity, expected digits: {multiplicity}"
                    )
                min_card, max_card = match.groups()
                if not max_card:
                    max_card = min_card
            else:
                min_card = max_card = "1"
            attr_yml["min_card"] = decl.NewObject(
                "LiteralNumericValue", value=min_card
            )
            attr_yml["max_card"] = decl.NewObject(
                "LiteralNumericValue", value=max_card
            )
            attrs.append(attr_yml)

        yml = {
            "promise_id": promise_id,
            "find": {"name": cls["name"]},
            "set": {
                "description": _get_description(cls),
                "properties": attrs,
            },
        }
        return yml, associations

    def _convert_enum(self, prefix: str, enum: dict) -> dict:
        promise_id = f"{prefix}.{enum['name']}"
        self._promise_ids.add(promise_id)
        yml = {
            "promise_id": promise_id,
            "find": {"name": enum["name"]},
            "set": {
                "description": _get_description(enum),
                "literals": [
                    {
                        "name": literal["name"],
                        "description": _get_description(literal),
                        "value": decl.NewObject(
                            "LiteralNumericValue",
                            value=str(literal["intId"]),
                        ),
                    }
                    for literal in enum.get("enumLiterals", [])
                ],
            },
        }
        return yml

    def _convert_datatype(self, promise_id: str) -> dict:
        name = promise_id.split(".", 1)[-1]
        if any(t in name for t in ["char", "str"]):
            _type = "StringType"
        elif any(t in name for t in ["bool", "byte"]):
            _type = "BooleanType"
        else:
            _type = "NumericType"
        yml = {
            "promise_id": promise_id,
            "find": {
                "name": name,
                "_type": _type,
            },
        }
        return yml

    def to_yaml(self, layer_data_uuid: str, sa_data_uuid: str) -> str:
        """Convert JSON data to decl YAML."""
        instructions = [
            {"parent": decl.UUIDReference(helpers.UUIDString(layer_data_uuid))}
            | self._convert_package(self.json),
        ]
        if needed_types := self._promise_id_refs - self._promise_ids:
            datatypes = [
                self._convert_datatype(promise_id)
                for promise_id in needed_types
            ]
            instructions.append(
                {
                    "parent": decl.UUIDReference(
                        helpers.UUIDString(sa_data_uuid)
                    ),
                    "sync": {
                        "packages": [
                            {
                                "find": {"name": "Data Types"},
                                "sync": {"datatypes": datatypes},
                            }
                        ],
                    },
                }
            )
        return decl.dump(instructions)


def _get_description(element: dict) -> str:
    description = element.get("info", "")
    if see := element.get("see", ""):
        description += f"<br><b>see: </b><a href='{see}'>{see}</a>"
    if exp := element.get("exp", ""):
        description += f"<br><b>exp: </b>{exp}"
    if unit := element.get("unit", ""):
        description += f"<br><b>unit: </b>{unit}"
    return description
