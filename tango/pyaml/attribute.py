import logging
from pydantic import BaseModel

from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value, Quality

from .controlsystem import TangoControlSystem
from .initializable_element import InitializableElement
from .device_factory import DeviceFactory
from .tango_pyaml_utils import *

PYAMLCLASS : str = "Attribute"

logger = logging.getLogger(__name__)

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

class Attribute(DeviceAccess, InitializableElement):
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
    def __init__(self, cfg: ConfigModel, writable=True):
        super().__init__()
        self._cfg = cfg

        self._attribute_dev_name, self._attr_name = cfg.attribute.rsplit("/", 1)
        self._unit = cfg.unit
        self._writable = writable
        self._attribute_dev:tango.DeviceProxy = None

        if TangoControlSystem.is_initialized():
            self.initialize()
        else:
            TangoControlSystem.get_instance().add_initializable(self)


    def initialize(self):
        super().initialize()
        try:
            self._attribute_dev = DeviceFactory().get_device(self._attribute_dev_name)
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

        if self._writable:
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
        if not self.is_initialized():
            raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
        logger.log(logging.DEBUG, f"Setting asynchronously {self._cfg.attribute} to {value}")
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
        if not self.is_initialized():
            raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
        logger.log(logging.DEBUG, f"Setting {self._cfg.attribute} to {value}")
        try:
            self._attribute_dev.write_attribute(self._attr_name, value)
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
        if not self.is_initialized():
            raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
        logger.log(logging.DEBUG, f"Reading {self._cfg.attribute}")
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
        if not self.is_initialized():
            raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
        try:
            return self._attribute_dev.read_attribute(self._attr_name).w_value
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)
