import logging

from .attribute_indexed import AttributeIndexed, ConfigModel  # noqa: F401 — ConfigModel re-exported

PYAMLCLASS = "AttributeIndexedReadOnly"

logger = logging.getLogger(__name__)


class AttributeIndexedReadOnly(AttributeIndexed):
    """
    Read-only scalar view of one element in a Tango SPECTRUM attribute.

    Use this class for READ Tango attributes where ``w_value`` is undefined.
    ``get()`` returns the measured value (``value[index]``), identical to
    :meth:`readback`.

    Parameters
    ----------
    cfg : ConfigModel
        Configuration including the attribute path and target index.
    """

    def get(self):
        """Return the measured element at the configured index (same as readback)."""
        return self.readback().value
