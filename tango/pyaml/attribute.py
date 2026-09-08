import copy
import logging
import tango
import pyaml
from typing import Optional, Tuple

from pydantic import BaseModel

from pyaml.common.element import __pyaml_repr__
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value, Quality
from pyaml.validation import register_schema, DynamicValidation

from .initializable_element import InitializableElement
from .device_factory import DeviceFactory
from .tango_pyaml_utils import to_float_or_none, tango_to_PyAMLException

PYAMLCLASS: str = "Attribute"

logger = logging.getLogger(__name__)


class AttributeConfig(BaseModel):
    """
    Configuration model for Tango attributes.

    Attributes
    ----------
    attribute : str
        Full path of the Tango attribute (e.g., 'my/ps/device/current').
    unit : str, optional
        The unit of the attribute.
    range : tuple(min, max), optional
        Range of valid values. Use null for -∞ or +∞.
    index : int, optional
        Zero-based index into a SPECTRUM attribute. When set, the instance
        behaves as a read-only scalar view of one vector element; writes are
        always rejected and a SPECTRUM data_format is enforced on init.
    """

    attribute: str
    unit: str = ""
    range: Optional[Tuple[Optional[float], Optional[float]]] = None
    index: Optional[int] = None


@register_schema
class Attribute(DeviceAccess, InitializableElement, DynamicValidation):
    """
    Tango attribute that can be written to.

    Parameters
    ----------
    attribute : str
        Full path of the Tango attribute (e.g., 'my/ps/device/current').
    unit : str, optional
        The unit of the attribute.
    range : tuple(min, max), optional
        Range of valid values. Use null for -∞ or +∞.
    index : int, optional
        Zero-based index into a SPECTRUM attribute. When set, the instance
        behaves as a read-only scalar view of one vector element; writes are
        always rejected and a SPECTRUM data_format is enforced on init.
    writable : bool, optional
        If the attribute should be writable. Default is True.

    Raises
    ------
    pyaml.PyAMLException
        If the Tango attribute is not writable.
    """

    def __init__(
        self,
        attribute: str,
        unit: str = "",
        range: Optional[Tuple[Optional[float], Optional[float]]] = None,
        index: Optional[int] = None,
        writable=True,
    ):
        super().__init__()

        self._attribute = attribute
        self._unit = unit
        self._range = range
        self._index = index

        # Indexed access never writes individual array elements.
        self._writable = writable and self._index is None
        self._attribute_dev: tango.DeviceProxy = None
        self._attr_config: tango.AttributeConfig = None
        self._attribute_dev_name: str = None
        self._attr_name: str = None

    def initialize(self):
        super().initialize()
        try:
            self._attribute_dev_name, self._attr_name = self._attribute.rsplit("/", 1)
            self._attribute_dev = DeviceFactory().get_device(self._attribute_dev_name)
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

        self._attr_config: tango.AttributeConfig = (
            self._attribute_dev.get_attribute_config(self._attr_name, wait=True)
        )

        if self._index is not None:
            if self._attr_config.data_format != tango.AttrDataFormat.SPECTRUM:
                raise pyaml.PyAMLException(
                    f"Tango attribute '{self._attribute}' is not a SPECTRUM; "
                    "indexed access requires a vector attribute."
                )

        if self._writable:
            if self._attr_config.writable not in [
                tango.AttrWriteType.READ_WRITE,
                tango.AttrWriteType.WRITE,
                tango.AttrWriteType.READ_WITH_WRITE,
            ]:
                raise pyaml.PyAMLException(
                    f"Tango attribute {self._attribute} is not writable."
                )

    def is_writable(self):
        return self._writable

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
            If the Tango write fails or this is an indexed attribute.
        """
        if self._index is not None:
            raise pyaml.PyAMLException(
                f"Indexed attribute '{self._attribute}[{self._index}]' "
                "does not support individual element writes."
            )
        self._ensure_initialized()
        logger.log(
            logging.DEBUG, f"Setting asynchronously {self._attribute} to {value}"
        )
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
            If the Tango write fails or this is an indexed attribute.
        """
        if self._index is not None:
            raise pyaml.PyAMLException(
                f"Indexed attribute '{self._attribute}[{self._index}]' "
                "does not support individual element writes."
            )
        self._ensure_initialized()
        logger.log(logging.DEBUG, f"Setting {self._attribute} to {value}")
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
        self._ensure_initialized()
        logger.log(logging.DEBUG, f"Reading {self._attribute}")
        try:
            attr_value = self._attribute_dev.read_attribute(self._attr_name)
            quality = Quality[
                attr_value.quality.name.rsplit("_", 1)[1]
            ]  # AttrQuality.ATTR_VALID gives Quality.VALID
            raw = (
                attr_value.value[self._index]
                if self._index is not None
                else attr_value.value
            )
            value = Value(raw, quality, attr_value.time.todatetime())
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
            The attribute path (e.g., 'my/ps/device/current'), or with index
            notation when indexed (e.g., 'my/ps/device/current[2]').
        """
        if self._index is not None:
            return f"{self._attribute}[{self._index}]"
        return self._attribute

    def get_tango_attribute(self) -> str:
        """
        Return the raw Tango attribute path without index decoration.

        Returns
        -------
        str
            Tango attribute path stored in the configuration.
        """
        return self._attribute

    def clone_with_tango_attribute(self, attribute: str) -> "Attribute":
        """
        Return a shallow copy configured with another Tango attribute path.

        Parameters
        ----------
        attribute : str
            Tango attribute path to store in the cloned instance.
        """
        new_obj = copy.copy(self)
        new_obj._attribute = attribute
        return new_obj

    def measure_name(self) -> str:
        """
        Return the short attribute name (last component).

        Returns
        -------
        str
            The attribute name (e.g., 'current'), with index notation when
            indexed (e.g., 'current[2]').
        """
        short = self._attribute.rsplit("/", 1)[1]
        if self._index is not None:
            return f"{short}[{self._index}]"
        return short

    def get(self) -> float:
        """
        Get the last written value of the attribute.

        For indexed attributes, returns the setpoint element at the configured
        index (``w_value[index]``).

        Returns
        -------
        float
            The last written value.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango read fails.
        """
        self._ensure_initialized()
        try:
            attr_val = self._attribute_dev.read_attribute(self._attr_name)
            if self._index is not None:
                return attr_val.w_value[self._index]
            return attr_val.w_value
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

    def get_range(self) -> list[float]:
        attr_range: list[float] = [None, None]
        if self._range is not None:
            attr_range[0] = self._range[0] if self._range[0] is not None else None
            attr_range[1] = self._range[1] if self._range[1] is not None else None
        else:
            self._ensure_initialized()
            min_value = self._attr_config.min_value
            max_value = self._attr_config.max_value
            attr_range[0] = to_float_or_none(min_value)
            attr_range[1] = to_float_or_none(max_value)

        return attr_range

    def check_device_availability(self) -> bool:
        available = True
        try:
            self._ensure_initialized()
            self._attribute_dev.ping()
        except tango.DevFailed | pyaml.PyAMLException:
            available = False
        return available

    def __repr__(self):
        return __pyaml_repr__(self)
