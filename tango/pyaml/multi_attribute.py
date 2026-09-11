"""
Aggregated access to several scalar Tango attributes.

:class:`MultiAttribute` is the Tango implementation of the pyAML
:class:`~pyaml.control.deviceaccesslist.DeviceAccessList` aggregator: reads and
writes on the managed :class:`~tango.pyaml.attribute.Attribute` objects are
issued asynchronously and collected afterwards.
"""

import logging

import numpy as np
from numpy import typing as npt
from pydantic import BaseModel

import pyaml
from pyaml.common.element import __pyaml_repr__
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.deviceaccesslist import DeviceAccessList
from pyaml.validation import DynamicValidation, register_schema

from .attribute import Attribute, AttributeConfig
from .device_factory import DeviceFactory

PYAMLCLASS: str = "MultiAttribute"

logger = logging.getLogger(__name__)


class MultiAttributeConfig(BaseModel):
    """
    Configuration model for a list of Tango attributes.

    Attributes
    ----------
    attributes : list of str
        List of Tango attribute paths.
    name : str, optional
        Group name.
    unit : str, optional
        Unit of the attributes.
    range : tuple(min, max), optional
        Range of valid values. Use null for -∞ or +∞.
    """

    attributes: list[str] = []
    name: str = ""
    unit: str = ""
    range: tuple[float | None, float | None] | None = None


