# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Main entry point into json2capella."""

import io
import logging
import pathlib
import typing as t

import capellambse
import click
import typing_extensions as te
from capellambse import cli_helpers, decl, helpers

import json2capella
from json2capella import importer

logger = logging.getLogger(__name__)


class _CapellaUUIDParam(click.ParamType):
    name = "UUID"

    def convert(
        self,
        value: t.Any,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> capellambse.helpers.UUIDString:
        del param, ctx

        if not helpers.is_uuid_string(value):
            self.fail(f"Not a valid UUID: {value!r}")
        return te.assert_type(value, capellambse.helpers.UUIDString)


@click.command()
@click.version_option(
    version=json2capella.__version__,
    prog_name="json2capella",
    message="%(prog)s %(version)s",
)
@click.option(
    "-m",
    "--model",
    type=cli_helpers.ModelCLI(),
    required=True,
    help="Path to the Capella model.",
)
@click.option(
    "-n",
    "--new",
    type=click.Path(path_type=pathlib.Path, exists=True),
    required=True,
    help="Path to JSON file or folder with JSON files "
    "containing the new model definition.",
)
@click.option(
    "-o",
    "--old",
    type=click.Path(path_type=pathlib.Path, exists=True),
    help="Path to JSON file or folder with JSON files. "
    "containing the old model definition.",
)
@click.option(
    "-l",
    "--layer",
    type=click.Choice(["oa", "la", "sa", "pa"], case_sensitive=False),
    help="The layer to import the JSON to.",
)
@click.option(
    "-r",
    "--root",
    type=_CapellaUUIDParam(),
    help="The UUID of the root package to import the JSON to.",
)
@click.option(
    "-t",
    "--types",
    type=_CapellaUUIDParam(),
    help="The UUID of the types package to import the generated data types to.",
)
@click.option(
    "--yaml",
    "output",
    type=click.Path(path_type=pathlib.Path, dir_okay=False),
    help="Write decl YAML into this file instead of modifying the model directly.",
)
def main(
    model: capellambse.MelodyModel,
    new: pathlib.Path,
    *,
    old: pathlib.Path,
    layer: str,
    root: capellambse.helpers.UUIDString,
    types: capellambse.helpers.UUIDString,
    output: pathlib.Path,
) -> None:
    """Import elements to Capella data package from JSON."""

    logging.basicConfig(level=logging.INFO)

    if root:
        root_uuid = root
    elif layer:
        root_uuid = getattr(model, layer).data_package.uuid
    else:
        raise click.UsageError("Either --root or --layer must be provided")

    params: dict[str, t.Any] = {}
    if types:
        params["types_uuid"] = types
    else:
        params["types_uuid"] = model.sa.data_package.uuid
        params["is_layer"] = True

    yml = importer.Importer(new, old).to_yaml(root_uuid, **params)

    if output:
        logger.info("Writing to file %s", output)
        output.write_text(yml, encoding="utf-8")
    else:
        logger.info("Writing to model %s", model.name)
        decl.apply(model, io.StringIO(yml))
        model.save()


if __name__ == "__main__":
    main()
