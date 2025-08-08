from abc import ABCMeta, abstractmethod


class InitializableElement(metaclass=ABCMeta):

    def __init__(self):
        self._initialized = False

    @abstractmethod
    def initialize(self):
        self._initialized = True


    def is_initialized(self) -> bool:
        return self._initialized