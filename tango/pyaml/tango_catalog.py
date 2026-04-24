import tango
import pyaml

from pydantic import ConfigDict
from pyaml.configuration.catalog import Catalog, CatalogConfigModel, CatalogResolver
from pyaml.control.deviceaccess import DeviceAccess

from .attribute import Attribute, ConfigModel as AttributeConfigModel
from .attribute_read_only import AttributeReadOnly
from .attribute_indexed import AttributeIndexed, ConfigModel as IndexedConfigModel
from .attribute_indexed_read_only import AttributeIndexedReadOnly
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

    Keys can be plain Tango attribute paths (``domain/family/member/attribute``)
    or indexed references into a SPECTRUM attribute
    (``domain/family/member/attribute@index``).
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

    Supports two key formats:

    - ``domain/family/member/attribute`` — resolves to a scalar
      :class:`~tango.pyaml.attribute.Attribute` or
      :class:`~tango.pyaml.attribute_read_only.AttributeReadOnly`.
    - ``domain/family/member/attribute@index`` — resolves to a scalar view
      of one element in a SPECTRUM attribute
      (:class:`~tango.pyaml.attribute_indexed.AttributeIndexed` or
      :class:`~tango.pyaml.attribute_indexed_read_only.AttributeIndexedReadOnly`).

    In connected mode (``disconnected=False``) indexed keys additionally verify
    that the Tango attribute is a SPECTRUM.
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

        Parameters
        ----------
        key : str
            Plain attribute path or indexed path (``attribute@index``).

        Returns
        -------
        DeviceAccess
            Resolved device access, cached for subsequent calls.

        Raises
        ------
        pyaml.PyAMLException
            If the key is malformed, the Tango call fails, or (in connected
            mode) an indexed key targets a non-SPECTRUM attribute.
        """
        attr_path, index = self._parse_key(key)

        if key not in self._refs:
            if index is not None:
                if self._catalog._cfg.disconnected:
                    self._refs[key] = self._build_disconnected_indexed(attr_path, index)
                else:
                    self._refs[key] = self._build_connected_indexed(attr_path, index)
            else:
                if self._catalog._cfg.disconnected:
                    self._refs[key] = self._build_disconnected_attribute(key)
                else:
                    self._refs[key] = self._build_connected_attribute(key)

        return self._refs[key]

    def get_data_format(self, key: str) -> tango.AttrDataFormat:
        """
        Return the Tango data format for a resolved attribute.

        Parameters
        ----------
        key : str
            Catalog key (must have been resolved at least once, or will be
            resolved now).

        Returns
        -------
        tango.AttrDataFormat
            Data format reported by Tango, or ``FMT_UNKNOWN`` in disconnected
            mode.
        """
        self.resolve(key)
        return self._data_formats[key]

    def _parse_key(self, key: str) -> tuple[str, int | None]:
        """
        Validate and split a catalog key into ``(attr_path, index)``.

        The ``index`` is ``None`` for plain attribute paths and an integer for
        indexed paths (``attr_path@index``).

        Raises
        ------
        pyaml.PyAMLException
            If the key is not a string, the attribute path does not have
            exactly four slash-separated components, or the index suffix is
            not a valid integer.
        """
        if not isinstance(key, str):
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' expects string keys, "
                f"got {type(key).__name__}"
            )

        if "@" in key:
            attr_path, idx_str = key.rsplit("@", 1)
            try:
                index = int(idx_str)
            except ValueError:
                raise pyaml.PyAMLException(
                    f"Tango catalog '{self._catalog.get_name()}' invalid index "
                    f"'{idx_str}' in key '{key}'."
                )
        else:
            attr_path = key
            index = None

        parts = attr_path.split("/")
        if len(parts) != 4 or any(part == "" for part in parts):
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot resolve invalid Tango attribute "
                f"reference '{key}'. Expected 'domain/family/member/attribute' or "
                f"'domain/family/member/attribute@index'."
            )

        return attr_path, index

    def _build_disconnected_attribute(self, key: str) -> DeviceAccess:
        # In disconnected mode, keep all metadata local. In particular, setting
        # range avoids Attribute.get_range() from lazily querying Tango later.
        self._data_formats[key] = tango.AttrDataFormat.FMT_UNKNOWN
        return Attribute(AttributeConfigModel(attribute=key, range=(None, None)))

    def _build_disconnected_indexed(self, attr_path: str, index: int) -> DeviceAccess:
        # Cannot verify SPECTRUM in disconnected mode; store FMT_UNKNOWN.
        key = f"{attr_path}@{index}"
        self._data_formats[key] = tango.AttrDataFormat.FMT_UNKNOWN
        return AttributeIndexed(IndexedConfigModel(attribute=attr_path, index=index, range=(None, None)))

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

    def _build_connected_indexed(self, attr_path: str, index: int) -> DeviceAccess:
        """
        Build an indexed device access after verifying the attribute is a SPECTRUM.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango call fails or the attribute is not a SPECTRUM.
        """
        key = f"{attr_path}@{index}"
        try:
            attr_config = tango.AttributeProxy(attr_path).get_config()
        except tango.DevFailed as df:
            pyaml_exception = tango_to_PyAMLException(df)
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot resolve '{key}': {pyaml_exception}"
            ) from df

        data_format = getattr(attr_config, "data_format", tango.AttrDataFormat.FMT_UNKNOWN)
        if data_format != tango.AttrDataFormat.SPECTRUM:
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot use '{key}' as an indexed "
                "key: the Tango attribute is not a SPECTRUM."
            )

        unit = getattr(attr_config, "unit", "") or ""
        self._data_formats[key] = tango.AttrDataFormat.SPECTRUM
        attr_range = (
            to_float_or_none(getattr(attr_config, "min_value", None)),
            to_float_or_none(getattr(attr_config, "max_value", None)),
        )
        cfg = IndexedConfigModel(attribute=attr_path, index=index, unit=unit, range=attr_range)

        if getattr(attr_config, "writable", tango.AttrWriteType.WT_UNKNOWN) in self._WRITABLE_TYPES:
            return AttributeIndexed(cfg)
        return AttributeIndexedReadOnly(cfg)
