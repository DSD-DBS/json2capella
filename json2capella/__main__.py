# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Main entry point into json2capella."""

import click

import json2capella


@click.command()
@click.version_option(
    version=json2capella.__version__,
    prog_name="json2capella",
    message="%(prog)s %(version)s",
)
def main():
    """Console script for json2capella."""


if __name__ == "__main__":
    main()
