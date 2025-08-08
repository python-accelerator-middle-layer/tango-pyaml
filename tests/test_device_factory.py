from tango.pyaml.device_factory import DeviceFactory

def test_factory():
    factory1 = DeviceFactory()
    factory2 = DeviceFactory()

    assert factory1 is factory2
