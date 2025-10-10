from abc import ABCMeta, abstractmethod

import pyaml

from .controlsystem import TangoControlSystem


class InitializableElement(metaclass=ABCMeta):

    def __init__(self):
        self._initialized = False

    @abstractmethod
    def initialize(self):
        self._initialized = True

    @abstractmethod
    def name(self) -> str:
        return ""

    def is_initialized(self) -> bool:
        return self._initialized

    def _ensure_initialized(self):
        if not self.is_initialized():
            if not TangoControlSystem.get_instance().lazy_devices:
                raise pyaml.PyAMLException(f"The attribute {self.name()} is not initialized.")
            self.initialize()
        pass
