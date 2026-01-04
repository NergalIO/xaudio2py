"""Logging configuration."""

import logging
from typing import Dict

_loggers: Dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger for the given name."""
    if name not in _loggers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)  # Only show warnings and errors
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(handler)
        _loggers[name] = logger
    return _loggers[name]