@register_schema
class MultiAttribute(DeviceAccessList, DynamicValidation):
    """
    Aggregate several scalar Tango attributes into one vector access.

    Each managed item is an :class:`~tango.pyaml.attribute.Attribute`.
    Items can be created from the ``attributes`` paths at construction time
    or appended later with :meth:`add_devices`; the latter is how
    :meth:`~tango.pyaml.controlsystem.TangoControlSystem.get_aggregator`
    uses this class.

    Parameters
    ----------
    attributes : list of str, optional
        List of Tango attribute paths. Default is an empty list.
    name : str, optional
        Group name.
    unit : str, optional
        Unit shared by all attributes.
    range : tuple(min, max), optional
        Range of valid values applied to every attribute. Use null for -∞
        or +∞.

    Attributes
    ----------
    _attributes : list of str
        Tango attribute paths given at construction time.
    _name : str
        Group name.
    _unit : str
        Unit shared by all attributes.
    _range : tuple of (float or None, float or None) or None
        Range applied to every attribute built from ``_attributes``.
    _items : list of Attribute
        Managed attributes, in order.

    Methods
    -------
    len()
        Return the number of managed attributes.
    get_device_at(index)
        Return the managed attribute at a given position.
    add_devices(devices)
        Append one or several attributes to the aggregate.
    set(value)
        Write one value per attribute, asynchronously.
    set_and_wait(value)
        Not implemented.
    get()
        Return the last written value of every attribute.
    readback()
        Return the readback value of every attribute.
    get_range()
        Return the valid ranges of all attributes.
    check_device_availability()
        Check whether every managed device is reachable.
    unit()
        Return the unit shared by the attributes.

    Notes
    -----
    Reads and writes are issued with the PyTango asynchronous API
    (``read_attribute_asynch`` / ``write_attribute_asynch``) on every item
    first, and the replies are then collected in order. The reply timeout is
    the one of :class:`~tango.pyaml.device_factory.DeviceFactory`.
    """

    def __init__(
        self,
        attributes: list[str] | None = None,
        name: str = "",
        unit: str = "",
        range: tuple[float | None, float | None] | None = None,
    ):
        super().__init__()
        self._attributes = [] if attributes is None else attributes
        self._name = name
        self._unit = unit
        self._range = range
        self._items: list[Attribute] = []

        for attribute in self._attributes:
            attr_config = AttributeConfig(
                attribute=attribute, unit=self._unit, range=self._range
            )
            attr = Attribute(**attr_config.model_dump())
            self._items.append(attr)

    def len(self) -> int:
        """
        Return the number of managed attributes.

        Returns
        -------
        int
            Number of items.
        """
        return len(self._items)

    def get_device_at(self, index: int) -> DeviceAccess:
        """
        Return the managed attribute at a given position.

        Parameters
        ----------
        index : int
            Zero-based position in the aggregate.

        Returns
        -------
        DeviceAccess
            The :class:`~tango.pyaml.attribute.Attribute` at ``index``.
        """
        return self._items[index]

    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        """
        Append one or several attributes to the aggregate.

        Parameters
        ----------
        devices : DeviceAccess or list of DeviceAccess
            Attribute(s) to append. Each one must be an instance of
            :class:`~tango.pyaml.attribute.Attribute`.

        Raises
        ------
        pyaml.PyAMLException
            If any device is not an ``Attribute``.
        """
        if isinstance(devices, list):
            if any(not isinstance(device, Attribute) for device in devices):
                raise pyaml.PyAMLException(
                    "All devices must be instances of Attribute (tango.pyaml.attribute)."
                )
            self._items.extend(devices)
        else:
            if not isinstance(devices, Attribute):
                raise pyaml.PyAMLException(
                    "Device must be an instance of Attribute (tango.pyaml.attribute)."
                )
            self._items.append(devices)

    def set(self, value: npt.NDArray[np.float64]):
        """
        Write one value per attribute, asynchronously.

        All writes are issued first, then every reply is awaited so that the
        call returns once all devices acknowledged the write.

        Parameters
        ----------
        value : numpy.ndarray of float
            Values to write, one per managed attribute, in order.

        Raises
        ------
        pyaml.PyAMLException
            If the size of ``value`` does not match the number of items.
        """
        if len(value) != len(self._items):
            raise pyaml.PyAMLException(
                f"Size of value ({len(value)} do not match the number of managed devices ({len(self._items)})"
            )
        asynch_call_ids = []
        timeout = DeviceFactory().get_timeout_ms()
        # Set part
        for index, device in enumerate(self._items):
            device._ensure_initialized()
            asynch_call_id = device._attribute_dev.write_attribute_asynch(
                device._attr_name, value[index]
            )
            asynch_call_ids.append(asynch_call_id)

        # Wait part
        for index, call_id in enumerate(asynch_call_ids):
            self._items[index]._attribute_dev.write_attribute_reply(call_id, timeout)

    def set_and_wait(self, value: npt.NDArray[np.float64]):
        """
        Not implemented.

        Parameters
        ----------
        value : numpy.ndarray of float
            Values to write, one per managed attribute.

        Raises
        ------
        NotImplementedError
            Always.
        """
        raise NotImplementedError("Not implemented yet.")

    def get(self) -> npt.NDArray[np.float64]:
        """
        Return the last written value of every attribute.

        For writable attributes the Tango ``w_value`` (setpoint) is returned;
        for read-only ones the readback ``value`` is used instead.

        Returns
        -------
        numpy.ndarray of float
            Setpoints, one per managed attribute, in order.
        """
        values = []
        asynch_call_ids = []
        timeout = DeviceFactory().get_timeout_ms()
        # Read asynch
        for index, device in enumerate(self._items):
            device._ensure_initialized()
            asynch_call_id = device._attribute_dev.read_attribute_asynch(
                device._attr_name
            )
            asynch_call_ids.append(asynch_call_id)

        # Wait to read the set_point, ie the write part in a tango attribute.
        for index, call_id in enumerate(asynch_call_ids):
            device = self._items[index]
            dev_attr = device._attribute_dev.read_attribute_reply(call_id, timeout)
            if device.is_writable():
                values.append(dev_attr.w_value)
            else:
                values.append(dev_attr.value)

        return np.array(values)

    def readback(self) -> np.array:
        """
        Return the readback value of every attribute.

        Returns
        -------
        numpy.ndarray of float
            Readback values, one per managed attribute, in order.
        """
        values = []
        asynch_call_ids = []
        timeout = DeviceFactory().get_timeout_ms()
        # Readback with asynch optim
        for index, device in enumerate(self._items):
            device._ensure_initialized()
            asynch_call_id = device._attribute_dev.read_attribute_asynch(
                device._attr_name
            )
            asynch_call_ids.append(asynch_call_id)

        # Wait to read the value
        for index, call_id in enumerate(asynch_call_ids):
            dev_attr = self._items[index]._attribute_dev.read_attribute_reply(
                call_id, timeout
            )
            values.append(dev_attr.value)

        return np.array(values)

    def get_range(self) -> list[float]:
        """
        Return the valid ranges of all attributes.

        Returns
        -------
        list of float or None
            Flattened ``[min0, max0, min1, max1, ...]`` list, one pair per
            managed attribute, where an unbounded limit is ``None``.
        """
        attr_range: list[float] = []
        for device in self._items:
            attr_range.extend(device.get_range())
        return attr_range

    def check_device_availability(self) -> bool:
        """
        Check whether every managed device is reachable.

        Returns
        -------
        bool
            ``True`` if all devices answer, ``False`` at the first
            unreachable one (or if there is no item).
        """
        available = False
        for device in self._items:
            available = device.check_device_availability()
            if not available:
                break
        return available

    def unit(self) -> str:
        """
        Return the unit shared by the attributes.

        Returns
        -------
        str
            Unit string.
        """
        return self._unit

    def __repr__(self):
        return __pyaml_repr__(self)
