# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0

import json
import pathlib

import pytest

from json2capella import parse

EXAMPLE_JSON_PATH = pathlib.Path(__file__).parent.joinpath("data/example.json")


@pytest.fixture
def sample_json_data():
    with open(EXAMPLE_JSON_PATH, encoding="utf-8") as file:
        data = json.load(file)
    return data


def test_parse_pkgdef_from_file():
    pkg_def = parse.PkgDef.from_file(EXAMPLE_JSON_PATH)

    assert pkg_def.name == "SamplePackage"
    assert pkg_def.description == "Sample package description"


def test_parse_pkgdef_from_json(sample_json_data):
    pkg_def = parse.PkgDef.from_json(sample_json_data)

    assert pkg_def.name == "SamplePackage"
    assert pkg_def.description == "Sample package description"

    assert len(pkg_def.enums) == 1
    assert isinstance(pkg_def.enums[0], parse.EnumDef)
    assert pkg_def.enums[0].name == "PetType"
    assert len(pkg_def.enums[0].literals) == 4
    assert isinstance(pkg_def.enums[0].literals[0], parse.LiteralDef)

    assert len(pkg_def.classes) == 3
    assert isinstance(pkg_def.classes[0], parse.ClassDef)
    assert pkg_def.classes[0].name == "Person"
    assert len(pkg_def.classes[0].properties) == 3
    assert isinstance(pkg_def.classes[0].properties[0], parse.PropertyDef)

    assert len(pkg_def.packages) == 1
    assert isinstance(pkg_def.packages[0], parse.PkgDef)
    assert pkg_def.packages[0].name == "SubPackage1"
