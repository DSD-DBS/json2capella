..
   Copyright DB InfraGO AG and contributors
   SPDX-License-Identifier: Apache-2.0

.. _usage:

*****
Usage
*****

This section describes how to use the JSON2Capella CLI.

.. code-block:: bash

   python -m json2capella -n <INPUT> -m <MODEL> -l <LAYER>

*  **-m/--model**, path to the Capella model.
*  **-n/--new**, path to JSON file or folder with JSON files.
*  **-o/--old**, path to JSON file or folder with JSON files to compare with. (optional)
*  **-l/--layer**, layer to import the package definitions to. (optional)
*  **-r/--root**, UUID of the root package to import the  package definitions to. (optional)
*  **-t/--types**, UUID of the types package to import the generated data types to. (optional)
*  **--yaml**, path to output decl YAML. (optional)
