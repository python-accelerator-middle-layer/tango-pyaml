# tango-pyaml

**Bridge between **[**Tango Controls**](https://www.tango-controls.org/)** and pyAML**

[![Documentation Status](https://readthedocs.org/projects/tango-pyaml/badge/?version=latest)](https://tango-pyaml.readthedocs.io/en/latest/?badge=latest)
[![Current release](https://img.shields.io/github/v/release/python-accelerator-middle-layer/tango-pyaml)](https://github.com/python-accelerator-middle-layer/tango-pyaml/releases)

## Overview

`tango-pyaml` is a Python bridge between the [Tango control system](https://www.tango-controls.org/) and the [pyAML](https://github.com/python-accelerator-middle-layer/pyaml) abstraction layer for control systems. It provides a set of classes that allow Tango attributes and devices to be accessed and controlled using pyAML concepts.

## Features

- ✅ Read and write Tango attributes via a unified PyAML interface
- 🔁 Support for read-only and read/write attributes
- 📊 Grouped attribute operations using `tango.Group`
- 💥 Exception mapping from Tango exceptions to PyAML exceptions
- 🧹 Designed to integrate seamlessly with PyAML `ControlSystem` components
- 🧪 Mocked devices for unit testing without Tango runtime

## Installation

Install the package from PyPI:

```bash
pip install tango-pyaml
```

## Development

Install the development dependencies with:

```bash
pip install tango-pyaml[dev]
```

Run the test suite with:

```bash
pytest
```

Install the pre-commit hooks with:

```bash
pre-commit install
```

## Documentation

The documentation is available at:

<https://tango-pyaml.readthedocs.io/en/stable/>

## Contributing

Please use the issue tracker or submit a pull request.
