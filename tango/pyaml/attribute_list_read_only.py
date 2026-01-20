import logging

import pyaml
from .attribute_list import AttributeList, ConfigModel

PYAMLCLASS: str = "AttributeListReadOnly"

logger = logging.getLogger(__name__)


class AttributeListReadOnly(AttributeList):
    """
    Handle a list of Tango attributes using Tango Groups.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration object with attribute list, name and unit.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

    def set(self, value: float):
        """
        Write a value asynchronously to all Tango attributes.

        Parameters
        ----------
        value : float
            Value to write.
        """
        raise pyaml.PyAMLException(
            f"Tango attribute list {self.name()} is not writable."
        )

    def set_and_wait(self, value: float):
        """
        Write a value synchronously to all Tango attributes.

        Parameters
        ----------
        value : float
            Value to write.
        """
        [
            group.write_attribute(attr_name, value)
            for attr_name, group in self._tango_groups.items()
        ]
