from abc import ABC

from pydantic import BaseModel
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value, Quality
from .tango_pyaml_utils import *

class ConfigModel(BaseModel):
    """
    Configuration model for Tango attributes.

    Attributes
    ----------
    attribute : str
        Full path of the Tango attribute (e.g., 'my/ps/device/current').
    unit : str, optional
        The unit of the attribute.
    """
    attribute: str
    unit: str = ""

class TangoAttribute(DeviceAccess, ABC):
    """
    Abstract base class for Tango attribute access.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration model containing attribute path and unit.

    Raises
    ------
    pyaml.PyAMLException
        If connection to Tango device proxy fails.
    """

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
        """
        Read the attribute value with metadata.

        Returns
        -------
        Value
            The attribute value, quality and timestamp.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango read operation fails.
        """
        try:
            attr_value = self._attribute_dev.read_attribute(self._attr_name)
            quality = Quality[attr_value.quality.name.rsplit('_', 1)[1]] # AttrQuality.ATTR_VALID gives Quality.VALID
            value = Value(attr_value.value, quality, attr_value.time.todatetime() )
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)
        return value

    def unit(self) -> str:
        """
        Return the unit of the attribute.

        Returns
        -------
        str
            The unit string.
        """
        return self._unit

    def name(self) -> str:
        """
        Return the full attribute name.

        Returns
        -------
        str
            The attribute path (e.g., 'my/ps/device/current').
        """
        return self._cfg.attribute

    def measure_name(self) -> str:
        """
        Return the short attribute name (last component).

        Returns
        -------
        str
            The attribute name (e.g., 'current').
        """
        return self._attr_name

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
