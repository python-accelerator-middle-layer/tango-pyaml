import logging
import os
from tango.pyaml.controlsystem import TangoControlSystem

from tango.pyaml.device_factory import DeviceFactory


def test_init_cs(caplog, config_tango_cs):
    # Capture logs
    with caplog.at_level(logging.DEBUG):
        tango_cs = TangoControlSystem(config_tango_cs)
        tango_cs.init_cs()

    # Check tango host
    assert os.environ["TANGO_HOST"] == "tangodb:10000"

    expected_message = (f"Tango control system binding for PyAML initialized with name '{config_tango_cs.name}'"
                        f" and TANGO_HOST={config_tango_cs.tango_host}")

    # Check that the INFO init message was actually logged with correct values
    assert any(expected_message == record.message for record in caplog.records)

def test_factory():
    factory1 = DeviceFactory()
    factory2 = DeviceFactory()

    assert factory1 is factory2
