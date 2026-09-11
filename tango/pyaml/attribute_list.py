"""
Grouped Tango attribute access.

This module handles a list of Tango attributes through :class:`tango.Group`
objects, one per distinct attribute name, so that a value can be written to or
read from many devices in a single call.
"""

import logging

from numpy import array
from pydantic import BaseModel

import pyaml
import tango
from pyaml.common.element import __pyaml_repr__
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Quality, Value
from pyaml.validation import DynamicValidation, register_schema

from .initializable_element import InitializableElement
from .tango_pyaml_utils import to_float_or_none

PYAMLCLASS: str = "AttributeList"

logger = logging.getLogger(__name__)


class AttributeListConfig(BaseModel):
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
    """

    attributes: list[str]
    name: str = ""
    unit: str = ""


@register_schema
class AttributeList(DeviceAccess, InitializableElement, DynamicValidation):
    """
    Handle a list of Tango attributes using Tango Groups.

    Attributes are grouped by attribute name: one :class:`tango.Group` is
    created per distinct attribute name and holds every device exposing it.
    Groups are created lazily on first access.

    Parameters
    ----------
    attributes : list of str
        List of Tango attribute paths.
    name : str, optional
        Group name.
    unit : str, optional
        Unit of the attributes.

    Attributes
    ----------
    _attributes : list of str
        Tango attribute paths in configured order.
    _name : str
        Group name.
    _unit : str
        Unit of the attributes.
    _tango_groups : dict of str to tango.Group
        Tango groups indexed by attribute name, created on initialization.
    _attr_dev : dict of str to list of str
        Device names indexed by attribute name.

    Methods
    -------
    initialize()
        Create one Tango group per attribute name.
    name()
        Return the group name.
    measure_name()
        Return the group name (alias for measurement name).
    get_tango_attributes()
        Return the raw Tango attribute paths stored in the configuration.
    set(value)
        Write a value asynchronously to all Tango attributes.
    set_and_wait(value)
        Write a value synchronously to all Tango attributes.
    get()
        Return the last written values of all attributes.
    readback()
        Return readback values with metadata for all attributes.
    unit()
        Return the unit for the attribute list.
    get_range()
        Return the valid ranges of the attributes.
    check_device_availability()
        Check whether every device of the groups answers to a ping.
    """

    def __init__(self, attributes: list[str], name: str = "", unit: str = ""):
        super().__init__()

        self._attributes = attributes
        self._name = name
        self._unit = unit

        self._tango_groups: dict[str, tango.Group] = {}
        self._attr_dev: dict[str, list[str]] = {}

        for attribute in self._attributes:
            attribute_dev_name, attr_name = attribute.rsplit("/", 1)
            if attr_name not in self._attr_dev:
                self._attr_dev[attr_name] = []
            if attribute_dev_name not in self._attr_dev[attr_name]:
                self._attr_dev[attr_name].append(attribute_dev_name)

    def initialize(self):
        """
        Create one Tango group per attribute name.

        Each group is named after the list and populated with the devices
        exposing that attribute.
        """
        super().initialize()
        for attr_name, dev_list in self._attr_dev.items():
            self._tango_groups[attr_name] = tango.Group(self._name)
            [self._tango_groups[attr_name].add(dev) for dev in dev_list]

    def name(self) -> str:
        """
        Return the group name.

        Returns
        -------
        str
            Group name.
        """
        return self._name

    def measure_name(self) -> str:
        """
        Return the group name (alias for measurement name).

        Returns
        -------
        str
            Group name.
        """
        return self._name

    def get_tango_attributes(self) -> list[str]:
        """
        Return the raw Tango attribute paths stored in the configuration.

        Returns
        -------
        list of str
            Tango attribute paths in configured order.
        """
        return self._attributes

    def set(self, value: float):
        """
        Write a value asynchronously to all Tango attributes.

        Parameters
        ----------
        value : float
            Value to write.
        """
        self._ensure_initialized()
        logger.log(
            logging.DEBUG, f"Setting asynchronously list {self.name()} to {value}"
        )
        [
            group.write_attribute_asynch(attr_name, value)
            for attr_name, group in self._tango_groups.items()
        ]

    def set_and_wait(self, value: float):
        """
        Write a value synchronously to all Tango attributes.

        Parameters
        ----------
        value : float
            Value to write.
        """
        self._ensure_initialized()
        logger.log(logging.DEBUG, f"Setting list {self.name()} to {value}")
        [
            group.write_attribute(attr_name, value)
            for attr_name, group in self._tango_groups.items()
        ]

    def get(self) -> array:
        """
        Return the last written values of all attributes.

        Returns
        -------
        numpy.ndarray
            Array of last written values ordered as in configuration. Entries
            whose read failed are ``None``.
        """
        self._ensure_initialized()
        result = {}
        grp_vals = [
            group.read_attribute(attr_name)
            for attr_name, group in self._tango_groups.items()
        ]
        for vals in grp_vals:
            for val in vals:
                attr_value = val.data
                if attr_value is not None:
                    result[val.dev_name + "/" + val.obj_name] = attr_value.w_value
                else:
                    result[val.dev_name + "/" + val.obj_name] = None
        return array([result[attribute] for attribute in self._attributes])

    def readback(self) -> array:
        """
        Return readback values with metadata for all attributes.

        Returns
        -------
        numpy.ndarray
            Array of :class:`~pyaml.control.readback_value.Value` objects
            ordered as in configuration. Entries whose read failed are
            ``None``.
        """
        self._ensure_initialized()
        logger.log(logging.DEBUG, f"Reading list {self.name()}")
        result = {}
        grp_vals = [
            group.read_attribute(attr_name)
            for attr_name, group in self._tango_groups.items()
        ]
        for vals in grp_vals:
            for val in vals:
                attr_value = val.data
                if attr_value is not None:
                    quality = Quality[
                        attr_value.quality.name.rsplit("_", 1)[1]
                    ]  # AttrQuality.ATTR_VALID gives Quality.VALID
                    value = Value(
                        attr_value.value, quality, attr_value.time.todatetime()
                    )
                    result[val.dev_name + "/" + val.obj_name] = value
                else:
                    result[val.dev_name + "/" + val.obj_name] = None
        list_res = [result[attribute] for attribute in self._attributes]
        return array(list_res)

    def unit(self) -> str:
        """
        Return the unit for the attribute list.

        Returns
        -------
        str
            Unit string.
        """
        return self._unit

    def get_range(self) -> list[float]:
        """
        Return the valid ranges of the attributes.

        If a ``_range`` is configured it is returned as ``[min, max]``.
        Otherwise the limits are read from the Tango attribute configuration
        of every device and returned flattened as
        ``[min0, max0, min1, max1, ...]``, in group order.

        Returns
        -------
        list of float or None
            Range limits, where an unbounded limit is ``None``.
        """
        attr_range: list[float] = [None, None]
        if self._range is not None:
            attr_range[0] = self._range[0] if self._range[0] is not None else None
            attr_range[1] = self._range[1] if self._range[1] is not None else None
        else:
            self._ensure_initialized()
            devices: list[tango.DeviceProxy] = []
            [
                devices.extend(group.get_device_list())
                for group in self._tango_groups.values()
            ]
            attr_confs = [dev.get_attribute_config() for dev in devices]
            attr_range: list[float] = []
            for conf in attr_confs:
                attr_range.append(to_float_or_none(conf.min_value))
                attr_range.append(to_float_or_none(conf.max_value))

        return attr_range

    def check_device_availability(self) -> bool:
        """
        Check whether every device of the groups answers to a ping.

        Returns
        -------
        bool
            ``True`` if all devices are reachable, ``False`` if initialization
            or any ping fails.
        """
        available = True
        try:
            self._ensure_initialized()
            [group.ping() for group in self._tango_groups.values()]
        except (tango.DevFailed, pyaml.PyAMLException):
            available = False
        return available

    def __repr__(self):
        return __pyaml_repr__(self)
