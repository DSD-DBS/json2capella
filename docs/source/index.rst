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

   $ python -m json2capella <JSON_FILE_PATH> <CAPELLA_MODEL_PATH> <CAPELLA_MODEL_LAYER> --port=<PORT> --exists-action=<EXISTS_ACTION>

*  **<JSON_FILE_PATH>**, import from JSON file <JSON_FILE_PATH>
*  **<CAPELLA_MODEL_PATH>**, export to Capella model <CAPELLA_MODEL_PATH>
*  **<CAPELLA_MODEL_LAYER>**, use data package of Capella model layer <CAPELLA_MODEL_LAYER>
*  **--port=<PORT>**, start Capella model viewer at <PORT> (optional)
*  **--exists-action=<EXISTS_ACTION>**, action to take if a Capella element already exists (optional)

   * **skip**, skip elements
   * **replace**, replace elements
   * **abort**, abort import
   * **ask**, ask the user (default)


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
