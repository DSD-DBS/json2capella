# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Parse from JSON."""

from __future__ import annotations

import json


class LiteralDef:
    """Literal definition."""

    def __init__(self, name: str, description: str, value: int):
        self.name = name
        self.description = description
        self.value = value


class EnumDef:
    """Enum definition."""

    def __init__(
        self, name: str, description: str, literals: list[LiteralDef]
    ):
        self.name = name
        self.description = description
        self.literals = literals


class ClassDef:
    """Class definition."""

    def __init__(
        self, name: str, description: str, properties: list[PropertyDef]
    ):
        self.name = name
        self.description = description
        self.properties = properties


class PropertyDef:
    """Property definition."""

    def __init__(
        self,
        name: str,
        description: str,
        type: ClassDef | EnumDef | str,
        min_card: str,
        max_card: str,
        min_value: str | None,
        max_value: str | None,
    ):
        self.name = name
        self.description = description
        self.type = type
        self.min_card = min_card
        self.max_card = max_card
        self.min_value = min_value
        self.max_value = max_value


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
    def from_file(cls, file_path: str):
        """Parse package definition from JSON file."""
        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)

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
                else:
                    min_card, max_card = "1", "1"

                range = property_.get("range")
                if range:
                    min_value, max_value = range.split("..")
                else:
                    min_value, max_value = None, None

                property_def = PropertyDef(
                    property_.get("name", ""),
                    property_.get("info", ""),
                    "",
                    min_card,
                    max_card,
                    min_value,
                    max_value,
                )
                if class_name := (
                    property_.get("reference") or property_.get("composition")
                ):
                    property_def.type = ClassDef(
                        class_name,
                        "",
                        [],
                    )
                elif enum_name := property_.get("enumType"):
                    property_def.type = EnumDef(
                        enum_name,
                        "",
                        [],
                    )
                else:
                    property_def.type = property_.get("dataType")

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
