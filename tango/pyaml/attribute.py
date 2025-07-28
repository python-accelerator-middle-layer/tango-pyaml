from pyaml.control.readback_value import Value, Quality
from .tango_attribute import TangoAttribute, ConfigModel
from .tango_pyaml_utils import *

PYAMLCLASS : str = "Attribute"

class Attribute(TangoAttribute):
    """
    Tango attribute that can be written to.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration object containing attribute path and units.

    Raises
    ------
    pyaml.PyAMLException
        If the Tango attribute is not writable.
    """
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

        attr_info = self._attribute_dev.attribute_query(self._attr_name)
        if attr_info.writable not in [tango._tango.AttrWriteType.READ_WRITE,
                                      tango._tango.AttrWriteType.WRITE,
                                      tango._tango.AttrWriteType.READ_WITH_WRITE]:
            raise pyaml.PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")


    def set(self, value: float):
        """
        Write a value asynchronously to the Tango attribute.

        Parameters
        ----------
        value : float
            Value to write to the attribute.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango write fails.
        """
        try:
            self._attribute_dev.write_attribute_asynch(self._attr_name, value)
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)


    def set_and_wait(self, value: float):
        """
        Write a value synchronously to the Tango attribute.

        Parameters
        ----------
        value : float
            Value to write to the attribute.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango write fails.
        """
        try:
            self._attribute_dev.write_attribute(self._attr_name, value)
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

    def get(self) -> float:
        """
        Get the last written value of the attribute.

        Returns
        -------
        float
            The last written value.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango read fails.
        """
        try:
            return self._attribute_dev.read_attribute(self._attr_name).w_value
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

    def readback(self) -> Value:
        """
        Return the readback value with metadata.

        Returns
        -------
        Value
            The readback value including quality and timestamp.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango read fails.
        """
        try:
            attr_value = self._attribute_dev.read_attribute(self._attr_name)
            quality = Quality[attr_value.quality.name.rsplit('_', 1)[1]] # AttrQuality.ATTR_VALID gives Quality.VALID
            value = Value(attr_value.value, quality, attr_value.time.todatetime() )
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)
        return value
