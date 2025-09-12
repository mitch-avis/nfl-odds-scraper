"""Implements a formatted logger for the application.

Adds optional file logging when LOG_PATH is configured in constants.
Works both in dev and in frozen PyInstaller builds.
"""

import logging
import os
from logging.config import dictConfig

try:
    # Local import to avoid circulars for constants import in logger config
    from constants import LOG_PATH
except ImportError:  # pragma: no cover - defensive
    LOG_PATH = None

# Configure the logging format and handler
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": (
                "[%(asctime)s.%(msecs)03d][%(levelname)s]"
                "[%(filename)s:%(funcName)s:%(lineno)s] %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "class": "coloredlogs.ColoredFormatter",
        },
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        # "file" handler will be added dynamically if LOG_PATH provided
    },
    "loggers": {
        "root": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Add a file handler if configured
if LOG_PATH:
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    except OSError:
        pass
    LOGGING_CONFIG["handlers"]["file"] = {
        "level": "DEBUG",
        "class": "logging.FileHandler",
        "filename": str(LOG_PATH),
        "encoding": "utf-8",
        "formatter": "default",
    }
    LOGGING_CONFIG["loggers"]["root"]["handlers"].append("file")

# Apply the logging configuration
dictConfig(LOGGING_CONFIG)

# Create a logger instance for use throughout the application
log = logging.getLogger()
