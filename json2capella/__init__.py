# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""The json2capella package."""
import logging
from importlib import metadata

try:
    __version__ = metadata.version("json2capella")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"
del metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
