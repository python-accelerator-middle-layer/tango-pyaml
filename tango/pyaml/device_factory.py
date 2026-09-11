"""Shared cache of Tango device proxies."""

from collections import defaultdict
from threading import Lock

import tango


class DeviceFactory:
    """
    Singleton factory to build PyAML elements with future compatibility logic.

    The factory caches one :class:`tango.DeviceProxy` per device name so that
    every :class:`~tango.pyaml.attribute.Attribute` of the same device shares
    the same connection. It also holds the client timeout applied to every
    proxy it creates.

    Attributes
    ----------
    _instance : DeviceFactory or None
        The unique instance, created on first call.
    _lock : threading.Lock
        Lock protecting the instance creation.
    _elements : dict of str to tango.DeviceProxy
        Cache of device proxies indexed by device name.
    _timeout : int
        Client timeout in milliseconds applied to new proxies.

    Methods
    -------
    set_timeout_ms(timeout)
        Set the timeout applied to newly created device proxies.
    get_timeout_ms()
        Return the timeout applied to device proxies.
    get_device(device_name)
        Return the cached device proxy for a device, creating it if needed.
    clear()
        Drop all cached device proxies.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        Return the unique factory instance.

        No matter how many times you call ``DeviceFactory()``, it will be
        created only once.

        Returns
        -------
        DeviceFactory
            The singleton instance.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._elements = defaultdict()
                cls._instance._timeout = 3000  # in ms
            return cls._instance

    def set_timeout_ms(self, timeout: int):
        """
        Set the timeout applied to newly created device proxies.

        Proxies already in the cache keep their current timeout.

        Parameters
        ----------
        timeout : int
            Timeout in milliseconds.
        """
        self._timeout = timeout

    def get_timeout_ms(self) -> int:
        """
        Return the timeout applied to device proxies.

        Returns
        -------
        int
            Timeout in milliseconds.
        """
        return self._timeout

    def get_device(self, device_name: str) -> tango.DeviceProxy:
        """
        Return the cached device proxy for a device, creating it if needed.

        Parameters
        ----------
        device_name : str
            Tango device name (``domain/family/member``), optionally prefixed
            by ``//host:port/``.

        Returns
        -------
        tango.DeviceProxy
            Device proxy configured with the factory timeout.

        Raises
        ------
        tango.DevFailed
            If the device proxy cannot be created.
        """
        if device_name not in self._elements:
            dp = tango.DeviceProxy(device_name)
            dp.set_timeout_millis(self._timeout)
            self._elements[device_name] = dp
        return self._elements[device_name]

    def clear(self):
        """Drop all cached device proxies."""
        self._elements.clear()
