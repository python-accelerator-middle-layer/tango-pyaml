"""
Tango implementation of the pyAML control system.

:class:`TangoControlSystem` resolves pyAML device references through a
:class:`~tango.pyaml.catalog.Catalog`, prefixes Tango attribute paths with the
configured Tango host and caches the resulting device access objects.
"""

import logging

from pydantic import BaseModel

from pyaml import PyAMLException
from pyaml.common.element import __pyaml_repr__
from pyaml.control.controlsystem import ControlSystem
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.validation import DynamicValidation, register_schema

from . import __version__
from .attribute import Attribute, AttributeConfig
from .attribute_list import AttributeList, AttributeListConfig
from .attribute_list_read_only import AttributeListReadOnly, AttributeListReadOnlyConfig
from .attribute_read_only import AttributeReadOnly, AttributeReadOnlyConfig
from .catalog import Catalog
from .multi_attribute import MultiAttribute

PYAMLCLASS: str = "TangoControlSystem"

logger = logging.getLogger(__name__)


@register_schema
class TangoControlSystem(ControlSystem, DynamicValidation):
    """
    Tango-specific implementation of a Control System.

    Parameters
    ----------
    name : str
        Name of the control system.
    tango_host : str, optional
        Tango host URL (``host:port``). Default is ``None``, meaning the
        ``TANGO_HOST`` environment variable is used by PyTango.
    catalog : Catalog, optional
        Catalog instance used to resolve PyAML device keys.
    debug_level : str or int, optional
        Debug verbosity level. Such as INFO, DEBUG, WARNING, ERROR, CRITICAL.
        Or 10, 20, 30, 40, 50.
    lazy_devices : bool, optional
        Reserved for lazy device creation. Default is True.
    timeout_ms : int, optional
        Device timeout in milliseconds. Default is 3000.

    Attributes
    ----------
    _name : str
        Name of the control system.
    _tango_host : str or None
        Configured Tango host.
    _catalog : Catalog or None
        Catalog used to resolve device keys.
    _debug_level : str or int or None
        Requested log level.
    _lazy_devices : bool
        Lazy device creation flag.
    _timeout_ms : int
        Device timeout in milliseconds.

    Methods
    -------
    attach(devs)
        Attach a list of device accesses to this control system.
    attach_array(devs)
        Attach a list of device accesses to this control system.
    get_device_access(ref)
        Resolve a public device reference for this Tango control system.
    name()
        Return the name of the control system.
    get_tango_host()
        Return the Tango host configured for this control system.
    get_aggregator()
        Return a new empty aggregator of device accesses.
    scalar_aggregator()
        Return the module name used for handling aggregator of DeviceAccess.
    vector_aggregator()
        Return the module name used for handling aggregator of
        DeviceVectorAccess.
    get_catalog()
        Return the catalog that references all control system devices.
    """

    def __init__(
        self,
        name: str,
        tango_host: str | None = None,
        catalog: Catalog | None = None,
        debug_level: str | int | None = None,
        lazy_devices: bool = True,
        timeout_ms: int = 3000,
    ):
        super().__init__()
        self._name = name
        self._tango_host = tango_host
        self._catalog = catalog
        self._debug_level = debug_level
        self._lazy_devices = lazy_devices
        self._timeout_ms = timeout_ms
        self.__devices = {}  # Dict containing all attached DeviceAccess

        if self._debug_level:
            if isinstance(self._debug_level, int):
                log_level = self._debug_level
            else:
                log_level = getattr(logging, self._debug_level, logging.WARNING)
            logger.parent.setLevel(log_level)
            logger.setLevel(log_level)

        logger.log(
            logging.WARNING,
            f"PyAML Tango control system binding ({__version__}) initialized with name '{self._name}'"
            f" and TANGO_HOST={self._tango_host}",
        )

    def attach_array(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        """
        Attach a list of device accesses to this control system.

        Parameters
        ----------
        devs : list of DeviceAccess
            Tango attributes to attach. ``None`` entries are preserved.

        Returns
        -------
        list of DeviceAccess
            Attached device accesses, in the same order as ``devs``.
        """
        return self._attach(devs)

    def attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        """
        Attach a list of device accesses to this control system.

        Parameters
        ----------
        devs : list of DeviceAccess
            Tango attributes to attach. ``None`` entries are preserved.

        Returns
        -------
        list of DeviceAccess
            Attached device accesses, in the same order as ``devs``.
        """
        return self._attach(devs)

    def _attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        """
        Prefix attribute paths with the Tango host and cache the results.

        Each device is cloned with its full attribute name
        (``//tango_host/attribute``) the first time it is seen; subsequent
        calls return the cached clone.

        Parameters
        ----------
        devs : list of DeviceAccess
            Tango attributes to attach. ``None`` entries are preserved.

        Returns
        -------
        list of DeviceAccess
            Attached device accesses, in the same order as ``devs``.

        Raises
        ------
        pyaml.PyAMLException
            If a device does not expose ``get_tango_attribute()``.
        """
        # Concatenate the tango_host prefix
        newDevs = []
        for d in devs:
            if d is not None:
                try:
                    attribute = d.get_tango_attribute()
                except AttributeError as exc:
                    raise PyAMLException(
                        f"Cannot attach device {d!r}: expected a Tango attribute with get_tango_attribute()."
                    ) from exc

                tango_host = self.get_tango_host()
                if tango_host:
                    full_name = "//" + tango_host + "/" + attribute
                else:
                    full_name = attribute
                if full_name not in self.__devices:
                    self.__devices[full_name] = d.clone_with_tango_attribute(full_name)
                newDevs.append(self.__devices[full_name])
            else:
                newDevs.append(None)
        return newDevs

    def get_device_access(self, ref: str | BaseModel | None) -> DeviceAccess | None:
        """
        Resolve a public device reference for this Tango control system.

        YAML references are opaque strings resolved by the configured backend
        catalog. Public Python APIs may pass Tango backend configuration models.
        Already constructed DeviceAccess instances are intentionally rejected:
        attach() remains the internal compatibility API for those.

        Parameters
        ----------
        ref : str or pydantic.BaseModel or None
            Catalog key, Tango configuration model
            (:class:`~tango.pyaml.attribute.AttributeConfig`,
            :class:`~tango.pyaml.attribute_read_only.AttributeReadOnlyConfig`,
            :class:`~tango.pyaml.attribute_list.AttributeListConfig` or
            :class:`~tango.pyaml.attribute_list_read_only.AttributeListReadOnlyConfig`),
            or ``None``.

        Returns
        -------
        DeviceAccess or None
            Attached device access, or ``None`` if ``ref`` is ``None``.

        Raises
        ------
        pyaml.PyAMLException
            If ``ref`` is an already constructed DeviceAccess, if no usable
            catalog is configured for a string key, or if ``ref`` has an
            unsupported type.
        """
        if ref is None:
            return None

        if isinstance(ref, DeviceAccess):
            raise PyAMLException(
                "TangoControlSystem.get_device_access() expects a catalog key "
                "or None. Use attach() for already constructed "
                "DeviceAccess objects."
            )

        if isinstance(ref, str):
            catalog = self.get_catalog()
            if catalog is None:
                raise PyAMLException(
                    f"TangoControlSystem '{self.name()}' has no catalog configured."
                )
            if not isinstance(catalog, Catalog):
                raise PyAMLException(
                    f"TangoControlSystem '{self.name()}' has unsupported catalog type "
                    f"{type(catalog).__name__}."
                )
            try:
                resolve = catalog.resolve
            except AttributeError as exc:
                raise PyAMLException(
                    f"Catalog '{catalog.get_name()}' cannot resolve key '{ref}': "
                    "missing backend resolve() method."
                ) from exc
            device = resolve(ref, self)
            return self._attach([device])[0]

        if isinstance(ref, AttributeReadOnlyConfig):
            return self._attach([AttributeReadOnly(**ref.model_dump())])[0]

        if isinstance(ref, AttributeConfig):
            return self._attach([Attribute(**ref.model_dump())])[0]

        if isinstance(ref, AttributeListReadOnlyConfig):
            cfg = self._attach_attribute_list_config(ref)
            return AttributeListReadOnly(**cfg.model_dump())

        if isinstance(ref, AttributeListConfig):
            cfg = self._attach_attribute_list_config(ref)
            return AttributeList(**cfg.model_dump())

        if isinstance(ref, BaseModel):
            raise PyAMLException(
                f"TangoControlSystem cannot construct a device from config model "
                f"{type(ref).__name__}."
            )

        raise PyAMLException(
            f"TangoControlSystem.get_device_access() cannot resolve references of type "
            f"{type(ref).__name__}; expected str or None."
        )

    def _attach_attribute_list_config(
        self, cfg: AttributeListConfig
    ) -> AttributeListConfig:
        """
        Return a copy of ``cfg`` with attribute paths prefixed by the Tango host.

        Parameters
        ----------
        cfg : AttributeListConfig
            Configuration to adapt.

        Returns
        -------
        AttributeListConfig
            ``cfg`` itself when no Tango host is configured, otherwise a copy
            whose ``attributes`` are ``//tango_host/attribute`` paths.
        """
        tango_host = self.get_tango_host()
        if not tango_host:
            return cfg

        return cfg.model_copy(
            update={
                "attributes": [
                    f"//{tango_host}/{attribute}" for attribute in cfg.attributes
                ]
            }
        )

    def name(self) -> str:
        """
        Return the name of the control system.

        Returns
        -------
        str
            Name of the control system.
        """
        return self._name

    def get_tango_host(self) -> str | None:
        """
        Return the Tango host configured for this control system.

        Returns
        -------
        str or None
            Tango host URL, or ``None`` when unconfigured.
        """
        return self._tango_host

    def get_aggregator(self) -> MultiAttribute | None:
        """
        Return a new empty aggregator of device accesses.

        If ``None`` were returned, serialized readings/writings would be
        performed by the pyAML core instead.

        Returns
        -------
        MultiAttribute
            New empty :class:`~tango.pyaml.multi_attribute.MultiAttribute`.
        """
        return MultiAttribute()

    def scalar_aggregator(self) -> str | None:
        """
        Return the module name used for handling aggregator of DeviceAccess.

        Returns
        -------
        str or None
            Aggregator module name. Always ``None`` for Tango.
        """
        return None

    def vector_aggregator(self) -> str | None:
        """
        Return the module name used for handling aggregator of DeviceVectorAccess.

        Returns
        -------
        str or None
            Aggregator module name. Always ``None`` for Tango.
        """
        return None

    def get_catalog(self) -> Catalog | None:
        """
        Return the catalog that references all control system devices.

        Returns
        -------
        Catalog or None
            The catalog, or ``None`` if none was configured.
        """
        return self._catalog

    def __repr__(self):
        return __pyaml_repr__(self)
