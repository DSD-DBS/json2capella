# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Parse from JSON."""

from __future__ import annotations

import json
import pathlib
import typing as t


class LiteralDef:
    """Literal definition."""

    def __init__(self, name: str, description: str, value: int):
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
        card: Cardinality,
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
        data = json.loads(file_path.read_text())
        return cls.from_json(data)

    @classmethod
    def from_json(cls, data: dict):
        """Parse package definition from JSON data."""
        enums = []
        for enum in data.get("enums", []):
            literals = []
            for i, literal in enumerate(enum.get("enumLiterals", [])):
                literal_def = LiteralDef(
                    literal.get("name", ""),
                    literal.get("info", ""),
                    literal.get("intId", i),
                )
                literals.append(literal_def)
            enum_def = EnumDef(
                enum.get("name", ""),
                enum.get("info", ""),
                literals,
            )
            enums.append(enum_def)

        classes = []
        for class_ in data.get("structs", []):
            properties = []
            for property_ in class_.get("attrs", []):
                multiplicity = property_.get("multiplicity")
                if multiplicity:
                    min_card, max_card = multiplicity.split("..")
                    card = Range(min_card, max_card)
                else:
                    card = Range("1", "1")

                if range_raw := property_.get("range"):
                    min_value, max_value = range_raw.split("..")
                    range = Range(min_value, max_value)
                else:
                    range = None

                property_def = PropertyDef(
                    property_.get("name", ""),
                    property_.get("info", ""),
                    "",
                    card,
                    range,
                )

                if type_name := property_.get("dataType"):
                    property_def.type = type_name
                else:
                    if class_name := (
                        property_.get("reference")
                        or property_.get("composition")
                    ):
                        property_def.type = ClassDef(
                            class_name,
                            "",
                            [],
                        )
                    else:
                        enum_name = property_.get("enumType")
                        property_def.type = EnumDef(
                            enum_name,
                            "",
                            [],
                        )

                    if len(ref := property_def.type.name.split(".")) == 2:
                        property_def.type.parent, property_def.type.name = ref

                properties.append(property_def)
            class_def = ClassDef(
                class_.get("name", ""),
                class_.get("info", ""),
                properties,
            )
            classes.append(class_def)

        packages = []
        for package in data.get("subPackages", []):
            packages.append(cls.from_json(package))

        out = cls(
            data.get("name", ""),
            data.get("info", ""),
            enums,
            classes,
            packages,
        )
        return out
