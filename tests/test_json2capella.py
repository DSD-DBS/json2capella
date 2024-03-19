# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0

import pathlib

import pytest
from capellambse import decl, helpers

from json2capella.importer import Importer, _get_description

PATH = pathlib.Path(__file__).parent

SAMPLE_PACKAGE_PATH = PATH.joinpath("data/example_jsons")
SAMPLE_PACKAGE_YAML = PATH.joinpath("data/example_jsons.yaml")
DUMMY_PATH = PATH.joinpath("data/empty_project_60")

ROOT = helpers.UUIDString("00000000-0000-0000-0000-000000000000")
SA_ROOT = helpers.UUIDString("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def importer():
    return Importer(DUMMY_PATH)


class TestDescription:
    @staticmethod
    def test_get_description():
        element = {
            "intId": 0,
            "name": "my_attr",
            "dataType": "int32",
            "info": "This is my_attr info.",
        }
        expected = "This is my_attr info."
        actual = _get_description(element)

        assert actual == expected

    @staticmethod
    def test_get_description_extra_info():
        element = {
            "intId": 0,
            "name": "my_attr",
            "dataType": "int32",
            "see": "http://dummy.url",
            "unit": "m",
            "exp": -3,
            "info": "This is my_attr info.",
        }
        expected = (
            "This is my_attr info."
            "<br><b>see: </b><a href='http://dummy.url'>http://dummy.url</a>"
            "<br><b>exp: </b>-3"
            "<br><b>unit: </b>m"
        )
        actual = _get_description(element)

        assert actual == expected

    @staticmethod
    def test_get_description_no_info():
        element = {
            "intId": 0,
            "name": "my_attr",
            "dataType": "int32",
            "unit": "m",
            "exp": -3,
        }
        expected = "<br><b>exp: </b>-3<br><b>unit: </b>m"
        actual = _get_description(element)

        assert actual == expected


def test_convert_datatype(importer):
    promise_id = "datatype.uint8"

    expected = {
        "promise_id": "datatype.uint8",
        "find": {
            "name": "uint8",
            "_type": "NumericType",
        },
    }
    actual = importer._convert_datatype(promise_id)

    assert decl.dump([actual]) == decl.dump([expected])


def test_convert_enum(importer):
    data = {
        "name": "MyEnum",
        "info": "This is MyEnum info.",
        "enumLiterals": [
            {"intId": 0, "name": "enumLiteral0"},
            {"intId": 1, "name": "enumLiteral1"},
            {"intId": 2, "name": "enumLiteral2"},
        ],
    }

    expected = {
        "promise_id": "my_package.MyEnum",
        "find": {
            "name": "MyEnum",
        },
        "set": {
            "description": "This is MyEnum info.",
            "literals": [
                {
                    "name": "enumLiteral0",
                    "description": "",
                    "value": decl.NewObject("LiteralNumericValue", value="0"),
                },
                {
                    "name": "enumLiteral1",
                    "description": "",
                    "value": decl.NewObject("LiteralNumericValue", value="1"),
                },
                {
                    "name": "enumLiteral2",
                    "description": "",
                    "value": decl.NewObject("LiteralNumericValue", value="2"),
                },
            ],
        },
    }
    actual = importer._convert_enum("my_package", data)

    assert decl.dump([actual]) == decl.dump([expected])
    assert {"my_package.MyEnum"} == importer._promise_ids


class TestClass:
    @staticmethod
    def test_convert_class(importer):
        data = {
            "name": "MyClass",
            "info": "This is MyClass info.",
            "attrs": [
                {
                    "intId": 1,
                    "name": "attr1",
                    "dataType": "uint8",
                    "info": "This is attr1 info.",
                },
            ],
        }

        expected = {
            "promise_id": "my_package.MyClass",
            "find": {
                "name": "MyClass",
            },
            "set": {
                "description": "This is MyClass info.",
                "properties": [
                    {
                        "promise_id": "my_package.MyClass.attr1",
                        "name": "attr1",
                        "description": "This is attr1 info.",
                        "kind": "COMPOSITION",
                        "type": decl.Promise("datatype.uint8"),
                        "min_card": decl.NewObject(
                            "LiteralNumericValue", value="1"
                        ),
                        "max_card": decl.NewObject(
                            "LiteralNumericValue", value="1"
                        ),
                    },
                ],
            },
        }
        actual, associations = importer._convert_class("my_package", data)

        assert decl.dump([actual]) == decl.dump([expected])
        assert {"my_package.MyClass"} == importer._promise_ids
        assert {"datatype.uint8"} == importer._promise_id_refs
        assert not associations

    @staticmethod
    def test_convert_class_with_range_and_multiplicity(importer):
        data = {
            "name": "MyClass",
            "info": "This is MyClass info.",
            "attrs": [
                {
                    "intId": 1,
                    "name": "attr1",
                    "dataType": "uint8",
                    "info": "This is attr1 info.",
                    "multiplicity": "0..*",
                    "range": "0..255",
                },
                {
                    "intId": 2,
                    "name": "attr2",
                    "dataType": "uint8",
                    "info": "This is attr2 info.",
                    "multiplicity": "2",
                },
            ],
        }

        expected = {
            "promise_id": "my_package.MyClass",
            "find": {
                "name": "MyClass",
            },
            "set": {
                "description": "This is MyClass info.",
                "properties": [
                    {
                        "promise_id": "my_package.MyClass.attr1",
                        "name": "attr1",
                        "description": "This is attr1 info.",
                        "kind": "COMPOSITION",
                        "type": decl.Promise("datatype.uint8"),
                        "min_value": decl.NewObject(
                            "LiteralNumericValue", value="0"
                        ),
                        "max_value": decl.NewObject(
                            "LiteralNumericValue", value="255"
                        ),
                        "min_card": decl.NewObject(
                            "LiteralNumericValue", value="0"
                        ),
                        "max_card": decl.NewObject(
                            "LiteralNumericValue", value="*"
                        ),
                    },
                    {
                        "promise_id": "my_package.MyClass.attr2",
                        "name": "attr2",
                        "description": "This is attr2 info.",
                        "kind": "COMPOSITION",
                        "type": decl.Promise("datatype.uint8"),
                        "min_card": decl.NewObject(
                            "LiteralNumericValue", value="2"
                        ),
                        "max_card": decl.NewObject(
                            "LiteralNumericValue", value="2"
                        ),
                    },
                ],
            },
        }
        actual, associations = importer._convert_class("my_package", data)

        assert decl.dump([actual]) == decl.dump([expected])
        assert {"my_package.MyClass"} == importer._promise_ids
        assert {"datatype.uint8"} == importer._promise_id_refs
        assert not associations

    @staticmethod
    def test_convert_class_with_composition(importer):
        data = {
            "name": "MyClass",
            "info": "This is MyClass info.",
            "attrs": [
                {
                    "intId": 1,
                    "name": "attr1",
                    "composition": "MyOtherClass",
                    "info": "This is attr1 info.",
                },
            ],
        }
        expected_yml = {
            "promise_id": "my_package.MyClass",
            "find": {
                "name": "MyClass",
            },
            "set": {
                "description": "This is MyClass info.",
                "properties": [
                    {
                        "promise_id": "my_package.MyClass.attr1",
                        "name": "attr1",
                        "kind": "COMPOSITION",
                        "type": decl.Promise("my_package.MyOtherClass"),
                        "description": "This is attr1 info.",
                        "min_card": decl.NewObject(
                            "LiteralNumericValue", value="1"
                        ),
                        "max_card": decl.NewObject(
                            "LiteralNumericValue", value="1"
                        ),
                    },
                ],
            },
        }

        expected_associations = [
            {
                "find": {
                    "name": "my_package.MyClass.attr1",
                },
                "set": {
                    "navigable_members": [
                        decl.Promise("my_package.MyClass.attr1")
                    ],
                    "members": [
                        {
                            "_type": "Property",
                            "type": decl.Promise("my_package.MyClass"),
                            "kind": "ASSOCIATION",
                            "min_card": decl.NewObject(
                                "LiteralNumericValue", value="1"
                            ),
                            "max_card": decl.NewObject(
                                "LiteralNumericValue", value="1"
                            ),
                        }
                    ],
                },
            }
        ]

        actual_yml, actual_associations = importer._convert_class(
            "my_package", data
        )
        assert decl.dump([actual_yml]) == decl.dump([expected_yml])
        assert {"my_package.MyClass"} == importer._promise_ids
        assert {"my_package.MyOtherClass"} == importer._promise_id_refs
        assert decl.dump(actual_associations) == decl.dump(
            expected_associations
        )

    @staticmethod
    def test_convert_class_with_reference(importer):
        data = {
            "name": "MyClass",
            "info": "This is MyClass info.",
            "attrs": [
                {
                    "intId": 1,
                    "name": "attr1",
                    "reference": "MyOtherClass",
                    "info": "This is attr1 info.",
                },
            ],
        }
        expected_yml = {
            "promise_id": "my_package.MyClass",
            "find": {
                "name": "MyClass",
            },
            "set": {
                "description": "This is MyClass info.",
                "properties": [
                    {
                        "promise_id": "my_package.MyClass.attr1",
                        "name": "attr1",
                        "kind": "ASSOCIATION",
                        "type": decl.Promise("my_package.MyOtherClass"),
                        "description": "This is attr1 info.",
                        "min_card": decl.NewObject(
                            "LiteralNumericValue", value="1"
                        ),
                        "max_card": decl.NewObject(
                            "LiteralNumericValue", value="1"
                        ),
                    },
                ],
            },
        }

        expected_associations = [
            {
                "find": {
                    "name": "my_package.MyClass.attr1",
                },
                "set": {
                    "navigable_members": [
                        decl.Promise("my_package.MyClass.attr1")
                    ],
                    "members": [
                        {
                            "_type": "Property",
                            "type": decl.Promise("my_package.MyClass"),
                            "kind": "ASSOCIATION",
                            "min_card": decl.NewObject(
                                "LiteralNumericValue", value="1"
                            ),
                            "max_card": decl.NewObject(
                                "LiteralNumericValue", value="1"
                            ),
                        }
                    ],
                },
            }
        ]

        actual_yml, actual_associations = importer._convert_class(
            "my_package", data
        )
        assert decl.dump([actual_yml]) == decl.dump([expected_yml])
        assert {"my_package.MyClass"} == importer._promise_ids
        assert {"my_package.MyOtherClass"} == importer._promise_id_refs
        assert decl.dump(actual_associations) == decl.dump(
            expected_associations
        )

    @staticmethod
    def test_convert_class_with_enumType(importer):
        data = {
            "name": "MyClass",
            "info": "This is MyClass info.",
            "attrs": [
                {
                    "intId": 1,
                    "name": "attr1",
                    "enumType": "MyEnum",
                    "info": "This is attr1 info.",
                },
            ],
        }
        expected = {
            "promise_id": "my_package.MyClass",
            "find": {
                "name": "MyClass",
            },
            "set": {
                "description": "This is MyClass info.",
                "properties": [
                    {
                        "promise_id": "my_package.MyClass.attr1",
                        "name": "attr1",
                        "kind": "COMPOSITION",
                        "type": decl.Promise("my_package.MyEnum"),
                        "description": "This is attr1 info.",
                        "min_card": decl.NewObject(
                            "LiteralNumericValue", value="1"
                        ),
                        "max_card": decl.NewObject(
                            "LiteralNumericValue", value="1"
                        ),
                    },
                ],
            },
        }

        actual, associations = importer._convert_class("my_package", data)

        assert decl.dump([actual]) == decl.dump([expected])
        assert {"my_package.MyClass"} == importer._promise_ids
        assert {"my_package.MyEnum"} == importer._promise_id_refs
        assert not associations


def test_convert_package(importer):
    expected = decl.dump(decl.load(SAMPLE_PACKAGE_YAML))
    actual = Importer(SAMPLE_PACKAGE_PATH).to_yaml(ROOT, SA_ROOT)

    assert actual == expected
