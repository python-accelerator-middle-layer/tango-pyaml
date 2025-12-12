from abc import ABCMeta, abstractmethod

import pyaml

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
            self.initialize()
        pass
