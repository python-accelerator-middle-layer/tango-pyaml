import pytest
from .mocked_device_proxy import *

from unittest.mock import patch
from tango.pyaml.attribute import Attribute
from .mocked_control_system_initialized import MockedControlSystemInitialized


class MockedMinMaxAttrDeviceProxy(MockedDeviceProxy):
    def attribute_query(self, name):
        attr_info = MockedAttributeInfoEx(name, tango._tango.AttrWriteType.READ_WRITE, "-10", "10")
        return attr_info

class MockedMinAttrDeviceProxy(MockedDeviceProxy):
    def attribute_query(self, name):
        attr_info = MockedAttributeInfoEx(name, tango._tango.AttrWriteType.READ_WRITE, "-10", "")
        return attr_info


def test_attribute_range_by_conf(config_range):
    with (patch("tango.DeviceProxy", new=MockedDeviceProxy),
          patch("tango.pyaml.controlsystem.TangoControlSystem", new=MockedControlSystemInitialized)):
        attr = Attribute(config_range)

        attr_range = attr.get_range()
        assert attr_range is not None
        assert len(attr_range) == 2
        assert attr_range[0] == -15 and attr_range[1] == 15


def test_attribute_range_by_conf_with_null(config_range_with_null):
    with (patch("tango.DeviceProxy", new=MockedDeviceProxy),
          patch("tango.pyaml.controlsystem.TangoControlSystem", new=MockedControlSystemInitialized)):
        attr = Attribute(config_range_with_null)

        attr_range = attr.get_range()
        assert attr_range is not None
        assert len(attr_range) == 2
        assert attr_range[0] == 0 and attr_range[1] == None


def test_attribute_range_by_device(config):
    with (patch("tango.DeviceProxy", new=MockedMinMaxAttrDeviceProxy),
          patch("tango.pyaml.controlsystem.TangoControlSystem", new=MockedControlSystemInitialized)):
        attr = Attribute(config)

        attr_range = attr.get_range()
        assert attr_range is not None
        assert len(attr_range) == 2
        assert attr_range[0] == -10 and attr_range[1] == 10


def test_attribute_range_by_device_min_only(config):
    with (patch("tango.DeviceProxy", new=MockedMinAttrDeviceProxy),
          patch("tango.pyaml.controlsystem.TangoControlSystem", new=MockedControlSystemInitialized)):
        attr = Attribute(config)

        attr_range = attr.get_range()
        assert attr_range is not None
        assert len(attr_range) == 2
        assert attr_range[0] == -10 and attr_range[1] == None
