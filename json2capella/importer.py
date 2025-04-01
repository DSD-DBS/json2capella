# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tool for importing JSON data into a Capella data package."""

import collections as c
import html
import json
import pathlib
import typing as t

from capellambse import decl, helpers

from . import datatypes

_AnyJSONType = (
    datatypes.Enum
    | datatypes.EnumLiteral
    | datatypes.Package
    | datatypes.Struct
    | datatypes.StructAttrs
)


class Importer:
    """Class for importing JSON data into a Capella data package."""

    def __init__(self, json_path: pathlib.Path) -> None:
        if json_path.is_dir():
            files = sorted(json_path.rglob("*.json"))
            self.json = datatypes.Package.model_validate(
                {
                    "name": "JSON root package",
                    "subPackages": [
                        json.loads(file.read_text()) for file in files
                    ],
                }
            )
        else:
            self.json = datatypes.Package.model_validate(
                json.loads(json_path.read_text())
            )

        self._promise_ids: c.OrderedDict[str, None] = c.OrderedDict()
        self._promise_id_refs: c.OrderedDict[str, None] = c.OrderedDict()

    def _convert_package(self, pkg: datatypes.Package) -> dict[str, t.Any]:
        associations = []
        classes = []
        for cls in pkg.structs:
            cls_yml, cls_associations = self._convert_class(pkg.prefix, cls)
            classes.append(cls_yml)
            associations.extend(cls_associations)
        enums = [
            self._convert_enum(pkg.prefix, enum_def) for enum_def in pkg.enums
        ]
        packages = []
        for sub_pkg in pkg.sub_packages:
            new_yml = {
                "find": {
                    "name": sub_pkg.name,
                }
            } | self._convert_package(sub_pkg)
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
        self,
        prefix: str,
        cls: datatypes.Struct,
    ) -> tuple[dict, list[dict]]:
        promise_id = f"{prefix}.{cls.name}"
        self._promise_ids[promise_id] = None
        attrs = []
        associations = []
        for attr in cls.attrs:
            attr_yml: dict[str, t.Any] = {
                "description": _get_description(attr),
            }

            attr_yml["kind"] = (
                "ASSOCIATION" if attr.reference is not None else "COMPOSITION"
            )
            if attr.data_type is not None:
                ref = f"datatype.{attr.data_type}"
            elif raw_ref := (
                attr.reference or attr.composition or attr.enum_type
            ):
                if "." in raw_ref:
                    ref = raw_ref
                else:
                    ref = f"{prefix}.{raw_ref}"
            else:
                raise ValueError(
                    "struct attributes need exactly one of dataType, reference, composition or enumType"
                )

            attr_yml["type"] = decl.Promise(ref)
            self._promise_id_refs[ref] = None

            if value_range := attr.range:
                min_val, _, max_val = value_range.partition("..")
                attr_yml["min_value"] = decl.NewObject(
                    "LiteralNumericValue", value=min_val
                )
                attr_yml["max_value"] = decl.NewObject(
                    "LiteralNumericValue", value=max_val
                )

            if not attr.multiplicity:
                min_card = max_card = "1"
            elif ".." in attr.multiplicity:
                min_card, _, max_card = attr.multiplicity.partition("..")
            elif attr.multiplicity == "*":
                min_card = "0"
                max_card = "*"
            else:
                min_card = max_card = attr.multiplicity
            attr_yml["min_card"] = decl.NewObject(
                "LiteralNumericValue", value=min_card
            )
            attr_yml["max_card"] = decl.NewObject(
                "LiteralNumericValue", value=max_card
            )

            attr_promise_id = f"{promise_id}.{attr.name}"
            attrs.append(
                {
                    "promise_id": attr_promise_id,
                    "find": {
                        "name": attr.name,
                    },
                    "set": attr_yml,
                }
            )

            if attr.reference is not None or attr.composition is not None:
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
            "find": {"name": cls.name},
            "set": {
                "description": _get_description(cls),
            },
            "sync": {
                "properties": attrs,
            },
        }
        return yml, associations

    def _convert_enum(self, prefix: str, enum: datatypes.Enum) -> dict:
        promise_id = f"{prefix}.{enum.name}"
        self._promise_ids[promise_id] = None
        literals = []
        for literal in enum.enum_literals:
            literal_yml = {
                "find": {"name": literal.name},
                "set": {
                    "description": _get_description(literal),
                    "value": decl.NewObject(
                        "LiteralNumericValue",
                        value=str(literal.int_id),
                    ),
                },
            }
            literals.append(literal_yml)
        return {
            "promise_id": promise_id,
            "find": {"name": enum.name},
            "set": {
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
        types_parent_uuid: str = "",
        types_uuid: str = "",
    ) -> str:
        """Convert JSON data to decl YAML."""
        instructions = [
            {"parent": decl.UUIDReference(helpers.UUIDString(root_uuid))}
            | self._convert_package(self.json),
        ]
        needed_types = [
            p for p in self._promise_id_refs if p not in self._promise_ids
        ]
        if not needed_types:
            return decl.dump(instructions)

        datatypes = [
            self._convert_datatype(promise_id) for promise_id in needed_types
        ]
        if types_uuid:
            instructions.append(
                {
                    "parent": decl.UUIDReference(
                        helpers.UUIDString(types_uuid)
                    ),
                    "sync": {"datatypes": datatypes},
                }
            )
        else:
            instructions.append(
                {
                    "parent": decl.UUIDReference(
                        helpers.UUIDString(types_parent_uuid)
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


def _get_description(element: _AnyJSONType) -> str:
    description = element.info
    if element.see:
        see = html.escape(element.see)
        description += f"<br><b>see: </b><a href='{see}'>{see}</a>"
    if isinstance(element, datatypes.StructAttrs):
        if element.exp is not None:
            description += f"<br><b>exp: </b>{element.exp}"
        if element.unit is not None:
            description += f"<br><b>unit: </b>{element.unit}"
    return description
