import tango
import pyaml

from pyaml.control.deviceaccess import DeviceAccess
from pyaml.validation import register_schema, DynamicValidation

from .attribute import Attribute, AttributeConfig
from .attribute_read_only import AttributeReadOnly
from .catalog import Catalog
from .tango_pyaml_utils import tango_to_PyAMLException, to_float_or_none

PYAMLCLASS = "TangoCatalog"


@register_schema
class TangoCatalog(Catalog, DynamicValidation):
    """
    Catalog resolving keys that are direct Tango attribute references.

    Keys can be plain Tango attribute paths (``domain/family/member/attribute``)
    or indexed references into a SPECTRUM attribute
    (``domain/family/member/attribute@index``).

    disconnected : bool
        If true, resolve Tango attribute names without querying Tango.
    """

    _WRITABLE_TYPES = {
        tango.AttrWriteType.READ_WRITE,
        tango.AttrWriteType.WRITE,
        tango.AttrWriteType.READ_WITH_WRITE,
    }

    def __init__(self, disconnected: bool = False):
        super().__init__()

        self._disconnected = disconnected
        # Resolved DeviceAccess objects are bound to one control-system context
        # because metadata lookup depends on that control system's Tango host.
        self._refs: dict[tuple[int, str], DeviceAccess] = {}
        self._data_formats: dict[tuple[int, str], tango.AttrDataFormat] = {}

    def resolve(self, key: str, control_system: object | None = None) -> DeviceAccess:
        """
        Resolve a Tango attribute reference into a DeviceAccess.

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

        Parameters
        ----------
        key : str
            Plain attribute path or indexed path (``attribute@index``).
        control_system : object
            Tango control-system context used for Tango host handling.

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
        self._validate_control_system(control_system, key)
        attr_path, index = self._parse_key(key)
        cache_key = (id(control_system), key)

        if cache_key not in self._refs:
            if index is not None:
                if self.is_disconnected():
                    self._refs[cache_key] = self._build_disconnected_indexed(
                        cache_key, attr_path, index
                    )
                else:
                    self._refs[cache_key] = self._build_connected_indexed(
                        cache_key, control_system, attr_path, index
                    )
            else:
                if self.is_disconnected():
                    self._refs[cache_key] = self._build_disconnected_attribute(
                        cache_key, key
                    )
                else:
                    self._refs[cache_key] = self._build_connected_attribute(
                        cache_key, control_system, key
                    )

        return self._refs[cache_key]

    def is_disconnected(self) -> bool:
        return self._disconnected

    def get_data_format(
        self, key: str, control_system: object | None = None
    ) -> tango.AttrDataFormat:
        """
        Return the Tango data format for a resolved attribute.

        Parameters
        ----------
        key : str
            Catalog key (must have been resolved at least once, or will be
            resolved now).
        control_system : object
            Tango control-system context used for Tango host handling.

        Returns
        -------
        tango.AttrDataFormat
            Data format reported by Tango, or ``FMT_UNKNOWN`` in disconnected
            mode.
        """
        self.resolve(key, control_system)
        return self._data_formats[(id(control_system), key)]

    def _validate_control_system(self, control_system: object | None, key: str) -> None:
        from .controlsystem import TangoControlSystem

        if control_system is None:
            raise pyaml.PyAMLException(
                f"Tango catalog needs a TangoControlSystem context "
                f"before resolving key '{key}'"
            )

        if not isinstance(control_system, TangoControlSystem):
            raise pyaml.PyAMLException(
                "Tango catalog can only resolve through TangoControlSystem"
            )

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
                f"Tango catalog expects string keys, got {type(key).__name__}"
            )

        if "@" in key:
            attr_path, idx_str = key.rsplit("@", 1)
            try:
                index = int(idx_str)
            except ValueError as exc:
                raise pyaml.PyAMLException(
                    f"Tango catalog invalid index '{idx_str}' in key '{key}'."
                ) from exc
        else:
            attr_path = key
            index = None

        parts = attr_path.split("/")
        if len(parts) != 4 or any(part == "" for part in parts):
            raise pyaml.PyAMLException(
                f"Tango catalog cannot resolve invalid Tango attribute "
                f"reference '{key}'. Expected 'domain/family/member/attribute' or "
                f"'domain/family/member/attribute@index'."
            )

        return attr_path, index

    def _build_disconnected_attribute(
        self, cache_key: tuple[int, str], key: str
    ) -> DeviceAccess:
        # In disconnected mode, keep all metadata local. In particular, setting
        # range avoids Attribute.get_range() from lazily querying Tango later.
        self._data_formats[cache_key] = tango.AttrDataFormat.FMT_UNKNOWN
        return Attribute(attribute=key, range=(None, None))

    def _build_disconnected_indexed(
        self, cache_key: tuple[int, str], attr_path: str, index: int
    ) -> DeviceAccess:
        # Cannot verify SPECTRUM in disconnected mode; store FMT_UNKNOWN.
        self._data_formats[cache_key] = tango.AttrDataFormat.FMT_UNKNOWN
        return Attribute(attribute=attr_path, index=index, range=(None, None))

    def _build_connected_attribute(
        self, cache_key: tuple[int, str], control_system: object, key: str
    ) -> DeviceAccess:
        tango_attr_name = self._tango_attribute_name(control_system, key)
        try:
            # AttributeProxy.get_config() is the most direct way to retrieve
            # writability, unit, range and data format from Tango.
            attr_config = tango.AttributeProxy(tango_attr_name).get_config()
        except tango.DevFailed as df:
            pyaml_exception = tango_to_PyAMLException(df)
            raise pyaml.PyAMLException(
                f"Tango catalog cannot resolve '{key}': {pyaml_exception}"
            ) from df

        unit, attr_range, data_format, writable = self._read_config_metadata(
            attr_config, key
        )
        self._data_formats[cache_key] = data_format
        cfg = AttributeConfig(attribute=key, unit=unit, range=attr_range)

        if writable in self._WRITABLE_TYPES:
            return Attribute(**cfg.model_dump())
        return AttributeReadOnly(**cfg.model_dump())

    def _build_connected_indexed(
        self,
        cache_key: tuple[int, str],
        control_system: object,
        attr_path: str,
        index: int,
    ) -> DeviceAccess:
        """
        Build an indexed device access after verifying the attribute is a SPECTRUM.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango call fails or the attribute is not a SPECTRUM.
        """
        key = f"{attr_path}@{index}"
        tango_attr_name = self._tango_attribute_name(control_system, attr_path)
        try:
            attr_config = tango.AttributeProxy(tango_attr_name).get_config()
        except tango.DevFailed as df:
            pyaml_exception = tango_to_PyAMLException(df)
            raise pyaml.PyAMLException(
                f"Tango catalog cannot resolve '{key}': {pyaml_exception}"
            ) from df

        unit, attr_range, data_format, writable = self._read_config_metadata(
            attr_config, key
        )
        if data_format != tango.AttrDataFormat.SPECTRUM:
            raise pyaml.PyAMLException(
                f"Tango catalog cannot use '{key}' as an indexed "
                "key: the Tango attribute is not a SPECTRUM."
            )

        self._data_formats[cache_key] = tango.AttrDataFormat.SPECTRUM
        cfg = AttributeConfig(
            attribute=attr_path, index=index, unit=unit, range=attr_range
        )

        if writable in self._WRITABLE_TYPES:
            return Attribute(**cfg.model_dump())
        return AttributeReadOnly(**cfg.model_dump())

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
                f"Tango catalog cannot resolve '{key}': "
                f"incomplete Tango attribute config, missing '{exc.name}'."
            ) from exc

        return unit, attr_range, data_format, writable

    def _tango_attribute_name(self, control_system: object, attr_path: str) -> str:
        tango_host = control_system.get_tango_host()
        if tango_host:
            return f"//{tango_host}/{attr_path}"
        return attr_path
