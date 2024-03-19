# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Main entry point into json2capella."""

import io
import pathlib

import capellambse
import click
from capellambse import cli_helpers, decl

import json2capella
from json2capella import importer

from . import logger


@click.command()
@click.version_option(
    version=json2capella.__version__,
    prog_name="json2capella",
    message="%(prog)s %(version)s",
)
@click.option(
    "-i",
    "--input",
    type=click.Path(path_type=pathlib.Path, exists=True),
    required=True,
    help="Path to JSON file or folder with JSON files.",
)
@click.option(
    "-m",
    "--model",
    type=cli_helpers.ModelCLI(),
    required=True,
    help="Path to the Capella model.",
)
@click.option(
    "-l",
    "--layer",
    type=click.Choice(["oa", "la", "sa", "pa"], case_sensitive=False),
    required=True,
    help="The layer to import the messages to.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=pathlib.Path, dir_okay=False),
    help="Output file path for decl YAML.",
)
def main(
    input: pathlib.Path,
    model: capellambse.MelodyModel,
    layer: str,
    output: pathlib.Path,
):
    """Import elements to Capella data package from JSON."""

    # TODO validate against valid JSON schema

    root_uuid = getattr(model, layer).data_package.uuid
    types_uuid = model.sa.data_package.uuid

    parsed = importer.Importer(input)
    logger.info("Loaded %d packages", len(parsed.json["subPackages"]))

    yml = parsed.to_yaml(root_uuid, types_uuid)
    if output:
        logger.info("Writing to file %s", output)
        output.write_text(yml, encoding="utf-8")
    else:
        logger.info("Writing to model %s", model.name)
        decl.apply(model, io.StringIO(yml))
        model.save()


if __name__ == "__main__":
    main()
