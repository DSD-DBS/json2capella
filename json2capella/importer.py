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
T = t.TypeVar("T", bound=_AnyJSONType)


def load_json(json_path: pathlib.Path) -> datatypes.Package:
    """Load JSON data from a file or folder."""
    if json_path.is_dir():
        files = sorted(json_path.rglob("*.json"))
        return datatypes.Package.model_validate(
            {
                "name": "JSON root package",
                "prefix": "json_root_package",
                "subPackages": [
                    json.loads(file.read_text()) for file in files
                ],
            }
        )
    return datatypes.Package.model_validate(json.loads(json_path.read_text()))


def get_old_by_id(old_jsons: list[T], int_id: int | None) -> T | None:
    """Get an element from the old JSON data by its intId."""
    if int_id is None:
        return None
    return next(
        (old_json for old_json in old_jsons if old_json.int_id == int_id),
        None,
    )


def get_name(element: T, old_element: T | None) -> str:
    """Get the name of an element."""
    if old_element:
        return old_element.name
    return element.name


class Importer:
    """Class for importing JSON data into a Capella data package."""

    def __init__(
        self,
        json_path: pathlib.Path,
        old_json_path: pathlib.Path | None = None,
    ) -> None:
        self.json = load_json(json_path)
        self.old_json = load_json(old_json_path) if old_json_path else None
        self._promise_ids: c.OrderedDict[str, None] = c.OrderedDict()
        self._promise_id_refs: c.OrderedDict[str, None] = c.OrderedDict()

    def _convert_package(
        self, pkg: datatypes.Package, old_pkg: datatypes.Package | None = None
    ) -> dict[str, t.Any]:
        if old_pkg is None:
            old_pkg = datatypes.Package(
                name=pkg.name, prefix=pkg.prefix, int_id=pkg.int_id
            )
        associations = []
        classes = []
        for cls in pkg.structs:
            old_cls = get_old_by_id(old_pkg.structs, cls.int_id)
            cls_yml, cls_associations = self._convert_class(
                pkg.prefix, cls, old_cls
            )
            classes.append(cls_yml)
            associations.extend(cls_associations)
        enums = []
        for enum_def in pkg.enums:
            old_enum = get_old_by_id(old_pkg.enums, enum_def.int_id)
            enums.append(self._convert_enum(pkg.prefix, enum_def, old_enum))
        packages = []
        for sub_pkg in pkg.sub_packages:
            old_sub_pkg = get_old_by_id(old_pkg.sub_packages, sub_pkg.int_id)
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

        result: dict[str, t.Any] = {"sync": sync}
        if desc := _get_description(pkg):
            result.setdefault("set", {})["description"] = desc
        if pkg is not self.json:
            result.setdefault("set", {})["name"] = get_name(pkg, old_pkg)
        return result

    def _convert_class(
        self,
        prefix: str,
        cls: datatypes.Struct,
        old_cls: datatypes.Struct | None = None,
    ) -> tuple[dict, list[dict]]:
        if old_cls is None:
            old_cls = datatypes.Struct(name=cls.name, int_id=cls.int_id)
        promise_id = f"{prefix}.{cls.name}"
        self._promise_ids[promise_id] = None
        attrs = []
        associations = []
        for attr in cls.attrs:
            attr_yml: dict[str, t.Any] = {
                "name": attr.name,
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
            old_attr = get_old_by_id(old_cls.attrs, attr.int_id)
            attrs.append(
                {
                    "promise_id": attr_promise_id,
                    "find": {
                        "name": get_name(attr, old_attr),
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

        yml: t.Any = {
            "promise_id": promise_id,
            "find": {"name": get_name(cls, old_cls)},
            "set": {
                "name": cls.name,
                "description": _get_description(cls),
            },
            "sync": {
                "owned_properties": attrs,
            },
        }

        if cls.extends:
            if "." not in cls.extends:
                yml["set"]["super"] = decl.Promise(f"{prefix}.{cls.extends}")
            else:
                yml["set"]["super"] = decl.Promise(cls.extends)

        return yml, associations

    def _convert_enum(
        self,
        prefix: str,
        enum: datatypes.Enum,
        old_enum: datatypes.Enum | None = None,
    ) -> dict:
        promise_id = f"{prefix}.{enum.name}"
        self._promise_ids[promise_id] = None
        literals = []
        for literal in enum.enum_literals:
            old_literal = (
                get_old_by_id(old_enum.enum_literals, literal.int_id)
                if old_enum is not None
                else None
            )
            literal_yml = {
                "find": {"name": get_name(literal, old_literal)},
                "set": {
                    "name": literal.name,
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
            "find": {"name": get_name(enum, old_enum)},
            "set": {
                "name": enum.name,
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
        types_parent_uuid: str = "",
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
        if types_uuid:
            types_yaml: dict[str, t.Any] = {
                "parent": decl.UUIDReference(helpers.UUIDString(types_uuid)),
            }
        else:
            types_yaml = {"parent": decl.Promise("types-package")}
            instructions.append(
                {
                    "parent": decl.UUIDReference(
                        helpers.UUIDString(types_parent_uuid)
                    ),
                    "sync": {
                        "packages": [
                            {
                                "find": {"name": "Data Types"},
                                "promise_id": "types-package",
                            }
                        ],
                    },
                }
            )

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
