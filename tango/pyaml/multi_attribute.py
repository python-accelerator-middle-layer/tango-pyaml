import logging

import numpy as np
import pyaml
from numpy import typing as npt
from pyaml.control.deviceaccess import DeviceAccess
from pydantic import BaseModel

from pyaml.control.deviceaccesslist import DeviceAccessList

from .attribute import Attribute, ConfigModel as AttrConfig
from .device_factory import DeviceFactory

PYAMLCLASS : str = "MultiAttribute"

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
    attributes: list[str] = []
    name: str = ""
    unit: str = ""

class MultiAttribute(DeviceAccessList):

    def __init__(self, cfg:ConfigModel=None):
        super().__init__()
        self._cfg = cfg
        if self._cfg:
            for attribute in self._cfg.attributes:
                attr_config = AttrConfig(attribute=attribute, unit=self._cfg.unit)
                attr = Attribute(attr_config)
                self.append(attr)

    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        if isinstance(devices, list):
            if any([not isinstance(device, Attribute) for device in devices]):
                raise pyaml.PyAMLException("All devices must be instances of Attribute (tango.pyaml.attribute).")
            super().extend(devices)
        else:
            if not isinstance(devices, Attribute):
                raise pyaml.PyAMLException("Device must be an instance of Attribute (tango.pyaml.attribute).")
            super().append(devices)

    def get_devices(self) -> DeviceAccess | list[DeviceAccess]:
        if len(self)==1:
            return self[0]
        else:
            return self

    def set(self, value: npt.NDArray[np.float64]):
        if len(value)!=len(self):
            raise pyaml.PyAMLException(f"Size of value ({len(value)} do not match the number of managed devices ({len(self)})")
        asynch_call_ids = []
        timeout = DeviceFactory().get_timeout_ms()
        # Set part
        for index, device in enumerate(self):
            device._ensure_initialized()
            asynch_call_id = device._attribute_dev.write_attribute_asynch(device._attr_name, value[index])
            asynch_call_ids.append(asynch_call_id)

        # Wait part
        for index, call_id in enumerate(asynch_call_ids):
            self[index]._attribute_dev.write_attribute_reply(call_id,timeout)

    def set_and_wait(self, value: npt.NDArray[np.float64]):
        raise NotImplemented("Not implemented yet.")

    def get(self) -> npt.NDArray[np.float64]:
        values = []
        asynch_call_ids = []
        timeout = DeviceFactory().get_timeout_ms()
        # Read asynch
        for index, device in enumerate(self):
            device._ensure_initialized()
            asynch_call_id = device._attribute_dev.read_attribute_asynch(device._attr_name)
            asynch_call_ids.append(asynch_call_id)

        # Wait to read the set_point, ie the write part in a tango attribute.
        for index, call_id in enumerate(asynch_call_ids):
            dev_attr = self[index]._attribute_dev.read_attribute_reply(call_id,timeout)
            if self[index].is_writable():
                values.append(dev_attr.w_value)
            else:
                values.append(dev_attr.value)

        return np.array(values)

    def readback(self) -> np.array:
        values = []
        asynch_call_ids = []
        timeout = DeviceFactory().get_timeout_ms()
        # Readback with asynch optim
        for index, device in enumerate(self):
            device._ensure_initialized()
            asynch_call_id = device._attribute_dev.read_attribute_asynch(device._attr_name)
            asynch_call_ids.append(asynch_call_id)

        # Wait to read the value
        for index, call_id in enumerate(asynch_call_ids):
            dev_attr = self[index]._attribute_dev.read_attribute_reply(call_id,timeout)
            values.append(dev_attr.value)

        return np.array(values)

    def unit(self) -> str:
        if self._cfg:
            return self._cfg.unit
        else:
            return ""

    def __repr__(self):
       return repr(self._cfg).replace("ConfigModel",self.__class__.__name__)