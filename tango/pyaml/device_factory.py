from threading import Lock
from collections import defaultdict
import tango


class DeviceFactory:
    """Singleton factory to build PyAML elements with future compatibility logic."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        No matter how many times you call DeviceFactory(), it will be created only once.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._elements = defaultdict()
                cls._instance._timeout = 3000  # in ms
            return cls._instance

    def set_timeout_ms(self, timeout: int):
        self._timeout = timeout

    def get_timeout_ms(self) -> int:
        return self._timeout

    def get_device(self, device_name: str) -> tango.DeviceProxy:
        if device_name not in self._elements:
            dp = tango.DeviceProxy(device_name)
            dp.set_timeout_millis(self._timeout)
            self._elements[device_name] = dp
        return self._elements[device_name]

    def clear(self):
        self._elements.clear()
