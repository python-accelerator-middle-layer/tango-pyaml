import os
import logging

from pydantic import BaseModel
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
        if self._cfg.tango_host:
            os.environ["TANGO_HOST"] = self._cfg.tango_host
        if self._cfg.debug_level:
            log_level = getattr(logging, self._cfg.debug_level, logging.WARNING)
            logger.parent.setLevel(log_level)
            logger.setLevel(log_level)

        logger.log(logging.INFO, f"Tango control system binding for PyAML initialized with name '{self._cfg.name}'"
                                 f" and TANGO_HOST={os.environ["TANGO_HOST"]}")
