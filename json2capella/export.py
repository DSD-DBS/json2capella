# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""The json2capella exporter CLI, i.e. capella2json."""

from __future__ import annotations

import logging
import typing as t

import capellambse
import click
from capellambse import cli_helpers
from capellambse.metamodel import information

from . import datatypes

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "-m",
    "--model",
    required=True,
    type=cli_helpers.ModelCLI(),
    help="Path to the Capella model.",
)
@click.option(
    "-p",
    "--package",
    "package_id",
    help="ID or name of the DataPkg to export.",
)
@click.option(
    "-l",
    "--list",
    "list_packages",
    is_flag=True,
    help="List all data packages found in the model.",
)
@click.option(
    "-o",
    "--output",
    default="-",
    type=click.File("w", atomic=True),
)
@click.option(
    "--indent",
    default=2,
    type=click.IntRange(-1),
    help="Pretty-print the JSON output, indenting by INT spaces per level.",
)
def main(
    *,
    model: capellambse.MelodyModel,
    package_id: str,
    list_packages: bool,
    output: t.IO[str],
    indent: int | None,
) -> None:
    if list_packages:
        print("The following data packages were found in the model:")
        for i in model.search("DataPkg"):
            print(" ", i._short_repr_())
        return

    if not package_id:
        raise click.UsageError(
            "--package is required (use --list to find a package)"
        )

    if indent is not None and indent < 0:
        indent = None

    package_obj = _find_package(model, package_id)
    package = _convert_package(package_obj)
    dump = package.model_dump_json(indent=indent, exclude_defaults=True)
    with output:
        output.write(dump)
        output.write("\n")


def _find_package(
    model: capellambse.MelodyModel, package_id: str, /
) -> information.DataPkg:
    try:
        obj = model.by_uuid(package_id)
    except KeyError:
        pass
    else:
        if not isinstance(obj, information.DataPkg):
            raise click.UsageError(
                f"Expected a DataPkg at ID {package_id!r},"
                f" but found a {type(obj).__name__} instead"
            )
        return obj

    packages = model.search(information.DataPkg).by_name(
        package_id, single=False
    )
    if len(packages) < 1:
        raise click.UsageError(
            f"Couldn't find a DataPkg with ID or name {package_id!r}"
        )
    if len(packages) > 1:
        pkg_strings = []
        for i in packages:
            try:
                p = i.parent
            except ValueError:
                pkg_strings.append(f"  {i.uuid!r} (orphaned)")
            else:
                pkg_strings.append(f"  {i.uuid!r} in {p._short_repr_()}")
        raise click.UsageError(
            f"Found more than one DataPkg with name {package_id!r}:\n"
            + "\n".join(pkg_strings)
        )
    (obj,) = packages
    assert isinstance(obj, information.DataPkg)
    return obj


def _convert_package(obj: information.DataPkg, /) -> datatypes.Package:
    return datatypes.Package(
        name=obj.name,
        info=obj.description,
        subPackages=[_convert_package(i) for i in obj.packages],  # type: ignore[call-arg]
        structs=[_convert_class(i) for i in obj.classes],
        enums=[_convert_enum(i) for i in obj.enumerations],
        prefix=obj.uuid,
    )


def _convert_class(obj: information.Class, /) -> datatypes.Struct:
    if obj.super is None:
        extends = None
    else:
        extends = ""
    return datatypes.Struct(
        name=obj.name,
        info=obj.description,
        extends=extends,
        attrs=[_convert_attr(i) for i in obj.properties],
    )


def _convert_attr(obj: information.Property, /) -> datatypes.StructAttrs:
    min = 0
    max = None
    if (c := obj.max_card) and (v := c.value) and v != "*":
        try:
            max = int(v)
        except ValueError:
            logger.warning(
                "Cannot convert max_card value %r of %s to int, ignoring",
                v,
                obj._short_repr_(),
            )
    if (c := obj.min_card) and (v := c.value):
        try:
            min = int(v)
        except ValueError:
            logger.warning(
                "Cannot convert min_card value %r of %s to int, ignoring",
                v,
                obj._short_repr_(),
            )

    if (min, max) == (0, None) or min == max:
        if max is None:
            mult = "*"
        else:
            mult = str(max)
    else:
        mult = f"{min}..{max or '*'}"

    if obj.type:
        typename = obj.type.name
    else:
        logger.warning(
            "No type set, falling back to 'string' for %s",
            obj._short_repr_(),
        )
        typename = "string"

    return datatypes.StructAttrs(
        name=obj.name,
        info=obj.description,
        multiplicity=mult,
        data_type=typename,
    )


def _convert_enum(obj: information.datatype.Enumeration, /) -> datatypes.Enum:
    return datatypes.Enum(
        name=obj.name,
        info=obj.description,
        enumLiterals=[  # type: ignore[call-arg]
            datatypes.EnumLiteral(
                intId=i,  # type: ignore[call-arg]
                name=o.name,
                info=o.description,
            )
            for i, o in enumerate(obj.literals)
        ],
    )


if __name__ == "__main__":
    main()
