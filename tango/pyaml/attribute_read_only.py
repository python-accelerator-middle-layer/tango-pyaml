from .tango_attribute import TangoAttribute, ConfigModel
from .tango_pyaml_utils import *

PYAMLCLASS : str = "AttributeReadOnly"

class AttributeReadOnly(TangoAttribute):
    """
    Read-only Tango attribute.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration model containing attribute path and unit.
    """
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

    def set(self, value: float):
        """
        Disallowed write operation.

        Raises
        ------
        pyaml.PyAMLException
            Always raised because the attribute is read-only.
        """
        raise pyaml.PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")

    def set_and_wait(self, value: float):
        """
        Disallowed synchronous write operation.

        Raises
        ------
        pyaml.PyAMLException
            Always raised because the attribute is read-only.
        """
        raise pyaml.PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")

    def get(self) -> float:
        """
        Disallowed get operation.

        Raises
        ------
        pyaml.PyAMLException
            Always raised because the attribute is read-only.
        """
        raise pyaml.PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")
