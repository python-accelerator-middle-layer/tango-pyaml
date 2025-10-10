import logging
import os

import pyaml
import pytest
from tango.pyaml.controlsystem import TangoControlSystem

from tango.pyaml.attribute_read_only import AttributeReadOnly

from .mocked_device_proxy import *
from unittest.mock import patch
from tango.pyaml.attribute import Attribute
from tango.pyaml.attribute_list import AttributeList


def test_init_cs(caplog, config_tango_cs):
    # Capture logs
    with caplog.at_level(logging.INFO):
        tango_cs = TangoControlSystem(config_tango_cs)
        tango_cs.init_cs()

    # Check tango host
    assert os.environ["TANGO_HOST"] == "tangodb:10000"

    expected_message = (f"Tango control system binding for PyAML initialized with name '{config_tango_cs.name}'"
                        f" and TANGO_HOST={config_tango_cs.tango_host}")

    # Check that the INFO init message was actually logged with correct values
    assert any(expected_message == record.message for record in caplog.records)

def test_cs_singleton(caplog, config_tango_cs, config_tango_cs_false):
    tango_cs1 = TangoControlSystem(config_tango_cs)
    tango_cs1.init_cs()

    with caplog.at_level(logging.WARNING):
        tango_cs2 = TangoControlSystem(config_tango_cs_false)
        tango_cs2.init_cs()

    # Check tango host matches tango_cs1
    assert tango_cs1 is tango_cs2
    assert os.environ["TANGO_HOST"] == "tangodb:10000"
    expected_message = (f"Tango control system binding for PyAML was already initialized"
                        f" with name '{config_tango_cs.name}' and TANGO_HOST={config_tango_cs.tango_host}")

    # Check that the INFO init message was actually logged with correct values
    assert any(expected_message == record.message for record in caplog.records)

def test_init_cs_attribute(config_tango_cs, config):
    tango_cs = TangoControlSystem(config_tango_cs)
    with patch("tango.DeviceProxy", new=MockedDeviceProxy):
        attr = Attribute(config)
        with pytest.raises(pyaml.PyAMLException) as exc:
            attr.set_and_wait(42.0)
        expected_message = f"The attribute {attr.name()} is not initialized."
        assert exc.value.message == expected_message
        tango_cs.init_cs()
        attr.set_and_wait(42.0)
        assert attr.get() == 42.0


def test_laziness_init_cs_attribute(config_tango_cs_lazy_default, config):
    tango_cs = TangoControlSystem(config_tango_cs_lazy_default)
    with patch("tango.DeviceProxy", side_effect=MockedDeviceProxy) as mock_ctor:
        attr = Attribute(config)
        mock_ctor.assert_not_called()
        tango_cs.init_cs()
        mock_ctor.assert_not_called()
        attr.set_and_wait(42.0)
        mock_ctor.assert_called_once()
        attr.set_and_wait(42.0)
        mock_ctor.assert_called_once()
        assert attr.get() == 42.0


def test_laziness_init_cs_go_eager(config_tango_cs_lazy_default, config):
    tango_cs = TangoControlSystem(config_tango_cs_lazy_default)
    with patch("tango.DeviceProxy", side_effect=MockedDeviceProxy) as mock_ctor:
        attr = Attribute(config)
        mock_ctor.assert_not_called()
        tango_cs.init_cs()
        tango_cs.warmup()
        mock_ctor.assert_called_once()
        attr.set_and_wait(42.0)
        assert attr.get() == 42.0
