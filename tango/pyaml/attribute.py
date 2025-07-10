from pyaml.control.readback_value import Value, Quality
from .tango_attribute import TangoAttribute, ConfigModel
from .tango_pyaml_utils import *

PYAMLCLASS : str = "Attribute"

class Attribute(TangoAttribute):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

        attr_info = self._attribute_dev.attribute_query(self._attr_name)
        if attr_info.writable not in [tango._tango.AttrWriteType.READ_WRITE,
                                      tango._tango.AttrWriteType.WRITE,
                                      tango._tango.AttrWriteType.READ_WITH_WRITE]:
            raise pyaml.PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")


    def set(self, value: float):
        """Write a value to the Tango attribute."""
        try:
            self._attribute_dev.write_attribute_asynch(self._attr_name, value)
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

    def set_and_wait(self, value: float):
        """Write a value to the Tango attribute."""
        try:
            self._attribute_dev.write_attribute(self._attr_name, value)
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

    def get(self) -> float:
        """Read the last written value of the attribute."""
        try:
            return self._attribute_dev.read_attribute(self._attr_name).w_value
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
