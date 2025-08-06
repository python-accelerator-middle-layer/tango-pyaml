from threading import Lock
from collections import defaultdict
import tango


class DeviceFactory:
    """Singleton factory to build PyAML elements with future compatibility logic."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        No matter how many times you call PyAMLFactory(), it will be created only once.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._elements = defaultdict()
            return cls._instance

    def get_device(self, device_name:str) -> tango.DeviceProxy:
        if device_name not in self._elements:
            self._elements[device_name] = tango.DeviceProxy(device_name)
        return self._elements[device_name]

    def clear(self):
        self._elements.clear()

TangoDeviceFactory = DeviceFactory()
