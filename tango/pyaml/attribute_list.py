import logging

import pyaml
from numpy import array
from pydantic import BaseModel
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value, Quality
import tango

from .controlsystem import TangoControlSystem
from .initializable_element import InitializableElement

PYAMLCLASS : str = "AttributeList"

logger = logging.getLogger(__name__)

class ConfigModel(BaseModel):
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

class AttributeList(DeviceAccess, InitializableElement):
    """
    Handle a list of Tango attributes using Tango Groups.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration object with attribute list, name and unit.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        self._tango_groups:dict[str,tango.Group] = {}
        self._attr_dev:dict[str,list[str]] = {}

        for attribute in self._cfg.attributes:
            attribute_dev_name, attr_name = attribute.rsplit("/", 1)
            if attr_name not in self._attr_dev.keys():
                self._attr_dev[attr_name] = []
            if attribute_dev_name not in self._attr_dev[attr_name]:
                self._attr_dev[attr_name].append(attribute_dev_name)

        if TangoControlSystem.is_initialized():
            self.initialize()
        else:
            TangoControlSystem.get_instance().add_initializable(self)


    def initialize(self):
        super().initialize()
        for attr_name, dev_list in self._attr_dev.items():
            self._tango_groups[attr_name] = tango.Group(self._cfg.name)
            [self._tango_groups[attr_name].add(dev) for dev in dev_list]


    def name(self) -> str:
        """
        Return the group name.

        Returns
        -------
        str
            Group name.
        """
        return self._cfg.name


    def measure_name(self) -> str:
        """
        Return the group name (alias for measurement name).

        Returns
        -------
        str
            Group name.
        """
        return self._cfg.name


    def set(self, value: float):
        """
        Write a value asynchronously to all Tango attributes.

        Parameters
        ----------
        value : float
            Value to write.
        """
        if not self.is_initialized():
            raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
        logger.log(logging.DEBUG, f"Setting asynchronously list {self.name()} to {value}")
        [group.write_attribute_asynch(attr_name, value) for attr_name, group in self._tango_groups.items()]


    def set_and_wait(self, value: float):
        """
        Write a value synchronously to all Tango attributes.

        Parameters
        ----------
        value : float
            Value to write.
        """
        if not self.is_initialized():
            raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
        logger.log(logging.DEBUG, f"Setting list {self.name()} to {value}")
        [group.write_attribute(attr_name, value) for attr_name, group in self._tango_groups.items()]


    def get(self) -> array:
        """
        Return the last written values of all attributes.

        Returns
        -------
        numpy.array
            Array of last written values ordered as in configuration.
        """
        if not self.is_initialized():
            raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
        result = {}
        grp_vals = [group.read_attribute(attr_name) for attr_name, group in self._tango_groups.items()]
        for vals in grp_vals:
            for val in vals:
                attr_value = val.data
                if attr_value is not None:
                    result[val.dev_name + '/' + val.obj_name] = attr_value.w_value
                else:
                    result[val.dev_name + '/'+ val.obj_name] = None
        return array([result[attribute] for attribute in self._cfg.attributes])


    def readback(self) -> array:
        """
        Return readback values with metadata for all attributes.

        Returns
        -------
        numpy.array
            Array of Value objects ordered as in configuration.
        """
        if not self.is_initialized():
            raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
        logger.log(logging.DEBUG, f"Reading list {self.name()}")
        result = {}
        grp_vals = [group.read_attribute(attr_name) for attr_name, group in self._tango_groups.items()]
        for vals in grp_vals:
            for val in vals:
                attr_value = val.data
                if attr_value is not None:
                    quality = Quality[attr_value.quality.name.rsplit('_', 1)[1]] # AttrQuality.ATTR_VALID gives Quality.VALID
                    value = Value(attr_value.value, quality, attr_value.time.todatetime() )
                    result[val.dev_name + '/' + val.obj_name] = value
                else:
                    result[val.dev_name + '/' + val.obj_name] = None
        list_res = [result[attribute] for attribute in self._cfg.attributes]
        return array(list_res)


    def unit(self) -> str:
        """
        Return the unit for the attribute list.

        Returns
        -------
        str
            Unit string.
        """
        return self._cfg.unit

