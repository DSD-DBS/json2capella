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

   python -m json2capella -i tests/data/example_jsons/package1.json -m tests/data/empty_project_60 -l la

Import from folder
------------------
.. code-block:: bash

   python -m json2capella -i tests/data/example_jsons -m tests/data/empty_project_60 -l la
