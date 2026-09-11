"""Read-only scalar Tango attribute."""

import logging

import pyaml
from pyaml.validation import DynamicValidation, register_schema

from .attribute import Attribute, AttributeConfig

PYAMLCLASS: str = "AttributeReadOnly"

logger = logging.getLogger(__name__)


class AttributeReadOnlyConfig(AttributeConfig):
    """Configuration model for a read-only Tango attribute."""


@register_schema
class AttributeReadOnly(Attribute, DynamicValidation):
    """
    Read-only Tango attribute.

    Behaves like :class:`~tango.pyaml.attribute.Attribute` but rejects every
    write and never checks the Tango attribute writability on
    initialization. :meth:`get` returns the readback value instead of the
    last written value.

    Parameters
    ----------
    attribute : str
        Full path of the Tango attribute (e.g., 'my/ps/device/current').
    unit : str, optional
        The unit of the attribute.
    range : tuple(min, max), optional
        Range of valid values. Use null for -∞ or +∞.
    index : int, optional
        Zero-based index into a SPECTRUM attribute. When set, the instance
        behaves as a read-only scalar view of one vector element; writes are
        always rejected and a SPECTRUM data_format is enforced on init.

    Attributes
    ----------
    _attribute : str
        Full path of the Tango attribute.
    _unit : str
        Unit of the attribute.
    _range : tuple of (float or None, float or None) or None
        Configured range, or ``None`` to query Tango.
    _index : int or None
        Index into a SPECTRUM attribute, or ``None`` for scalar access.

    Methods
    -------
    set(value)
        Disallowed write operation.
    set_and_wait(value)
        Disallowed synchronous write operation.
    get()
        Return the current readback value of the attribute.
    """

    def __init__(
        self,
        attribute: str,
        unit: str = "",
        range: tuple[float | None, float | None] | None = None,
        index: int | None = None,
    ):
        super().__init__(
            attribute=attribute, unit=unit, range=range, index=index, writable=False
        )

        self._attribute = attribute
        self._unit = unit
        self._range = range
        self._index = index

    def set(self, value: float):
        """
        Disallowed write operation.

        Parameters
        ----------
        value : float
            Ignored.

        Raises
        ------
        pyaml.PyAMLException
            Always raised because the attribute is read-only.
        """
        raise pyaml.PyAMLException(
            f"Tango attribute {self._attribute} is not writable."
        )

    def set_and_wait(self, value: float):
        """
        Disallowed synchronous write operation.

        Parameters
        ----------
        value : float
            Ignored.

        Raises
        ------
        pyaml.PyAMLException
            Always raised because the attribute is read-only.
        """
        raise pyaml.PyAMLException(
            f"Tango attribute {self._attribute} is not writable."
        )

    def get(self) -> float:
        """
        Return the current readback value of the attribute.

        A read-only attribute has no setpoint, so this is equivalent to
        ``readback().value``.

        Returns
        -------
        float
            The readback value.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango read fails.
        """
        return self.readback().value
