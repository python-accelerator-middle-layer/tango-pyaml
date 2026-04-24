import logging

import pyaml
import tango

from pyaml.control.readback_value import Value, Quality

from .attribute import Attribute, ConfigModel as AttributeConfigModel
from .tango_pyaml_utils import tango_to_PyAMLException

PYAMLCLASS = "AttributeIndexed"

logger = logging.getLogger(__name__)


class ConfigModel(AttributeConfigModel):
    """
    Configuration model for an indexed Tango SPECTRUM attribute.

    Attributes
    ----------
    attribute : str
        Full path of the Tango SPECTRUM attribute.
    index : int
        Zero-based index of the element to extract from the vector.
    unit : str, optional
        Unit of the extracted scalar value.
    range : tuple, optional
        Valid range ``[min, max]`` for the scalar. Use ``null`` for open bounds.
    """

    index: int


class AttributeIndexed(Attribute):
    """
    Scalar view of one element in a Tango SPECTRUM (vector) attribute.

    The underlying Tango attribute must have ``data_format == SPECTRUM``,
    which is enforced at first use via lazy initialisation.  ``get()`` returns
    the setpoint component (``w_value[index]``); use
    :class:`AttributeIndexedReadOnly` for READ-only Tango attributes where
    ``w_value`` is undefined.

    ``set()`` and ``set_and_wait()`` always raise: writing individual array
    elements back to Tango is not supported.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration including the attribute path and target index.

    Raises
    ------
    pyaml.PyAMLException
        At first use if the Tango attribute is not a SPECTRUM.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg, writable=False)
        self._index = cfg.index

    def initialize(self):
        super().initialize()
        if self._attr_config.data_format != tango.AttrDataFormat.SPECTRUM:
            raise pyaml.PyAMLException(
                f"Tango attribute '{self._cfg.attribute}' is not a SPECTRUM; "
                "indexed access requires a vector attribute."
            )

    def get(self):
        """
        Return the setpoint element at the configured index (``w_value[index]``).

        Raises
        ------
        pyaml.PyAMLException
            If the Tango read fails.
        """
        self._ensure_initialized()
        try:
            return self._attribute_dev.read_attribute(self._attr_name).w_value[self._index]
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

    def readback(self) -> Value:
        """
        Return the measured element at the configured index (``value[index]``).

        Returns
        -------
        Value
            Measured scalar with quality and timestamp.

        Raises
        ------
        pyaml.PyAMLException
            If the Tango read fails.
        """
        self._ensure_initialized()
        try:
            attr_value = self._attribute_dev.read_attribute(self._attr_name)
            quality = Quality[attr_value.quality.name.rsplit("_", 1)[1]]
            return Value(attr_value.value[self._index], quality, attr_value.time.todatetime())
        except tango.DevFailed as df:
            raise tango_to_PyAMLException(df)

    def set(self, value):
        """
        Raises
        ------
        pyaml.PyAMLException
            Always raised: element-level writes are not supported.
        """
        raise pyaml.PyAMLException(
            f"Indexed attribute '{self._cfg.attribute}[{self._index}]' "
            "does not support individual element writes."
        )

    def set_and_wait(self, value):
        """
        Raises
        ------
        pyaml.PyAMLException
            Always raised: element-level writes are not supported.
        """
        raise pyaml.PyAMLException(
            f"Indexed attribute '{self._cfg.attribute}[{self._index}]' "
            "does not support individual element writes."
        )

    def name(self) -> str:
        """Return the attribute path with index, e.g. ``'domain/family/member/attr[2]'``."""
        return f"{self._cfg.attribute}[{self._index}]"

    def measure_name(self) -> str:
        """Return the short attribute name with index, e.g. ``'attr[2]'``."""
        return f"{self._cfg.attribute.rsplit('/', 1)[1]}[{self._index}]"
