import logging

from pydantic import BaseModel, ConfigDict

from pyaml import PyAMLException
from pyaml.control.controlsystem import ControlSystem
from pyaml.control.deviceaccess import DeviceAccess
from . import __version__
from .attribute import Attribute, ConfigModel as AttributeConfigModel
from .attribute_list import AttributeList, ConfigModel as AttributeListConfigModel
from .attribute_list_read_only import (
    AttributeListReadOnly,
    ConfigModel as AttributeListReadOnlyConfigModel,
)
from .attribute_read_only import (
    AttributeReadOnly,
    ConfigModel as AttributeReadOnlyConfigModel,
)
from .catalog import Catalog
from .multi_attribute import MultiAttribute

PYAMLCLASS: str = "TangoControlSystem"

logger = logging.getLogger(__name__)


class ConfigModel(BaseModel):
    """
    Configuration model for a Tango Control System.

    Attributes
    ----------
    name : str
        Name of the control system.
    tango_host : str
        Tango host URL. Default is the TANGO_HOST variable.
    catalog : Catalog | None
        Catalog instance used to resolve PyAML device keys.
    debug_level : int
        Debug verbosity level.
    scalar_aggregator : str
        Aggregator module for scalar values. If none specified, writings and readings of sclar value are serialized.
    vector_aggregator : str
        Aggregator module for vecrors. If none specified, writings and readings of vector are serialized.
    timeout_ms : int
        Device timeout in milli seconds.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    tango_host: str | None = None
    catalog: Catalog | None = None
    debug_level: str | None = None
    lazy_devices: bool = True
    timeout_ms: int = 3000


class TangoControlSystem(ControlSystem):
    """
    Tango-specific implementation of a Control System.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration parameters including name, host and debug level.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        self.__devices = {}  # Dict containing all attached DeviceAccess

        if self._cfg.debug_level:
            log_level = getattr(logging, self._cfg.debug_level, logging.WARNING)
            logger.parent.setLevel(log_level)
            logger.setLevel(log_level)

        logger.log(
            logging.WARNING,
            f"PyAML Tango control system binding ({__version__}) initialized with name '{self._cfg.name}'"
            f" and TANGO_HOST={self._cfg.tango_host}",
        )

    def attach_array(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        return self._attach(devs)

    def attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        return self._attach(devs)

    def _attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
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

    def get_device(self, ref: str | BaseModel | None) -> DeviceAccess | None:
        """
        Resolve a public device reference for this Tango control system.

        YAML references are opaque strings resolved by the configured backend
        catalog. Public Python APIs may pass Tango backend configuration models.
        Already constructed DeviceAccess instances are intentionally rejected:
        attach() remains the internal compatibility API for those.
        """
        if ref is None:
            return None

        if isinstance(ref, DeviceAccess):
            raise PyAMLException(
                "TangoControlSystem.get_device() expects a catalog key, Tango "
                "ConfigModel, or None. Use attach() for already constructed "
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

        if isinstance(ref, AttributeReadOnlyConfigModel):
            return self._attach([AttributeReadOnly(ref)])[0]

        if isinstance(ref, AttributeConfigModel):
            return self._attach([Attribute(ref)])[0]

        if isinstance(ref, AttributeListReadOnlyConfigModel):
            return AttributeListReadOnly(self._attach_attribute_list_config(ref))

        if isinstance(ref, AttributeListConfigModel):
            return AttributeList(self._attach_attribute_list_config(ref))

        if isinstance(ref, BaseModel):
            raise PyAMLException(
                f"TangoControlSystem cannot construct a device from config model "
                f"{type(ref).__name__}."
            )

        raise PyAMLException(
            f"TangoControlSystem.get_device() cannot resolve references of type "
            f"{type(ref).__name__}; expected str, Tango ConfigModel, or None."
        )

    def _attach_attribute_list_config(
        self, cfg: AttributeListConfigModel
    ) -> AttributeListConfigModel:
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
        return self._cfg.name

    def get_tango_host(self) -> str | None:
        """
        Return the Tango host configured for this control system.

        Returns
        -------
        str | None
            Tango host URL, or ``None`` when unconfigured.
        """
        return self._cfg.tango_host

    def get_aggregator(self) -> MultiAttribute | None:
        """Returns a new empty DeviceAccessList. If None is returned serialized readings/writtings are performed"""
        return MultiAttribute()

    def get_catalog(self) -> Catalog | None:
        """
        Returns the catalog that references all control systems devices.

        Returns
        -------
        Catalog
            The catalog
        """
        return self._cfg.catalog

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
