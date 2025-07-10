import tango
from pydantic import BaseModel
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value, Quality
from .tango_attribute import TangoAttribute, ConfigModel
from .tango_pyaml_utils import *

PYAMLCLASS : str = "AttributeReadOnly"

class AttributeReadOnly(TangoAttribute):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

    def set(self, value: float):
        raise pyaml.PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")

    def set_and_wait(self, value: float):
        raise pyaml.PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")

    def get(self) -> float:
        raise pyaml.PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")

    def readback(self) -> Value:
        """Return the readback value."""
        try:
            attr_value = self._attribute_dev.read_attribute(self._attr_name)
            quality = Quality[attr_value.quality.name.rsplit('_', 1)[1]] # AttrQuality.ATTR_VALID gives Quality.VALID
            value = Value(attr_value.value, quality, attr_value.time.todatetime() )
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)
        return value
