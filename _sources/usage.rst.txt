..
   Copyright DB InfraGO AG and contributors
   SPDX-License-Identifier: Apache-2.0

.. _usage:

*****
Usage
*****

This section describes how to use the JSON2Capella CLI.

.. code-block:: bash

   python -m json2capella -i <INPUT> -m <MODEL> -l <LAYER>

*  **-i/--input**, path to JSON file or folder with JSON files.
*  **-m/--model**, path to the Capella model.
*  **-l/--layer**, layer to import the package definitions to.
*  **-r/--root**, UUID of the root package to import the  package definitions to.
*  **-t/--types**, UUID of the types package to import the generated data types to.
*  **-o/--output**, path to output decl YAML.
