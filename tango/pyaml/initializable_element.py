"""
Lazy initialization support for Tango-backed elements.

Tango connections are expensive and may fail when the control system is not
reachable. Elements derived from :class:`InitializableElement` postpone any
Tango call until the first access, through :meth:`_ensure_initialized`.
"""

from abc import ABCMeta, abstractmethod


class InitializableElement(metaclass=ABCMeta):
    """
    Base class for elements whose Tango resources are created lazily.

    Subclasses implement :meth:`initialize` to open the Tango connections
    they need and call :meth:`_ensure_initialized` at the beginning of every
    method that requires them.

    Attributes
    ----------
    _initialized : bool
        ``True`` once :meth:`initialize` has been called.

    Methods
    -------
    initialize()
        Create the Tango resources needed by the element.
    name()
        Return the element name.
    is_initialized()
        Tell whether the element has already been initialized.
    """

    def __init__(self):
        self._initialized = False

    @abstractmethod
    def initialize(self):
        """
        Create the Tango resources needed by the element.

        Subclasses must call ``super().initialize()`` so that the
        initialization flag is set.
        """
        self._initialized = True

    @abstractmethod
    def name(self) -> str:
        """
        Return the element name.

        Returns
        -------
        str
            Element name.
        """
        return ""

    def is_initialized(self) -> bool:
        """
        Tell whether the element has already been initialized.

        Returns
        -------
        bool
            ``True`` if :meth:`initialize` has been called.
        """
        return self._initialized

    def _ensure_initialized(self):
        """Call :meth:`initialize` if it has not been called yet."""
        if not self.is_initialized():
            self.initialize()
