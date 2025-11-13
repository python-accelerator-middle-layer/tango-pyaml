__version__ = "0.3.0"

import logging.config
import os

config_file = os.getenv("TANGO_PYAML_LOG_CONFIG", "tango_pyaml_logging.conf")

if os.path.exists(config_file):
    logging.config.fileConfig(config_file, disable_existing_loggers=False)

logger = logging.getLogger("tango.pyaml")
level = os.getenv("TANGO_PYAML_LOG_LEVEL", "").upper()
if len(level)>0:
    logger.setLevel(getattr(logging, level, logging.WARNING))
