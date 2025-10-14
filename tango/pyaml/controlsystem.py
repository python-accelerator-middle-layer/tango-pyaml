import os
import logging
from threading import Lock

from pydantic import BaseModel, field_validator
from pyaml.control.controlsystem import ControlSystem

PYAMLCLASS : str = "TangoControlSystem"

logger = logging.getLogger(__name__)



class ConfigModel(BaseModel):
    """
    Configuration model for a Tango Control System.

    Attributes
    ----------
    name : str
        Name of the control system.
    tango_host : str
        Tango host URL.
    debug_level : int
        Debug verbosity level.
    """
    name: str
    tango_host: str
    debug_level: str=None
    lazy_devices: bool = True


class TangoControlSystem(ControlSystem):
    """
    Tango-specific implementation of a Control System.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration parameters including name, host and debug level.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls, cfg: ConfigModel):
        """
        No matter how many times you call PyAMLFactory(), it will be created only once.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._cfg = cfg
                cls._instance._initializable_elements = []
                cls._instance._initialized = False
                cls._instance._lazy_devices = cfg.lazy_devices
            return cls._instance

    @classmethod
    def is_initialized(cls):
        return cls._instance is not None and cls._instance.is_instance_initialized()


    @classmethod
    def get_instance(cls) -> "TangoControlSystem":
        return cls._instance

    def __init__(self, cfg: ConfigModel):
        super().__init__()


    def is_instance_initialized(self) -> bool:
        return self._initialized


    def name(self) -> str:
        """
        Return the name of the control system.

        Returns
        -------
        str
            Name of the control system.
        """
        return self._cfg.name


    def init_cs(self):
        """
        Initialize the control system.

        This method is a placeholder and should be implemented as needed.
        """
        if self._initialized:
            logger.log(logging.WARNING, f"Tango control system binding for PyAML was already initialized"
                                        f" with name '{self._cfg.name}' and TANGO_HOST={os.environ['TANGO_HOST']}")
            return

        if self._cfg.tango_host:
            os.environ["TANGO_HOST"] = self._cfg.tango_host
        if self._cfg.debug_level:
            log_level = getattr(logging, self._cfg.debug_level, logging.WARNING)
            logger.parent.setLevel(log_level)
            logger.setLevel(log_level)

        """
        Eagerly initializes registered elements only if *lazy_devices* is False.
        When *lazy_devices* is True (default), initialization is deferred until
        `warmup()` or first-use via `ensure_initialized()`.
        """
        if not self._cfg.lazy_devices:
            self._do_initialize_all()
        else:
            logger.debug("init_cs(): lazy mode enabled; deferring initialization")

        self._initialized = True

        logger.log(logging.INFO, f"Tango control system binding for PyAML initialized with name '{self._cfg.name}'"
                                 f" and TANGO_HOST={os.environ['TANGO_HOST']}")


    def _do_initialize_all(self) -> None:
        # Initialize all registered elements exactly once
        for elem in self._initializable_elements:
            try:
                elem.initialize()
            except Exception as exc:  # pragma: no cover
                logger.exception("Failed to initialize %r: %s", elem, exc)
                raise
        self._initializable_elements.clear()


    def add_initializable(self, initializable):
        self._initializable_elements.append(initializable)


    def warmup(self) -> None:
        """Explicitly switch to eager behavior and initialize now."""
        with self._lock:
            self._lazy_devices = False
            self._do_initialize_all()

    @property
    def lazy_devices(self) -> bool:
        return self._lazy_devices
