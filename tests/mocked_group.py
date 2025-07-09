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


class MockedGroupAttrReply:
    def __init__(self, dev_name, obj_name, data:MockedDeviceAttribute = None, error=None, *args, **kwargs):
        super().__init__(dev_name, obj_name, error, *args, **kwargs)
        self.data = data

    def get_data(self) -> MockedDeviceAttribute:
        return self.data


class MockedGroupCmdReply:
    def __init__(self, dev_name, obj_name, data = None, error=None, *args, **kwargs):
        super().__init__(dev_name, obj_name, error, *args, **kwargs)
        self.data = data

    def get_data(self):
        return self.data


class MockedGroup(MagicMock):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.devices = {}

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
                replies_id[dev] = idx
            except Exception as e:
                replies.append(MockedGroupCmdReply(name, command_name, None, e))
        for dev, idx in replies_id:
            value = dev.command_inout_reply(idx)
            replies.append(MockedGroupCmdReply(dev.name(), command_name, value))
        return replies

    def read_attribute(self, attr_name):
        replies_id = {}
        replies = []
        for name, dev in self.devices.items():
            try:
                idx = dev.read_attribute_asynch(attr_name)
                replies_id[dev] = idx
            except Exception as e:
                replies.append(MockedGroupAttrReply(name, attr_name, None, e))
        for dev, idx in replies_id:
            dev_attr = dev.read_attribute_reply(idx)
            replies.append(MockedGroupAttrReply(dev.name(), attr_name, dev_attr))
        return replies

    def write_attribute(self, attr_name, value):
        replies = []
        for name, dev in self.devices.items():
            try:
                dev.write_attribute(attr_name, value)
                replies.append(MockedGroupReply(name, attr_name))
            except Exception as e:
                replies.append(MockedGroupReply(name, attr_name, e))
        return replies
