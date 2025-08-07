import random

from tango.pyaml.attribute_read_only import AttributeReadOnly
from .mocked_device_proxy import MockedDeviceProxy
from unittest.mock import patch
from tango.pyaml.attribute import Attribute
from tango.pyaml.multi_attribute import MultiAttribute


class TestMultiAttributes:

    def test_multi_read_write(self, config_multi):
        with patch("tango.DeviceProxy", new=MockedDeviceProxy):
                attr_list = MultiAttribute(config_multi)
                rand = random.Random()
                values = [rand.random() for _ in range(4)]
                attr_list.set_and_wait(values)
                vals = attr_list.readback()
                assert len(vals)==len(values)
                for index, val in enumerate(vals):
                    assert val == values[index]
