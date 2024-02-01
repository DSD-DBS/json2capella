# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Convert JSON to Capella data package."""

import logging
import pathlib

import click
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
