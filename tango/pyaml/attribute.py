"""
Scalar Tango attribute access.

This module maps a single Tango attribute (or one element of a SPECTRUM
attribute) onto the pyAML :class:`~pyaml.control.deviceaccess.DeviceAccess`
interface.
"""

import copy
import logging

from pydantic import BaseModel

import pyaml
import tango
from pyaml.common.element import __pyaml_repr__
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Quality, Value
from pyaml.validation import DynamicValidation, register_schema

from .device_factory import DeviceFactory
from .initializable_element import InitializableElement
from .tango_pyaml_utils import tango_to_PyAMLException, to_float_or_none

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
    range: tuple[float | None, float | None] | None = None
    index: int | None = None


@register_schema
class Attribute(DeviceAccess, InitializableElement, DynamicValidation):
    """
    Tango attribute that can be written to.

    The Tango device proxy is obtained lazily from
    :class:`~tango.pyaml.device_factory.DeviceFactory` on first access, so
    building an ``Attribute`` never contacts the control system.

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

    Attributes
    ----------
    _attribute : str
        Full path of the Tango attribute.
    _unit : str
        Unit of the attribute.
    _range : tuple of (float or None, float or None) or None
        Configured range, or ``None`` to query Tango on first use.
    _index : int or None
        Index into a SPECTRUM attribute, or ``None`` for scalar access.
    _writable : bool
        ``True`` if writes are allowed (always ``False`` when indexed).
    _attribute_dev : tango.DeviceProxy or None
        Proxy of the device owning the attribute, set on initialization.
    _attr_config : tango.AttributeInfoEx or None
        Tango attribute configuration, set on initialization.
    _attribute_dev_name : str or None
        Device part of the attribute path, set on initialization.
    _attr_name : str or None
        Attribute part of the attribute path, set on initialization.

    Methods
    -------
    initialize()
        Connect to the Tango device and check the attribute configuration.
    is_writable()
        Tell whether the attribute accepts writes.
    set(value)
        Write a value asynchronously to the Tango attribute.
    set_and_wait(value)
        Write a value synchronously to the Tango attribute.
    get()
        Get the last written value of the attribute.
    readback()
        Return the readback value with metadata.
    unit()
        Return the unit of the attribute.
    name()
        Return the full attribute name.
    measure_name()
        Return the short attribute name (last component).
    get_tango_attribute()
        Return the raw Tango attribute path without index decoration.
    clone_with_tango_attribute(attribute)
        Return a shallow copy configured with another Tango attribute path.
    get_range()
        Return the valid range of the attribute.
    check_device_availability()
        Check whether the Tango device answers to a ping.

    Raises
    ------
    pyaml.PyAMLException
        If the Tango attribute is not writable.
    """

    def __init__(
        self,
        attribute: str,
        unit: str = "",
        range: tuple[float | None, float | None] | None = None,
        index: int | None = None,
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
        """
        Connect to the Tango device and check the attribute configuration.

        Splits the attribute path into device and attribute names, obtains
        the device proxy from :class:`~tango.pyaml.device_factory.DeviceFactory`
        and reads the attribute configuration.

        Raises
        ------
        pyaml.PyAMLException
            If the device proxy cannot be created, if an indexed attribute is
            not a SPECTRUM, or if a writable attribute is not writable in
            Tango.
        """
        super().initialize()
        try:
            self._attribute_dev_name, self._attr_name = self._attribute.rsplit("/", 1)
            self._attribute_dev = DeviceFactory().get_device(self._attribute_dev_name)
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

        self._attr_config: tango.AttributeConfig = (
            self._attribute_dev.get_attribute_config(self._attr_name, wait=True)
        )

        if (
            self._index is not None
            and self._attr_config.data_format != tango.AttrDataFormat.SPECTRUM
        ):
            raise pyaml.PyAMLException(
                f"Tango attribute '{self._attribute}' is not a SPECTRUM; "
                "indexed access requires a vector attribute."
            )

        if self._writable and self._attr_config.writable not in [
            tango.AttrWriteType.READ_WRITE,
            tango.AttrWriteType.WRITE,
            tango.AttrWriteType.READ_WITH_WRITE,
        ]:
            raise pyaml.PyAMLException(
                f"Tango attribute {self._attribute} is not writable."
            )

    def is_writable(self):
        """
        Tell whether the attribute accepts writes.

        Returns
        -------
        bool
            ``True`` if :meth:`set` and :meth:`set_and_wait` are allowed.
        """
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

        Returns
        -------
        Attribute
            Copy of this instance pointing to ``attribute``.
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
        """
        Return the valid range of the attribute.

        The configured ``range`` takes precedence; otherwise the ``min_value``
        and ``max_value`` limits of the Tango attribute configuration are
        used, which requires initialization.

        Returns
        -------
        list of float or None
            ``[min, max]`` where an unbounded limit is ``None``.

        Raises
        ------
        pyaml.PyAMLException
            If no range is configured and initialization fails.
        """
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
        """
        Check whether the Tango device answers to a ping.

        Returns
        -------
        bool
            ``True`` if the device is reachable, ``False`` if initialization
            or the ping fails.
        """
        available = True
        try:
            self._ensure_initialized()
            self._attribute_dev.ping()
        except (tango.DevFailed, pyaml.PyAMLException):
            available = False
        return available

    def __repr__(self):
        return __pyaml_repr__(self)
