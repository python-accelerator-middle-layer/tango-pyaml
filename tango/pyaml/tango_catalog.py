import tango
import pyaml

from typing import TYPE_CHECKING
from pydantic import ConfigDict
from pyaml.configuration.catalog import Catalog, CatalogConfigModel, CatalogResolver
from pyaml.control.deviceaccess import DeviceAccess

from .attribute import Attribute, ConfigModel as AttributeConfigModel
from .attribute_read_only import AttributeReadOnly
from .tango_pyaml_utils import tango_to_PyAMLException, to_float_or_none

PYAMLCLASS = "TangoCatalog"

if TYPE_CHECKING:
    from .controlsystem import TangoControlSystem


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
            f"Tango catalog '{self.get_name()}' must be attached to a TangoControlSystem before resolving key '{key}'"
        )

    def is_disconnected(self) -> bool:
        return self._cfg.disconnected

    def attach_control_system(self, control_system: object) -> "TangoCatalogResolver":
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

    def __init__(self, catalog: TangoCatalog, control_system: "TangoControlSystem"):
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
                if self._catalog.is_disconnected():
                    self._refs[key] = self._build_disconnected_indexed(attr_path, index)
                else:
                    self._refs[key] = self._build_connected_indexed(attr_path, index)
            else:
                if self._catalog.is_disconnected():
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
                f"Tango catalog '{self._catalog.get_name()}' expects string keys, got {type(key).__name__}"
            )

        if "@" in key:
            attr_path, idx_str = key.rsplit("@", 1)
            try:
                index = int(idx_str)
            except ValueError as exc:
                raise pyaml.PyAMLException(
                    f"Tango catalog '{self._catalog.get_name()}' invalid index '{idx_str}' in key '{key}'."
                ) from exc
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
        return Attribute(
            AttributeConfigModel(attribute=attr_path, index=index, range=(None, None))
        )

    def _build_connected_attribute(self, key: str) -> DeviceAccess:
        tango_attr_name = self._tango_attribute_name(key)
        try:
            # AttributeProxy.get_config() is the most direct way to retrieve
            # writability, unit, range and data format from Tango.
            attr_config = tango.AttributeProxy(tango_attr_name).get_config()
        except tango.DevFailed as df:
            pyaml_exception = tango_to_PyAMLException(df)
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot resolve '{key}': {pyaml_exception}"
            ) from df

        unit, attr_range, data_format, writable = self._read_config_metadata(
            attr_config, key
        )
        self._data_formats[key] = data_format
        cfg = AttributeConfigModel(attribute=key, unit=unit, range=attr_range)

        if writable in self._WRITABLE_TYPES:
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
        tango_attr_name = self._tango_attribute_name(attr_path)
        try:
            attr_config = tango.AttributeProxy(tango_attr_name).get_config()
        except tango.DevFailed as df:
            pyaml_exception = tango_to_PyAMLException(df)
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot resolve '{key}': {pyaml_exception}"
            ) from df

        unit, attr_range, data_format, writable = self._read_config_metadata(
            attr_config, key
        )
        if data_format != tango.AttrDataFormat.SPECTRUM:
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot use '{key}' as an indexed "
                "key: the Tango attribute is not a SPECTRUM."
            )

        self._data_formats[key] = tango.AttrDataFormat.SPECTRUM
        cfg = AttributeConfigModel(
            attribute=attr_path, index=index, unit=unit, range=attr_range
        )

        if writable in self._WRITABLE_TYPES:
            return Attribute(cfg)
        return AttributeReadOnly(cfg)

    def _read_config_metadata(
        self, attr_config, key: str
    ) -> tuple[
        str,
        tuple[float | None, float | None],
        tango.AttrDataFormat,
        tango.AttrWriteType,
    ]:
        try:
            unit = attr_config.unit or ""
            attr_range = (
                to_float_or_none(attr_config.min_value),
                to_float_or_none(attr_config.max_value),
            )
            data_format = attr_config.data_format
            writable = attr_config.writable
        except AttributeError as exc:
            raise pyaml.PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot resolve '{key}': "
                f"incomplete Tango attribute config, missing '{exc.name}'."
            ) from exc

        return unit, attr_range, data_format, writable

    def _tango_attribute_name(self, attr_path: str) -> str:
        tango_host = self._control_system.get_tango_host()
        if tango_host:
            return f"//{tango_host}/{attr_path}"
        return attr_path
