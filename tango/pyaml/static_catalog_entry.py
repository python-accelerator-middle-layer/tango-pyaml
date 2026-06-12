from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS = "StaticCatalogEntry"


class ConfigModel(BaseModel):
    """
    Configuration model for a static catalog entry.

    Attributes
    ----------
    key : str
        Catalog key used to look up the device.
    device : DeviceAccess
        Device access object returned when the key is resolved.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    key: str
    device: DeviceAccess


class StaticCatalogEntry:
    """
    A single key-to-device mapping in a static catalog.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration containing the key and device.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

    def get_key(self) -> str:
        """Return the catalog key for this entry."""
        return self._cfg.key

    def get_device(self) -> DeviceAccess:
        """Return the device access object associated with this entry."""
        return self._cfg.device
