..
   Copyright DB InfraGO AG and contributors
   SPDX-License-Identifier: Apache-2.0

***********************************************
Welcome to the JSON2Capella documentation!
***********************************************


Overview
========

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Black

**Date**: |today| **Version**: |Version|

JSON2Capella is a tool to import data from JSON files into a Capella model's data package.

Usage
=====

.. code-block:: bash

   $ python -m json2capella  -i <INPUT> -m <MODEL> -l <LAYER>

*  **-i/--input**, path to JSON file or folder with JSON files.
*  **-m/--model**, path to the Capella model.
*  **-l/--layer**, layer to import the JSON to.
*  **-r/--root**, UUID of the root package to import the JSON to.
*  **-t/--types**, UUID of the types package to import the generated data types to.
*  **-o/--output**, path to output decl YAML.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. toctree::
   :maxdepth: 3
   :caption: API reference

   code/modules



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
