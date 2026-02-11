"""Structured logging setup for shruggie-feedtools.

Provides a named logger ``shruggie_feedtools`` with configurable level.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: int = logging.WARNING) -> logging.Logger:
    """Configure and return the shruggie_feedtools logger.

    Args:
        level: Logging level (e.g. ``logging.DEBUG``, ``logging.WARNING``).

    Returns:
        The configured logger instance.
    """
    logger = logging.getLogger("shruggie_feedtools")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_logger() -> logging.Logger:
    """Return the shruggie_feedtools logger (creating it if needed)."""
    return logging.getLogger("shruggie_feedtools")
