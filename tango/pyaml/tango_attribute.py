from abc import ABC

from pydantic import BaseModel
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value, Quality
from .tango_pyaml_utils import *

class ConfigModel(BaseModel):
    """Name of tango attribute (i.e. my/ps/device/current) and optionally, the units"""
    attribute: str
    unit: str = ""

class TangoAttribute(DeviceAccess, ABC):
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg

        self._attribute_dev_name, self._attr_name = cfg.attribute.rsplit("/", 1)
        self._unit = cfg.unit
        try:
            self._attribute_dev = tango.DeviceProxy(self._attribute_dev_name)
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

    def readback(self) -> Value:
        """Return the readback value."""
        try:
            attr_value = self._attribute_dev.read_attribute(self._attr_name)
            quality = Quality[attr_value.quality.name.rsplit('_', 1)[1]] # AttrQuality.ATTR_VALID gives Quality.VALID
            value = Value(attr_value.value, quality, attr_value.time.todatetime() )
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)
        return value

    def unit(self) -> str:
        return self._unit

    def name(self) -> str:
        """Return the name of the variable"""
        return self._cfg.attribute

    def measure_name(self) -> str:
        """Return the name of the measure"""
        return self._attr_name
