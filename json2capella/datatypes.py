# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import typing as t

import pydantic as p


class _BaseModel(p.BaseModel):
    int_id: t.Annotated[int | None, p.Field(alias="intId")] = None
    name: str
    info: str = ""
    see: str = ""


class Package(_BaseModel):
    sub_packages: t.Annotated[list[Package], p.Field(alias="subPackages")] = []
    structs: list[Struct] = []
    enums: list[Enum] = []
    prefix: t.Annotated[str, p.Field(min_length=1)]


class Enum(_BaseModel):
    enum_literals: t.Annotated[
        list[EnumLiteral], p.Field(alias="enumLiterals")
    ] = []


class EnumLiteral(_BaseModel):
    int_id: t.Annotated[int, p.Field(alias="intId")]


class Struct(_BaseModel):
    extends: str | None = None
    attrs: list[StructAttrs] = []

    @p.field_validator("extends")
    @classmethod
    def extends_is_valid_dotted_name(cls, value: str) -> str:
        numdots = sum(1 for char in value if char == ".")
        if numdots not in (0, 1):
            raise ValueError(
                "Invalid extends, expected 'Class' or 'prefix.Class':"
                f" {value!r}"
            )
        if value.startswith(".") or value.endswith("."):
            raise ValueError("'extends' value cannot start or end with '.'")
        return value


class StructAttrs(_BaseModel):
    data_type: t.Annotated[str | None, p.Field(alias="dataType")] = None
    reference: str | None = None
    composition: str | None = None
    enum_type: t.Annotated[str | None, p.Field(alias="enumType")] = None
    unit: str | None = None
    exp: int | None = None

    range: t.Annotated[
        str | None, p.Field(pattern=r"^-?\d+\.\.(-?\d+|\*)$")
    ] = None
    multiplicity: t.Annotated[
        str | None, p.Field(pattern=r"^(?:\d+\.\.)?(\d+|\*)$")
    ] = None
