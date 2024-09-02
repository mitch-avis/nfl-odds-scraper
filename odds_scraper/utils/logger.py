"""Implements a formatted logger for the application."""

import logging
from logging.config import dictConfig

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
    },
    "loggers": {
        "root": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Apply the logging configuration
dictConfig(LOGGING_CONFIG)
# Create a logger instance for use throughout the application
log = logging.getLogger()
