import tango
from pydantic import BaseModel
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS : str = "Attribute"

class ConfigModel(BaseModel):
    attribute: str
    unit: str = ""
    """Name of tango attribute (i.e. my/ps/device/current)"""

class Attribute(DeviceAccess):
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg

        self._attribute_dev_name, self._attr_name = cfg.attribute.rsplit("/", 1)
        self._unit = cfg.unit
        self._attribute_dev = tango.DeviceProxy(self._attribute_dev_name)



    def set(self, value: float):
        """Write a value to the Tango attribute."""
        self._attribute_dev.write_attribute(self._attr_name, value)

    def get(self) -> float:
        """Read the last written value of the attribute."""
        return self._attribute_dev.read_attribute(self._attr_name).w_value

    def readback(self) -> float:
        """Return the readback value. Alias for get()."""
        return self._attribute_dev.read_attribute(self._attr_name).value

    def unit(self) -> str:
        return self._unit

    def name(self) -> str:
        """Return the name of the variable"""
        return self._cfg.attribute

    def measure_name(self) -> str:
        """Return the name of the measure"""
        return self._attr_name
