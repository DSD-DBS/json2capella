# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Parse from JSON."""

from __future__ import annotations

import json
import pathlib
import typing as t


class LiteralDef:
    """Literal definition."""

    def __init__(self, name: str, description: str, value: str):
        self.name = name
        self.description = description
        self.value = value


class EnumDef:
    """Enum definition."""

    def __init__(
        self,
        name: str,
        description: str,
        literals: list[LiteralDef],
        parent: str | None = None,
    ):
        self.name = name
        self.description = description
        self.literals = literals
        self.parent = parent


class ClassDef:
    """Class definition."""

    def __init__(
        self,
        name: str,
        description: str,
        properties: list[PropertyDef],
        parent: str | None = None,
    ):
        self.name = name
        self.description = description
        self.properties = properties
        self.parent = parent


class Range(t.NamedTuple):
    """Define range of values."""

    max: str
    min: str


class PropertyDef:
    """Property definition."""

    def __init__(
        self,
        name: str,
        description: str,
        type: ClassDef | EnumDef | str,
        card: Range,
        range: Range | None,
    ):
        self.name = name
        self.description = description
        self.type = type
        self.card = card
        self.range = range


class PkgDef:
    """Package definition."""

    def __init__(
        self,
        name: str,
        description: str,
        enums: list[EnumDef],
        classes: list[ClassDef],
        packages=list["PkgDef"],
    ):
        self.name = name
        self.description = description
        self.enums = enums
        self.classes = classes
        self.packages = packages

    @classmethod
    def from_file(cls, file_path: pathlib.Path):
        """Parse package definition from JSON file."""
        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)
        return cls.from_json(data)

    @classmethod
    def from_json(cls, data: dict):
        """Parse package definition from JSON data."""
        enums = []
        for enum in data.get("enums", []):
            enum_def = EnumDef(
                enum.get("name", ""),
                _get_description(enum),
                _get_literals(enum),
            )
            enums.append(enum_def)

        classes = []
        for class_ in data.get("structs", []):
            class_def = ClassDef(
                class_.get("name", ""),
                _get_description(class_),
                _get_properties(class_),
            )
            classes.append(class_def)

        packages = []
        for package in data.get("subPackages", []):
            packages.append(cls.from_json(package))

        out = cls(
            data.get("name", ""),
            _get_description(data),
            enums,
            classes,
            packages,
        )
        return out


def _get_literals(enum: dict) -> list[LiteralDef]:
    literals = []
    for i, literal in enumerate(enum.get("enumLiterals", [])):
        literal_def = LiteralDef(
            literal.get("name", ""),
            _get_description(literal),
            literal.get("intId", str(i)),
        )
        literals.append(literal_def)
    return literals


def _get_properties(class_: dict) -> list[PropertyDef]:
    properties = []
    for property_ in class_.get("attrs", []):
        if multiplicity := property_.get("multiplicity"):
            card = _get_range(multiplicity)
        else:
            card = Range("1", "1")

        if range_raw := property_.get("range"):
            range = _get_range(range_raw)
        else:
            range = None

        if type_name := property_.get("dataType"):
            type_def = type_name
        else:
            if class_name := (
                property_.get("reference") or property_.get("composition")
            ):
                type_def = ClassDef(
                    class_name,
                    "",
                    [],
                )
            else:
                enum_name = property_.get("enumType")
                type_def = EnumDef(
                    enum_name,
                    "",
                    [],
                )

            if len(ref := type_def.name.split(".")) == 2:
                type_def.parent, type_def.name = ref

        property_def = PropertyDef(
            property_.get("name", ""),
            _get_description(property_),
            type_def,
            card,
            range,
        )
        properties.append(property_def)
    return properties


def _get_description(element: dict) -> str:
    description = f"<p>{element.get('info', '')}</p>"
    if see := element.get("see", ""):
        description += (
            "<p><strong>see: </strong>" f"<a href='{see}'>{see}</a></p>"
        )
    if exp := element.get("exp", ""):
        description += f"<p><strong>exp: </strong>{exp}</p>"
    if unit := element.get("unit", ""):
        description += f"<p><strong>unit: </strong>{unit}</p>"
    return description


def _get_range(range_str: str) -> Range:
    min_value, max_value = range_str.split("..")
    return Range(min_value, max_value)
