import pyaml.control.readback_value
import pytest

from tango.pyaml.attribute_read_only import AttributeReadOnly

from .mocked_control_system_initialized import MockedControlSystemInitialized
from .mocked_device_proxy import *
from .mocked_group import MockedGroup
from unittest.mock import patch
from tango.pyaml.attribute import Attribute
from tango.pyaml.attribute_list import AttributeList


class MockedReadExceptDeviceProxy(MockedDeviceProxy):
    def read_attribute(self, name):
        raise tango.Except.throw_exception(
            "mocked reason", f"mocked desc for attr {name}", "mocked origin"
        )


class MockedROAttrDeviceProxy(MockedDeviceProxy):
    def attribute_query(self, name):
        attr_ro_info = MockedAttributeInfoEx(name, tango.AttrWriteType.READ)
        return attr_ro_info


class TestAttributes:
    def test_attribute_get_set(self, config):
        with (
            patch("tango.DeviceProxy", new=MockedDeviceProxy),
            patch(
                "tango.pyaml.controlsystem.TangoControlSystem",
                new=MockedControlSystemInitialized,
            ),
        ):
            attr = Attribute(config)
            attr.set_and_wait(42.0)
            assert attr.get() == 42.0
            assert attr.readback() == 42.0
            assert attr.readback().timestamp is not None
            assert attr.readback().quality is pyaml.control.readback_value.Quality.VALID

            # Test infos
            assert attr.unit() == "A"
            assert attr.name() == "sys/tg_test/1/float_scalar"
            assert attr.measure_name() == "float_scalar"

    def test_attribute_except(self, config):
        with (
            patch("tango.DeviceProxy", new=MockedReadExceptDeviceProxy),
            patch(
                "tango.pyaml.controlsystem.TangoControlSystem",
                new=MockedControlSystemInitialized,
            ),
        ):
            attr = Attribute(config)
            with pytest.raises(pyaml.PyAMLException) as exc:
                attr.readback()
            assert exc is not None

    def test_attribute_read_only(self, config):
        with (
            patch("tango.DeviceProxy", new=MockedROAttrDeviceProxy),
            patch(
                "tango.pyaml.controlsystem.TangoControlSystem",
                new=MockedControlSystemInitialized,
            ),
        ):
            # Cannot create an attribute with a read-only tango attribute.
            expected_message = (
                "Tango attribute sys/tg_test/1/float_scalar is not writable."
            )
            attr1 = Attribute(config)
            with pytest.raises(pyaml.PyAMLException) as exc:
                attr1.get()
            assert exc.value.message == expected_message

            # Read-only attributes cannot be sets.
            attr = AttributeReadOnly(config)
            with pytest.raises(pyaml.PyAMLException) as exc2:
                attr.set(10)
            assert exc2.value.message == expected_message

    def test_group_read_write(self, config_group):
        with (
            patch("tango.Group", new=MockedGroup),
            patch(
                "tango.pyaml.controlsystem.TangoControlSystem",
                new=MockedControlSystemInitialized,
            ),
        ):
            attr_list = AttributeList(config_group)
            attr_list.set_and_wait(10)
            vals = attr_list.readback()
            for val in vals:
                assert val == 10

    def test_unique_device(self, config):
        with (
            patch("tango.DeviceProxy", new=MockedDeviceProxy),
            patch(
                "tango.pyaml.controlsystem.TangoControlSystem",
                new=MockedControlSystemInitialized,
            ),
        ):
            attr1 = Attribute(config)
            attr2 = Attribute(config)
            assert attr1._attribute_dev is attr2._attribute_dev
