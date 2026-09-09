from pyaml import PyAMLException
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.validation import DynamicValidation, register_schema

from .catalog import Catalog
from .static_catalog_entry import StaticCatalogEntry

PYAMLCLASS = "StaticCatalog"


@register_schema
class StaticCatalog(Catalog, DynamicValidation):
    """
    Catalog backed by a fixed list of key-to-device mappings.

    All entries are validated at construction time: the list must be
    non-empty and every key must be unique. Resolution is an O(1) dictionary
    lookup; no Tango connection is required.

    Parameters
    ----------
    name : str
        Catalog identifier.
    entries : list[StaticCatalogEntry]
        Explicit list of key-to-device mappings. Must contain at least one
        entry, and keys must be unique within the catalog.

    Raises
    ------
    pyaml.PyAMLException
        If ``cfg.entries`` is empty or contains duplicate keys.
    """

    def __init__(self, entries: list[StaticCatalogEntry]):
        super().__init__()

        self._entries = entries
        if len(self._entries) == 0:
            raise PyAMLException(
                "StaticCatalog.entries must contain at least one entry"
            )
        self._refs: dict[str, DeviceAccess] = {}
        for entry in self._entries:
            key = entry.get_key()
            if key in self._refs:
                raise PyAMLException(
                    f"StaticCatalog.entries contains duplicate key '{key}'"
                )
            self._refs[key] = entry.get_device()

    def resolve(self, key: str, control_system: object | None = None) -> DeviceAccess:
        """
        Return the device associated with ``key``.

        Parameters
        ----------
        key : str
            Catalog key to resolve.
        control_system : object | None
            Optional backend context. Static catalogs do not need it, but the
            argument keeps the backend catalog API uniform.

        Returns
        -------
        DeviceAccess
            The device access object registered under ``key``.

        Raises
        ------
        pyaml.PyAMLException
            If ``key`` is not present in the catalog.
        """
        try:
            return self._refs[key]
        except KeyError as exc:
            raise PyAMLException(f"Catalog cannot resolve key '{key}'") from exc
