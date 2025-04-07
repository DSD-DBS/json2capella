# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re

import pydantic as p


class _BaseModel(p.BaseModel):
    int_id: int | None = p.Field(None, alias="intId")
    name: str
    info: str = ""
    see: str = ""


class Package(_BaseModel):
    sub_packages: list[Package] = p.Field([], alias="subPackages")
    structs: list[Struct] = []
    enums: list[Enum] = []
    prefix: str = p.Field(min_length=1)


class Enum(_BaseModel):
    enum_literals: list[EnumLiteral] = p.Field([], alias="enumLiterals")


class EnumLiteral(_BaseModel):
    int_id: int = p.Field(alias="intId")


class Struct(_BaseModel):
    attrs: list[StructAttrs]


class StructAttrs(_BaseModel):
    data_type: str | None = p.Field(None, alias="dataType")
    reference: str | None = None
    composition: str | None = None
    enum_type: str | None = p.Field(None, alias="enumType")
    unit: str | None = None
    exp: int | None = None

    range: str | None = p.Field(
        None, pattern=re.compile(r"^-?\d+\.\.(-?\d+|\*)$")
    )
    multiplicity: str | None = p.Field(
        None, pattern=re.compile(r"^(?:\d+\.\.)?(\d+|\*)$")
    )
