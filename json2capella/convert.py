# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Convert JSON to Capella data package."""

import logging
import pathlib

import capellambse
import click
from capellambse import decl
from capellambse.model.crosslayer import information

from json2capella import parse, serialize

logger = logging.getLogger(__name__)


class Converter:
    """Convert JSON to Capella data package."""

    def __init__(
        self,
        json_path: pathlib.Path,
        capella_path: str,
        layer: str,
        action: str,
    ):
        self.json = parse.PkgDef("", "", [], [], [])
        if json_path.is_dir():
            for json_file in json_path.rglob("*.json"):
                pkg_def = parse.PkgDef.from_file(json_file)
                self.json.packages.append(pkg_def)
        else:
            pkg_def = parse.PkgDef.from_file(json_path)
            self.json.packages.append(pkg_def)

        self.capella = serialize.CapellaDataPackage(capella_path, layer)
        self.action = action

    def _handle_objects_skip(
        self,
        elem_def_list: list,
        attr_name: str,
        current_root: information.DataPkg,
    ):
        for elem_def in elem_def_list:
            getattr(self.capella, f"create_{attr_name}")(
                elem_def, current_root
            )

    def _handle_objects_replace(
        self,
        elem_def_list: list,
        attr_name: str,
        current_root: information.DataPkg,
    ):
        for elem_def in elem_def_list:
            if elem_obj := getattr(self.capella, f"create_{attr_name}")(
                elem_def, current_root
            ):
                getattr(self.capella, f"remove_{attr_name}")(
                    elem_obj, current_root
                )
                getattr(self.capella, f"create_{attr_name}")(
                    elem_def, current_root
                )

    def _handle_objects_abort(
        self,
        elem_def_list: list,
        attr_name: str,
        current_root: information.DataPkg,
    ):
        for elem_def in elem_def_list:
            if getattr(self.capella, f"create_{attr_name}")(
                elem_def, current_root
            ):
                raise click.Abort()

    def _handle_objects_ask(
        self,
        elem_def_list: list,
        attr_name: str,
        current_root: information.DataPkg,
    ):
        for i, elem_def in enumerate(elem_def_list):
            if elem_obj := getattr(self.capella, f"create_{attr_name}")(
                elem_def, current_root
            ):
                confirm = click.prompt(
                    f"{elem_def.name} already exists. Overwrite? [y]es / [Y]es to all / [n]o / [N]o to all",
                    type=click.Choice(
                        ["y", "Y", "n", "N"],
                        case_sensitive=True,
                    ),
                )
                if confirm == "n":
                    continue
                elif confirm == "N":
                    for elem_def in elem_def_list[(i + 1) :]:
                        getattr(self.capella, f"create_{attr_name}")(
                            elem_def, current_root
                        )
                    self.action = "skip"
                    break
                elif confirm == "y":
                    getattr(self.capella, f"remove_{attr_name}")(
                        elem_obj, current_root
                    )
                    getattr(self.capella, f"create_{attr_name}")(
                        elem_def, current_root
                    )
                elif confirm == "Y":
                    for elem_def in elem_def_list[i:]:
                        if elem_obj := getattr(
                            self.capella, f"create_{attr_name}"
                        )(elem_def, current_root):
                            getattr(self.capella, f"remove_{attr_name}")(
                                elem_obj, current_root
                            )
                            getattr(self.capella, f"create_{attr_name}")(
                                elem_def, current_root
                            )
                    self.action = "replace"
                    break

    def _handle_objects(
        self, current_pkg_def: parse.PkgDef, current_root: information.DataPkg
    ):
        for attr_name in [
            ("package", "packages"),
            ("class", "classes"),
            ("enum", "enums"),
        ]:
            elem_def_list = getattr(current_pkg_def, attr_name[1])
            getattr(self, f"_handle_objects_{self.action}")(
                elem_def_list, attr_name[0], current_root
            )

        for new_pkg_def in current_pkg_def.packages:
            new_root = current_root.packages.by_name(new_pkg_def.name)
            self._handle_objects(new_pkg_def, new_root)

    def _handle_relations(
        self, current_pkg_def: parse.PkgDef, current_root: information.DataPkg
    ):
        for cls_def in current_pkg_def.classes:
            self.capella.create_properties(cls_def, current_root)

        for new_pkg_def in current_pkg_def.packages:
            new_root = current_root.packages.by_name(new_pkg_def.name)
            self._handle_relations(new_pkg_def, new_root)

    def __call__(self):
        """Convert JSON to Capella data package."""
        current_root = self.capella.data_package

        self._handle_objects(self.json, current_root)
        self._handle_relations(self.json, current_root)

        self.capella.save_changes()


def convert_package(pkg: dict) -> tuple[dict, set]:
    new_pkg = {"name": pkg["name"]}
    if info := pkg.get("info"):
        new_pkg["description"] = info

    new_pkg["classes"] = []
    needed_datatypes = set()
    for i in pkg.get("structs", []):
        cls, datatypes = convert_class(pkg["name"], i)
        new_pkg["classes"].append(cls)
        needed_datatypes.update(datatypes)

    new_pkg["enumerations"] = [
        convert_enum(enum) for enum in pkg.get("enums", [])
    ]

    if pkg.get("subPackages"):
        raise NotImplementedError("Subpackages are not supported yet")

    return new_pkg, needed_datatypes


def convert_class(pkgname: str, cls: dict) -> tuple[dict, set[str]]:
    needed_datatypes = set()
    new_cls = {
        "name": cls["name"],
        "description": _get_description(cls),
        "properties": [],
    }

    for attr in cls.get("attrs", []):
        prop = {
            "name": attr["name"],
            "description": _get_description(attr),
        }
        match attr:
            case {"reference": ref} | {"composition": ref} | {"enumType": ref}:
                if "." in ref:
                    prop["type"] = decl.Promise(ref)
                else:
                    prop["type"] = decl.Promise(f"{pkgname}.{ref}")
            case {"dataType": ref}:
                needed_datatypes.add(ref)
                prop["type"] = decl.Promise(f"DataType-{ref}")

        if value_range := attr.get("range"):
            if ".." not in value_range:
                raise ValueError(
                    f"Invalid value range, expected format A..B: {value_range}"
                )
            min_val, max_val = value_range.split("..", 1)
            prop["min_value"] = capellambse.new_object(
                "LiteralNumericValue", value=min_val
            )
            prop["max_value"] = capellambse.new_object(
                "LiteralNumericValue", value=max_val
            )

        if multiplicity := attr.get("multiplicity"):
            if ".." in multiplicity:
                min_val, _, max_val = multiplicity.partition("..")
            else:
                min_val = max_val = multiplicity

            prop["min_card"] = capellambse.new_object(
                "LiteralNumericValue", value=min_val
            )
            prop["max_card"] = capellambse.new_object(
                "LiteralNumericValue", value=max_val
            )

    return new_cls, needed_datatypes


def convert_enum(enum: dict) -> dict:
    new_enum = {
        "name": enum["name"],
        "description": _get_description(enum),
        "literals": [
            {
                "name": i["name"],
                "description": _get_description(i),
                "value": capellambse.new_object(
                    "LiteralNumericValue", str(i["intId"])
                ),
            }
            for i in enum.get("enumLiterals", [])
        ],
    }
    return new_enum


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
