..
   Copyright DB InfraGO AG and contributors
   SPDX-License-Identifier: Apache-2.0

.. _examples:

********
Examples
********

This section contains a collection of examples that demonstrate how to use the tool.

Import from file
----------------
.. code-block:: bash

   python -m json2capella --new tests/data/example_jsons/package1.json --model tests/data/empty_project_60 --layer la

Import from folder
------------------
.. code-block:: bash

   python -m json2capella --new tests/data/example_jsons --model tests/data/empty_project_60 --layer la
