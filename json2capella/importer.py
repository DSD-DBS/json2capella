# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tool for importing JSON data into a Capella data package."""

import collections as c
import json
import pathlib
import re
import typing as t

from capellambse import decl, helpers

VALID_RANGE_PATTERN = re.compile(r"^(-?\d+)\.\.(-?\d+|\*)$")
VALID_CARD_PATTERN = re.compile(r"^(\d+)(?:\.\.(\d+|\*))?$")


def get_json_from_path(json_path: pathlib.Path) -> dict[str, t.Any]:
    """Get JSON data from a file or folder."""
    if json_path.is_dir():
        files = sorted(json_path.rglob("*.json"))
        return {
            "subPackages": [json.loads(file.read_text()) for file in files],
        }
    return json.loads(json_path.read_text())


def get_old_by_id(
    old_jsons: list[dict[str, t.Any]], int_id: int
) -> dict[str, t.Any] | None:
    """Get an element from the old JSON data by its intId."""
    return next(
        (old_json for old_json in old_jsons if old_json["intId"] == int_id),
        None,
    )


def get_name(
    element: dict[str, t.Any], old_element: dict[str, t.Any] | None
) -> str:
    """Get the name of an element."""
    if old_element:
        return old_element["name"]
    return element["name"]


class Importer:
    """Class for importing JSON data into a Capella data package."""

    def __init__(
        self,
        json_path: pathlib.Path,
        old_json_path: pathlib.Path | None = None,
    ) -> None:
        self.json = get_json_from_path(json_path)
        self.old_json = (
            get_json_from_path(old_json_path) if old_json_path else None
        )
        self._promise_ids: c.OrderedDict[str, None] = c.OrderedDict()
        self._promise_id_refs: c.OrderedDict[str, None] = c.OrderedDict()

    def _convert_package(
        self, pkg: dict[str, t.Any], old_pkg: dict[str, t.Any] | None = None
    ) -> dict[str, t.Any]:
        if old_pkg is None:
            old_pkg = {}
        associations = []
        classes = []
        for cls in pkg.get("structs", []):
            old_cls = get_old_by_id(old_pkg.get("structs", []), cls["intId"])
            cls_yml, cls_associations = self._convert_class(
                pkg["prefix"], cls, old_cls
            )
            classes.append(cls_yml)
            associations.extend(cls_associations)
        enums = []
        for enum_def in pkg.get("enums", []):
            old_enum = get_old_by_id(
                old_pkg.get("enums", []), enum_def["intId"]
            )
            enums.append(self._convert_enum(pkg["prefix"], enum_def, old_enum))
        packages = []
        for sub_pkg in pkg.get("subPackages", []):
            if any(k not in sub_pkg for k in ["prefix", "name", "intId"]):
                continue
            old_sub_pkg = get_old_by_id(
                old_pkg.get("subPackages", []), sub_pkg["intId"]
            )
            new_yml = {
                "find": {
                    "name": get_name(sub_pkg, old_sub_pkg),
                }
            } | self._convert_package(sub_pkg, old_sub_pkg)
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

        return {
            "set": {
                "name": get_name(pkg, old_pkg),
                "description": _get_description(pkg),
            },
            "sync": sync,
        }

    def _convert_class(
        self, prefix: str, cls: dict, old_cls: dict | None = None
    ) -> tuple[dict, list[dict]]:
        if old_cls is None:
            old_cls = {}
        promise_id = f"{prefix}.{cls['name']}"
        self._promise_ids[promise_id] = None
        attrs = []
        associations = []
        for attr in cls.get("attrs", []):
            attr_yml: dict[str, t.Any] = {
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
            self._promise_id_refs[ref] = None

            if value_range := attr.get("range"):
                if not (match := VALID_RANGE_PATTERN.match(value_range)):
                    raise ValueError(
                        "Invalid value range, "
                        f"expected format A..B: {value_range}"
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
                        "Invalid multiplicity, "
                        f"expected digits: {multiplicity}"
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

            attr_promise_id = f"{promise_id}.{attr['name']}"
            old_attr = get_old_by_id(old_cls.get("attrs", []), attr["intId"])
            attrs.append(
                {
                    "promise_id": attr_promise_id,
                    "find": {
                        "name": get_name(attr, old_attr),
                    },
                    "set": attr_yml,
                }
            )

            if "reference" in attr or "composition" in attr:
                associations.append(
                    {
                        "find": {
                            "navigable_members": [
                                decl.Promise(attr_promise_id)
                            ],
                        },
                        "sync": {
                            "members": [
                                {
                                    "find": {
                                        "type": decl.Promise(promise_id),
                                    },
                                    "set": {
                                        "_type": "Property",
                                        "kind": "ASSOCIATION",
                                        "min_card": decl.NewObject(
                                            "LiteralNumericValue", value="1"
                                        ),
                                        "max_card": decl.NewObject(
                                            "LiteralNumericValue", value="1"
                                        ),
                                    },
                                }
                            ],
                        },
                    }
                )

        yml = {
            "promise_id": promise_id,
            "find": {"name": get_name(cls, old_cls)},
            "set": {
                "name": cls["name"],
                "description": _get_description(cls),
            },
            "sync": {
                "properties": attrs,
            },
        }
        return yml, associations

    def _convert_enum(
        self, prefix: str, enum: dict, old_enum: dict | None = None
    ) -> dict:
        if old_enum is None:
            old_enum = {}
        promise_id = f"{prefix}.{enum['name']}"
        self._promise_ids[promise_id] = None
        literals = []
        for literal in enum.get("enumLiterals", []):
            old_literal = get_old_by_id(
                old_enum.get("enumLiterals", []), literal["intId"]
            )
            literal_yml = {
                "find": {"name": get_name(literal, old_literal)},
                "set": {
                    "name": literal["name"],
                    "description": _get_description(literal),
                    "value": decl.NewObject(
                        "LiteralNumericValue",
                        value=str(literal["intId"]),
                    ),
                },
            }
            literals.append(literal_yml)
        return {
            "promise_id": promise_id,
            "find": {"name": get_name(enum, old_enum)},
            "set": {
                "name": enum["name"],
                "description": _get_description(enum),
            },
            "sync": {
                "literals": literals,
            },
        }

    def _convert_datatype(self, promise_id: str) -> dict:
        name = promise_id.split(".", 1)[-1]
        if any(t in name for t in ["char", "str"]):
            _type = "StringType"
        elif any(t in name for t in ["bool", "byte"]):
            _type = "BooleanType"
        else:
            _type = "NumericType"
        return {
            "promise_id": promise_id,
            "find": {
                "name": name,
                "_type": _type,
            },
        }

    def to_yaml(
        self,
        root_uuid: str,
        *,
        types_uuid: str = "",
        is_layer: bool = False,
    ) -> str:
        """Convert JSON data to decl YAML."""
        instructions = [
            {"parent": decl.UUIDReference(helpers.UUIDString(root_uuid))}
            | self._convert_package(self.json, self.old_json)
        ]
        needed_types = [
            p for p in self._promise_id_refs if p not in self._promise_ids
        ]
        if not needed_types:
            return decl.dump(instructions)

        datatypes = [
            self._convert_datatype(promise_id) for promise_id in needed_types
        ]

        types_yaml: dict[str, t.Any] = {
            "parent": decl.UUIDReference(helpers.UUIDString(types_uuid)),
        }

        if is_layer:
            types_yaml["sync"] = {
                "packages": [
                    {
                        "find": {"name": "Data Types"},
                        "sync": {"datatypes": datatypes},
                    }
                ]
            }
        else:
            types_yaml["sync"] = {"datatypes": datatypes}

        instructions.append(types_yaml)
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
