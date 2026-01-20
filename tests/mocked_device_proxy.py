import tango
import numpy as np
from unittest.mock import MagicMock


class MockedAttributeInfoEx:
    def __init__(
        self,
        name,
        writable=tango.AttrWriteType.READ_WRITE,
        min_value: str = "",
        max_value: str = "",
    ):
        self.name = name
        self.writable = writable
        self.min_value = min_value
        self.max_value = max_value


class MockedDeviceAttribute:
    def __init__(self, name, value):
        self.value = value
        self.w_value = value
        self.name = name
        self.quality = tango.AttrQuality.ATTR_VALID
        self.time = tango.TimeVal.now()
        if isinstance(value, np.ndarray):
            if len(value.shape) == 1:
                self.data_format = tango.AttrDataFormat.SPECTRUM
                self.dim_x = value.shape[0]
                self.dim_y = 0
            else:
                self.data_format = tango.AttrDataFormat.IMAGE
                self.dim_x = value.shape[0]
                self.dim_y = value.shape[1]
        else:
            self.data_format = tango.AttrDataFormat.SCALAR
            self.dim_x = 0
            self.dim_y = 0
        self.w_dim_x = self.dim_x
        self.w_dim_y = self.dim_y
        """
        self.r_dimension : (tuple) Attribute read dimensions.
        self.w_dimension : (tuple) Attribute written dimensions.
        self.nb_read : (int) attribute read total length
        self.nb_written : (int) attribute written total length
        """


class MockedDeviceProxy(MagicMock):
    def __init__(self, device_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_name = device_name
        self.values = {
            "state": MockedDeviceAttribute("state", tango.DevState.ON),
            "status": MockedDeviceAttribute("status", ""),
        }
        self.asynch_values = {}

    def name(self) -> str:
        return self.device_name

    def state(self) -> tango.DevState:
        return self.read_attribute("state").value

    def status(self) -> str:
        return self.read_attribute("status").value

    def command_inout(self, cmd_name, cmd_param=None):
        return None

    def command_inout_asynch(self, cmd_name, cmd_param=None, forget=False):
        asynch_index = max(self.asynch_values.keys()) + 1
        if not forget:
            self.asynch_values[asynch_index] = self.command_inout(cmd_name, cmd_param)
        return asynch_index

    def command_inout_reply(self, idx, timeout=None):
        val = self.asynch_values.pop(idx)
        return val

    def read_attribute(self, attr_name: str):
        if attr_name not in self.values.keys():
            return MockedDeviceAttribute(attr_name, None)
        return self.values[attr_name]

    def write_attribute(self, attr_name, value):
        self.values[attr_name] = MockedDeviceAttribute(attr_name, value)

    def read_attribute_asynch(self, attr_name) -> int:
        asynch_index = 0
        if len(self.asynch_values) > 0:
            asynch_index = max(self.asynch_values.keys()) + 1
        self.asynch_values[asynch_index] = self.read_attribute(attr_name)
        return asynch_index

    def write_attribute_asynch(self, attr_name, value) -> int:
        asynch_index = 0
        if len(self.asynch_values) > 0:
            asynch_index = max(self.asynch_values.keys()) + 1
        self.write_attribute(attr_name, value)
        self.asynch_values[asynch_index] = None
        return asynch_index

    def read_attribute_reply(
        self, idx, extract_as=None, green_mode=None, wait=True
    ) -> MockedDeviceAttribute:
        val = self.asynch_values.pop(idx)
        return val

    # def read_attribute_reply(self, idx, poll_timeout, extract_as=None, green_mode=None, wait=True) -> MockedDeviceAttribute:
    #    return self.read_attribute_reply(idx, extract_as, green_mode, wait)

    def write_attribute_reply(self, idx, green_mode=None, wait=True):
        self.asynch_values.pop(idx)

    # def write_attribute_reply(self, idx, poll_timeout, green_mode=None, wait=True):
    #     self.write_attributes_reply(idx, green_mode, wait)

    def attribute_query(self, attr_name):
        return MockedAttributeInfoEx(attr_name)

    def get_attribute_config(self, attr_name, wait=True):
        return self.attribute_query(attr_name)

    def attribute_list_query(self):
        pass

    def set_timeout_millis(self, timeout: float):
        pass

    def ping(self, green_mode=None, wait=True, timeout=True) -> int:
        return 1


class MockedAttributeProxy(MagicMock):
    def __init__(self, attr_full_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attr_full_name = attr_full_name
        self.device_name, self._attr_name = attr_full_name.rsplit("/", 1)
        self.device_proxy = MockedDeviceProxy(self.device_name)

    def get_config(self, *args, **kwds):
        return self.device_proxy.get_attribute_config(self.name(), *args, **kwds)

    def read(self, *args, **kwds):
        return self.device_proxy.read_attribute(self.name(), *args, **kwds)

    def read_asynch(self, *args, **kwds) -> int:
        return self.device_proxy.read_attribute_asynch(self.name(), *args, **kwds)

    def read_reply(self, *args, **kwds) -> MockedDeviceAttribute:
        return self.device_proxy.read_attribute_reply(self.name(), *args, **kwds)

    def write(self, *args, **kwds):
        self.device_proxy.write_attribute(self.name(), *args, **kwds)

    def write_asynch(self, *args, **kwds) -> int:
        return self.device_proxy.write_attribute_asynch(self.name(), *args, **kwds)

    def write_reply(self, *args, **kwds):
        return self.device_proxy.write_attribute_reply(self.name(), *args, **kwds)

    def name(self):
        return self._attr_name

    def get_device_proxy(self):
        return self.device_proxy

    def ping(self):
        return self.device_proxy.ping()
