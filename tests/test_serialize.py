# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0

import pathlib

import pytest

from json2capella import parse, serialize

EXAMPLE_CAPELLA_PATH = pathlib.Path(__file__).parent.joinpath(
    "data/empty_model"
)


@pytest.fixture
def sample_capella_data_package():
    capella_path = EXAMPLE_CAPELLA_PATH.as_posix()
    return serialize.CapellaDataPackage(capella_path, "la")


@pytest.fixture
def sample_class_person():
    return parse.ClassDef(
        "Person",
        "",
        [
            parse.PropertyDef(
                "name",
                "",
                "string",
                parse.Range("1", "1"),
                None,
            ),
            parse.PropertyDef(
                "age",
                "",
                "uint8",
                parse.Range("1", "1"),
                parse.Range("0", "150"),
            ),
            parse.PropertyDef(
                "pet",
                "",
                parse.ClassDef("Pet", "", [], None),
                parse.Range("0", "*"),
                None,
            ),
        ],
    )


@pytest.fixture
def sample_class_pet():
    return parse.ClassDef(
        "Pet",
        "",
        [
            parse.PropertyDef(
                "name",
                "",
                "string",
                parse.Range("1", "1"),
                None,
            ),
            parse.PropertyDef(
                "type",
                "",
                parse.EnumDef(
                    "PetType",
                    "",
                    [
                        parse.LiteralDef("CAT", "", "0"),
                        parse.LiteralDef("DOG", "", "1"),
                    ],
                ),
                parse.Range("1", "1"),
                None,
            ),
        ],
    )


def test_package(sample_capella_data_package):
    pkg_name = "SamplePackage"
    pkg_def = parse.PkgDef(pkg_name, "", [], [], [])
    sample_capella_data_package.create_package(
        pkg_def, sample_capella_data_package.data_package
    )

    pkg_obj = sample_capella_data_package.create_package(
        pkg_def, sample_capella_data_package.data_package
    )

    assert pkg_obj in sample_capella_data_package.data_package.packages
    assert pkg_obj.name == "SamplePackage"

    sample_capella_data_package.remove_package(
        pkg_obj, sample_capella_data_package.data_package
    )

    assert not pkg_obj in sample_capella_data_package.data_package.packages


def _create_person_class(sample_capella_data_package, sample_class_person):
    sample_capella_data_package.create_class(
        sample_class_person, sample_capella_data_package.data_package
    )
    cls_obj = sample_capella_data_package.create_class(
        sample_class_person, sample_capella_data_package.data_package
    )
    return cls_obj


def test_class(sample_capella_data_package, sample_class_person):
    cls_obj = _create_person_class(
        sample_capella_data_package, sample_class_person
    )

    assert cls_obj in sample_capella_data_package.data_package.classes
    assert cls_obj.name == "Person"

    sample_capella_data_package.remove_class(
        cls_obj, sample_capella_data_package.data_package
    )

    assert not cls_obj in sample_capella_data_package.data_package.classes


def _create_pet_type_enum(sample_capella_data_package, sample_class_pet):
    enum_def = sample_class_pet.properties[1].type
    sample_capella_data_package.create_enum(
        enum_def, sample_capella_data_package.data_package
    )
    enum_obj = sample_capella_data_package.create_enum(
        enum_def, sample_capella_data_package.data_package
    )
    return enum_obj


def test_enum(sample_capella_data_package, sample_class_pet):
    enum_obj = _create_pet_type_enum(
        sample_capella_data_package, sample_class_pet
    )

    assert enum_obj in sample_capella_data_package.data_package.datatypes
    assert enum_obj.name == "PetType"
    assert len(enum_obj.literals) == 2
    assert enum_obj.literals[0].name == "CAT"

    sample_capella_data_package.remove_enum(
        enum_obj, sample_capella_data_package.data_package
    )

    assert not enum_obj in sample_capella_data_package.data_package.datatypes


def test_create_properties(
    sample_capella_data_package, sample_class_person, sample_class_pet
):
    _create_pet_type_enum(sample_capella_data_package, sample_class_pet)

    sample_capella_data_package.create_class(
        sample_class_pet, sample_capella_data_package.data_package
    )
    sample_capella_data_package.create_properties(
        sample_class_pet, sample_capella_data_package.data_package
    )

    cls_obj = _create_person_class(
        sample_capella_data_package, sample_class_person
    )

    sample_capella_data_package.create_properties(
        sample_class_person, sample_capella_data_package.data_package
    )

    assert len(cls_obj.properties) == 3

    sample_capella_data_package.remove_class(
        cls_obj, sample_capella_data_package.data_package
    )

    assert not cls_obj in sample_capella_data_package.data_package.classes
