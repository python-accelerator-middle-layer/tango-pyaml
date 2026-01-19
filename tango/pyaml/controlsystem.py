import logging
import copy

from pydantic import BaseModel
from pyaml.control.controlsystem import ControlSystem
from pyaml.control.deviceaccess import DeviceAccess

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
    debug_level : int
        Debug verbosity level.
    scalar_aggregator : str
        Aggregator module for scalar values. If none specified, writings and readings of sclar value are serialized.
    vector_aggregator : str
        Aggregator module for vecrors. If none specified, writings and readings of vector are serialized.
    timeout_ms : int
        Device timeout in milli seconds.
    """

    name: str
    tango_host: str | None = None
    debug_level: str = None
    lazy_devices: bool = True
    scalar_aggregator: str | None = "tango.pyaml.multi_attribute"
    vector_aggregator: str | None = None
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
            f"Tango control system binding for PyAML initialized with name '{self._cfg.name}'"
            f" and TANGO_HOST={self._cfg.tango_host}",
        )

    def __newref(self, obj, new_name: str):
        # Shallow copy the object
        newObj = copy.copy(obj)
        # Shallow copy the config object
        # to allow a new attribute name
        newObj._cfg = copy.copy(obj._cfg)
        newObj._cfg.attribute = new_name
        return newObj

    def attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        # Concatenate the tango_host prefix
        newDevs = []
        for d in devs:
            if d is not None:
                if self._cfg.tango_host:
                    full_name = "//" + self._cfg.tango_host + "/" + d._cfg.attribute
                else:
                    full_name = d._cfg.attribute
                if full_name not in self.__devices:
                    self.__devices[full_name] = self.__newref(d, full_name)
                newDevs.append(self.__devices[full_name])
            else:
                newDevs.append(None)
        return newDevs

    def attach_array(self, dev: list[DeviceAccess]) -> list[DeviceAccess]:
        pass

    def name(self) -> str:
        """
        Return the name of the control system.

        Returns
        -------
        str
            Name of the control system.
        """
        return self._cfg.name

    def scalar_aggregator(self) -> str | None:
        """
        Returns the module name used for handling aggregator of DeviceAccess

        Returns
        -------
        str
            Aggregator module name
        """
        return self._cfg.scalar_aggregator

    def vector_aggregator(self) -> str | None:
        """
        Returns the module name used for handling aggregator of DeviceVectorAccess

        Returns
        -------
        str
            Aggregator module name
        """
        return self._cfg.vector_aggregator

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
