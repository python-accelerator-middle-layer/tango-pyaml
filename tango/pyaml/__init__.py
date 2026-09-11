"""
Tango backend for pyAML.

This package bridges `Tango Controls <https://www.tango-controls.org/>`_ and
the pyAML abstraction layer. It exposes Tango attributes and attribute groups
as pyAML :class:`~pyaml.control.deviceaccess.DeviceAccess` objects, provides a
:class:`~tango.pyaml.controlsystem.TangoControlSystem` implementation and
catalogs that resolve pyAML device keys into Tango attribute references.

The package registers its configuration schemas with pyAML through the
``pyaml.schemas`` entry point, so the classes below can be used directly in
pyAML YAML configuration files.

Logging is configured at import time from two optional environment variables:

``TANGO_PYAML_LOG_CONFIG``
    Path to a :mod:`logging.config` file (default ``tango_pyaml_logging.conf``
    in the current directory). Loaded only if the file exists.
``TANGO_PYAML_LOG_LEVEL``
    Level name (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``)
    applied to the ``tango.pyaml`` logger.
"""

import logging.config
import os

from ._version import __version__ as __version__

config_file = os.getenv("TANGO_PYAML_LOG_CONFIG", "tango_pyaml_logging.conf")

if os.path.exists(config_file):
    logging.config.fileConfig(config_file, disable_existing_loggers=False)

logger = logging.getLogger("tango.pyaml")
level = os.getenv("TANGO_PYAML_LOG_LEVEL", "").upper()
if len(level) > 0:
    logger.setLevel(getattr(logging, level, logging.WARNING))
