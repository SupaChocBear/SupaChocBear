"""
logger.py
=========
Simple logger wrapper for the electrical measurements project.
Outputs timestamped messages to stdout and to a rotating log file.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_fmt = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_handler_console = logging.StreamHandler()
_handler_console.setFormatter(_fmt)

_handler_file = RotatingFileHandler(
    filename=os.path.join(LOG_DIR, "electrical.log"),
    maxBytes=5 * 1024 * 1024,   # 5 MB per file
    backupCount=3,
    encoding="utf-8",
)
_handler_file.setFormatter(_fmt)

logger = logging.getLogger("electrical")
logger.setLevel(logging.DEBUG)
logger.addHandler(_handler_console)
logger.addHandler(_handler_file)
