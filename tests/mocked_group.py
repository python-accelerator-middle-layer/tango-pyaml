from .mocked_device_proxy import *

class MockedGroupReply:
    def __init__(self, dev_name, obj_name, error=None):
        self.dev_name = dev_name
        self.obj_name = obj_name
        self.err = error

    def has_failed(self):
        return self.err is not None

    def __repr__(self):
        return f"<MockedGroupReply device={self.dev_name}, obj_name={self.obj_name}, error={self.err}>"


class MockedGroupAttrReply(MockedGroupReply):
    def __init__(self, dev_name, obj_name, data:MockedDeviceAttribute = None, error=None):
        super().__init__(dev_name, obj_name, error)
        self.data = data

    def get_data(self) -> MockedDeviceAttribute:
        return self.data


class MockedGroupCmdReply(MockedGroupReply):
    def __init__(self, dev_name, obj_name, data = None, error=None):
        super().__init__(dev_name, obj_name, error)
        self.data = data

    def get_data(self):
        return self.data


class MockedGroup(MagicMock):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.devices = {}
        self.asynch_values = {}

    def add(self, device_name):
        proxy = MockedDeviceProxy(device_name)
        self.devices[device_name] = proxy
        return proxy

    def command_inout(self, command_name, *args, **kwargs):
        replies_id = {}
        replies = []
        for name, dev in self.devices.items():
            try:
                idx = dev.command_inout_asynch(command_name)
                replies_id[name] = idx
            except Exception as e:
                replies.append(MockedGroupCmdReply(name, command_name, None, e))
        for name, idx in replies_id.items():
            dev = self.devices[name]
            value = dev.command_inout_reply(idx)
            replies.append(MockedGroupCmdReply(dev.name(), command_name, value))
        return replies

    def read_attribute(self, attr_name) -> list[MockedGroupAttrReply]:
        replies_id = {}
        replies = []
        for name, dev in self.devices.items():
            try:
                idx = dev.read_attribute_asynch(attr_name)
                replies_id[name] = idx
            except Exception as e:
                replies.append(MockedGroupAttrReply(name, attr_name, None, e))
        for name, idx in replies_id.items():
            dev = self.devices[name]
            dev_attr = dev.read_attribute_reply(idx)
            replies.append(MockedGroupAttrReply(name, attr_name, dev_attr))
        return replies


    def read_attribute_asynch(self, attr_name) -> int:
        asynch_index = 0
        if len(self.asynch_values)>0:
            asynch_index = max(self.asynch_values.keys()) + 1
        self.asynch_values[asynch_index] = self.read_attribute(attr_name)
        return asynch_index


    def read_attribute_reply(self, idx):
        val = self.asynch_values[idx]
        del self.asynch_values[idx]
        return val


    def write_attribute(self, attr_name, value):
        replies = []
        for name, dev in self.devices.items():
            try:
                dev.write_attribute(attr_name, value)
                replies.append(MockedGroupReply(name, attr_name))
            except Exception as e:
                replies.append(MockedGroupReply(name, attr_name, e))
        return replies


    def write_attribute_asynch(self, attr_name, value) -> int:
        asynch_index = 0
        if len(self.asynch_values)>0:
            asynch_index = max(self.asynch_values.keys()) + 1
        self.write_attribute(attr_name, value)
        self.asynch_values[asynch_index] = None
        return asynch_index


    def write_attribute_reply(self, idx):
        del self.asynch_values[idx]
