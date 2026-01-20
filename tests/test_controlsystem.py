import logging

from tango.pyaml.controlsystem import TangoControlSystem


from .mocked_device_proxy import MockedDeviceProxy
from unittest.mock import patch
from tango.pyaml.attribute import Attribute
from tango.pyaml import __version__


def test_init_cs(caplog, config_tango_cs):
    # Capture logs
    with caplog.at_level(logging.INFO):
        TangoControlSystem(config_tango_cs)

    expected_message = (
        f"PyAML Tango control system binding ({__version__}) initialized with name '{config_tango_cs.name}'"
        f" and TANGO_HOST={config_tango_cs.tango_host}"
    )

    # Check that the INFO init message was actually logged with correct values
    assert any(expected_message == record.message for record in caplog.records)


def test_laziness_init_cs_attribute(config_tango_cs_lazy_default, config):
    with patch("tango.DeviceProxy", side_effect=MockedDeviceProxy) as mock_ctor:
        attr = Attribute(config)
        mock_ctor.assert_not_called()
        attr.set_and_wait(42.0)
        mock_ctor.assert_called_once()
        attr.set_and_wait(42.0)
        mock_ctor.assert_called_once()
        assert attr.get() == 42.0
