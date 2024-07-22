<!--
 ~ Copyright DB InfraGO AG and contributors
 ~ SPDX-License-Identifier: Apache-2.0
 -->

# JSON2Capella

![image](https://github.com/DSD-DBS/json2capella/actions/workflows/build-test-publish.yml/badge.svg)
![image](https://github.com/DSD-DBS/json2capella/actions/workflows/lint.yml/badge.svg)

Command-line tool for importing package definitions from JSON files into a Capella model's data package.

![Showcase](https://i.imgur.com/Qwzm0In.gif)

# Documentation

Read the [full documentation on Github pages](https://dsd-dbs.github.io/json2capella).

# Examples

Apply package definition from .json file to Capella model layer's root data package:

```sh
python -m json2capella \
-i tests/data/example_jsons/package1.json \
-m tests/data/empty_project_60 \
-l la \
```

Import package definitions from folder with .json files to Capella model layer's root data package:

```sh
python -m json2capella \
-i tests/data/example_jsons \
-m tests/data/empty_project_60 \
-l la
```

# Installation

You can install the latest released version directly from PyPI.

```sh
pip install json2capella
```

To set up a development environment, clone the project and install it into a
virtual environment.

```sh
git clone https://github.com/DSD-DBS/json2capella
cd json2capella
python -m venv .venv

source .venv/bin/activate.sh  # for Linux / Mac
.venv\Scripts\activate  # for Windows

pip install -U pip pre-commit
pip install -e '.[docs,test]'
pre-commit install
```

# Contributing

We'd love to see your bug reports and improvement suggestions! Please take a
look at our [guidelines for contributors](CONTRIBUTING.md) for details.

# Licenses

This project is compliant with the
[REUSE Specification Version 3.0](https://git.fsfe.org/reuse/docs/src/commit/d173a27231a36e1a2a3af07421f5e557ae0fec46/spec.md).

Copyright DB InfraGO AG, licensed under Apache 2.0 (see full text in
[LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt))

Dot-files are licensed under CC0-1.0 (see full text in
[LICENSES/CC0-1.0.txt](LICENSES/CC0-1.0.txt))
