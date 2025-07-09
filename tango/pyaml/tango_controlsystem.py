from pydantic import BaseModel
from pyaml.control.controlsystem import ControlSystem

class ConfigModel(BaseModel):
    name: str
    tango_host: str
    debug_level: int


class TangoControlSystem(ControlSystem):
    """
    Class that implements global parameters for a CS
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg

    def name(self) -> str:
        return self._cfg.name

    def init_cs(self):
        """Initialize control system"""
        pass
