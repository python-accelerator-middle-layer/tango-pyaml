import logging

import pyaml
from pyaml.validation import DynamicValidation, register_schema

from .attribute_list import AttributeList, AttributeListConfig

PYAMLCLASS: str = "AttributeListReadOnly"

logger = logging.getLogger(__name__)


class AttributeListReadOnlyConfig(AttributeListConfig): ...


@register_schema
class AttributeListReadOnly(AttributeList, DynamicValidation):
    """
    Handle a list of Tango attributes using Tango Groups.

    Parameters
    ----------
    attributes : list of str
        List of Tango attribute paths.
    name : str, optional
        Group name.
    unit : str, optional
        Unit of the attributes.
    """

    def __init__(self, attributes: list[str], name: str = "", unit: str = ""):
        super().__init__(attributes, name, unit)

        self._attributes = attributes
        self._name = name
        self._unit = unit

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
