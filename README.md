# tango-pyaml

**Bridge between **[**Tango Controls**](https://www.tango-controls.org/)** and PyAML**



## Overview

`tango-pyaml` is a Python bridge between the [Tango control system](https://www.tango-controls.org/) and the [PyAML](https://github.com/python-accelerator-middle-layer/pyaml) abstraction layer for control systems. It provides a set of classes that allow Tango attributes and devices to be accessed and controlled using PyAML concepts.

This library is part of the **Python Accelerator Middle Layer (PyAML)** ecosystem.

## Features

- ✅ Read and write Tango attributes via a unified PyAML interface
- 🔁 Support for read-only and read/write attributes
- 📊 Grouped attribute operations using `tango.Group`
- 💥 Exception mapping from Tango exceptions to PyAML exceptions
- 🧹 Designed to integrate seamlessly with PyAML `ControlSystem` components
- 🧪 Mocked devices for unit testing without Tango runtime

## Installation

```bash
pip install tango-pyaml
```

## Requirements

- Python >= 3.9
- [PyTango](https://pytango.readthedocs.io/en/latest/) >= 9.5.1
- [PyAML](https://github.com/python-accelerator-middle-layer/pyaml)
- [pydantic](https://docs.pydantic.dev/) >= 2.0

For development and testing:

```bash
pip install tango-pyaml[dev]
```

## Usage Example

This is an example of an explicit call to a Tango attribute using PyAML. For more details about implicit declaration and broader configuration options, please refer to the [PyAML documentation](https://github.com/python-accelerator-middle-layer/pyaml).

Configuration file `attribute.yaml`:

```yaml
attribute: "sys/tg_test/1/float_scalar"
unit: "A"
```

Python code:

```python
from tango.pyaml.attribute import Attribute
from tango.pyaml.tango_attribute import ConfigModel
import yaml

with open("attribute.yaml") as f:
    cfg_dict = yaml.safe_load(f)

cfg = ConfigModel(**cfg_dict)
attr = Attribute(cfg)

attr.set(10.0)
value = attr.get()
readback = attr.readback()

print(f"Value: {value}, Readback: {readback.value} [{readback.quality}]")
```

## Available Classes

- `Attribute` — Read/write access to a Tango attribute
- `AttributeReadOnly` — Read-only attribute wrapper
- `AttributeList` — Manage a group of attributes from multiple devices
- `TangoControlSystem` — Adapter to configure global Tango control system context

## Testing

Tests rely on mocked Tango devices and attributes using `unittest.mock`. To run tests:

```bash
pytest
```

## Project Structure

- `tango.pyaml.attribute` – Main attribute interface
- `tango.pyaml.attribute_read_only` – Read-only attribute implementation
- `tango.pyaml.attribute_list` – Attribute groups with `tango.Group`
- `tango.pyaml.tango_attribute` – Base class wrapping attribute logic
- `mocked_device_proxy.py` – In-memory mock for Tango `DeviceProxy` and `AttributeProxy`

## License

This project is licensed under the MIT License.

## Links

- 🧺 [Repository](https://github.com/python-accelerator-middle-layer/tango-pyaml)

