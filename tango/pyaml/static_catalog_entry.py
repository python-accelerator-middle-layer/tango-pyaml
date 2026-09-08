from pyaml.control.deviceaccess import DeviceAccess
from pyaml.validation import register_schema, DynamicValidation

PYAMLCLASS = "StaticCatalogEntry"


@register_schema
class StaticCatalogEntry(DynamicValidation):
    """
    A single key-to-device mapping in a static catalog.

    Parameters
    ----------
    key : str
        Catalog key used to look up the device.
    device : DeviceAccess
        Device access object returned when the key is resolved.
    """

    def __init__(self, key: str, device: DeviceAccess):
        self.key = key
        self.device = device

    def get_key(self) -> str:
        """Return the catalog key for this entry."""
        return self.key

    def get_device(self) -> DeviceAccess:
        """Return the device access object associated with this entry."""
        return self.device
