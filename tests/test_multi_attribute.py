import random

from .mocked_control_system_initialized import MockedControlSystemInitialized
from .mocked_device_proxy import MockedDeviceProxy
from unittest.mock import patch
from tango.pyaml.multi_attribute import MultiAttribute


class TestMultiAttributes:
    def test_multi_read_write(self, config_multi):
        with (
            patch("tango.DeviceProxy", new=MockedDeviceProxy),
            patch(
                "tango.pyaml.controlsystem.TangoControlSystem",
                new=MockedControlSystemInitialized,
            ),
        ):
            attr_list = MultiAttribute(config_multi)
            rand = random.Random()
            values = [rand.random() for _ in range(4)]
            attr_list.set(values)
            vals = attr_list.readback()
            assert len(vals) == len(values)
            for index, val in enumerate(vals):
                assert val == values[index]

    def test_multiattribute_range(self, config_multi_range):
        with (
            patch("tango.DeviceProxy", new=MockedDeviceProxy),
            patch(
                "tango.pyaml.controlsystem.TangoControlSystem",
                new=MockedControlSystemInitialized,
            ),
        ):
            ma = MultiAttribute(config_multi_range)
            attr_range = ma.get_range()
            assert attr_range is not None
            assert len(attr_range) == 8  # (4*2)
            assert attr_range == [-15, 15, -15, 15, -15, 15, -15, 15]
