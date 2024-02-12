# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Main entry point into json2capella."""

import pathlib
import sys

import click

import json2capella
from json2capella import convert
from json2capella.viewer import app


@click.command()
@click.version_option(
    version=json2capella.__version__,
    prog_name="json2capella",
    message="%(prog)s %(version)s",
)
@click.argument(
    "json_path",
    type=click.Path(exists=True, path_type=pathlib.Path),
    required=True,
)
@click.argument(
    "capella_path",
    type=click.Path(exists=True),
    required=True,
)
@click.argument(
    "layer",
    type=click.Choice(["oa", "la", "sa", "pa"], case_sensitive=False),
    required=True,
)
@click.option(
    "--exists-action",
    "action",
    type=click.Choice(
        ["skip", "replace", "abort", "ask"], case_sensitive=False
    ),
    default="ask" if sys.stdin.isatty() else "abort",
    help="Default action when an element already exists.",
)
@click.option("--port", type=int, help="Open model viewer on given port.")
def main(
    json_path: pathlib.Path,
    capella_path: str,
    layer: str,
    action: str,
    port: int,
):
    """Import elements to Capella data package from JSON file.

    JSON_PATH: Path to JSON file or folder with JSON files.
    CAPELLA_PATH: Path to Capella model.
    LAYER: Layer of Capella model to import elements to.
    """

    converter = convert.Converter(
        json_path,
        capella_path,
        layer,
        action,
    )
    converter()

    if port:
        app.start(converter.capella.model, layer, port)


if __name__ == "__main__":
    main()
