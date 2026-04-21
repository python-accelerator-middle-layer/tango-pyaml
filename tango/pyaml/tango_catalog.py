import tango
import pyaml

from pydantic import ConfigDict
from pyaml.configuration.catalog import Catalog, CatalogConfigModel, CatalogResolver
from pyaml.control.deviceaccess import DeviceAccess

from .attribute import Attribute, ConfigModel as AttributeConfigModel
from .attribute_read_only import AttributeReadOnly
from .tango_pyaml_utils import tango_to_PyAMLException, to_float_or_none

PYAMLCLASS = "TangoCatalog"


class ConfigModel(CatalogConfigModel):
    """
    Configuration model for a Tango catalog.

    Attributes
    ----------
    name : str
        Catalog identifier.
    disconnected : bool
        If true, resolve Tango attribute names without querying Tango.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    disconnected: bool = False


class TangoCatalog(Catalog):
    """
    Catalog resolving keys that are direct Tango attribute references.
    """

    def resolve(self, key: str) -> DeviceAccess:
        raise pyaml.PyAMLException(
            f"Tango catalog '{self.get_name()}' must be attached to a TangoControlSystem "
            f"before resolving key '{key}'"
        )

    def attach_control_system(self, control_system):
        from .controlsystem import TangoControlSystem

        if not isinstance(control_system, TangoControlSystem):
            raise pyaml.PyAMLException(
                f"Tango catalog '{self.get_name()}' can only be attached to TangoControlSystem"
            )
        return TangoCatalogResolver(self, control_system)


class TangoCatalogResolver(CatalogResolver):
    """
    Resolver bound to one TangoControlSystem.
    """

    _WRITABLE_TYPES = {
        tango.AttrWriteType.READ_WRITE,
        tango.AttrWriteType.WRITE,
        tango.AttrWriteType.READ_WITH_WRITE,
    }

    def __init__(self, catalog: TangoCatalog, control_system):
        self._catalog = catalog
        self._control_system = control_system
        # Resolved DeviceAccess objects are bound to one control system context,
        # so cache them in the resolver returned by attach_control_system().
        self._refs: dict[str, DeviceAccess] = {}
        self._data_formats: dict[str, tango.AttrDataFormat] = {}

    def resolve(self, key: str) -> DeviceAccess:
        """
        Resolve a Tango attribute reference into a DeviceAccess.
        """
        self._validate_key(key)

        if key not in self._refs:
            if self._catalog._cfg.disconnected:
                self._refs[key] = self._build_disconnected_attribute(key)
            else:
                self._refs[key] = self._build_connected_attribute(key)

        return self._refs[key]

    def get_data_format(self, key: str) -> tango.AttrDataFormat:
        """
        Return the Tango data format for a resolved attribute.
        """
        self.resolve(key)
        return self._data_formats[key]

    def _validate_key(self, key: str):
        if not isinstance(key, str):
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' expects string keys, got {type(key).__name__}"
            )

        parts = key.split("/")
        if len(parts) != 4 or any(part == "" for part in parts):
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot resolve invalid Tango attribute "
                f"reference '{key}'. Expected 'domain/family/member/attribute'."
            )

    def _build_disconnected_attribute(self, key: str) -> DeviceAccess:
        # In disconnected mode, keep all metadata local. In particular, setting
        # range avoids Attribute.get_range() from lazily querying Tango later.
        self._data_formats[key] = tango.AttrDataFormat.FMT_UNKNOWN
        return Attribute(AttributeConfigModel(attribute=key, range=(None, None)))

    def _build_connected_attribute(self, key: str) -> DeviceAccess:
        try:
            # AttributeProxy.get_config() is the most direct way to retrieve
            # writability, unit, range and data format from Tango.
            attr_config = tango.AttributeProxy(key).get_config()
        except tango.DevFailed as df:
            pyaml_exception = tango_to_PyAMLException(df)
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot resolve '{key}': {pyaml_exception}"
            ) from df

        unit = getattr(attr_config, "unit", "") or ""
        self._data_formats[key] = getattr(
            attr_config, "data_format", tango.AttrDataFormat.FMT_UNKNOWN
        )
        attr_range = (
            to_float_or_none(getattr(attr_config, "min_value", None)),
            to_float_or_none(getattr(attr_config, "max_value", None)),
        )
        cfg = AttributeConfigModel(attribute=key, unit=unit, range=attr_range)

        if getattr(attr_config, "writable", tango.AttrWriteType.WT_UNKNOWN) in self._WRITABLE_TYPES:
            return Attribute(cfg)
        return AttributeReadOnly(cfg)
