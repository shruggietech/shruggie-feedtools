"""Structured logging setup for shruggie-feedtools.

Provides a named logger ``shruggie_feedtools`` with configurable level.
Supports optional file-based debug logging for diagnostics.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_FILE_HANDLER: logging.FileHandler | None = None
_CONSOLE_HANDLER: logging.StreamHandler | None = None


def setup_logging(level: int = logging.WARNING) -> logging.Logger:
    """Configure and return the shruggie_feedtools logger.

    Args:
        level: Logging level (e.g. ``logging.DEBUG``, ``logging.WARNING``).

    Returns:
        The configured logger instance.
    """
    global _CONSOLE_HANDLER
    logger = logging.getLogger("shruggie_feedtools")
    logger.setLevel(level)

    if not _CONSOLE_HANDLER:
        _CONSOLE_HANDLER = logging.StreamHandler(sys.stderr)
        _CONSOLE_HANDLER.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        _CONSOLE_HANDLER.setFormatter(formatter)
        logger.addHandler(_CONSOLE_HANDLER)
    else:
        _CONSOLE_HANDLER.setLevel(level)

    return logger


def get_logger() -> logging.Logger:
    """Return the shruggie_feedtools logger (creating it if needed)."""
    return logging.getLogger("shruggie_feedtools")


def get_log_file_path() -> Path:
    """Determine the log file path based on the running executable.

    The log file is placed next to the executable with a ``.log`` extension.
    For frozen apps (PyInstaller), uses ``sys.executable``.
    For script execution, uses ``sys.argv[0]``.
    """
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable)
    else:
        exe_path = Path(sys.argv[0]).resolve()
    return exe_path.with_suffix(".log")


def setup_file_logging(log_path: str | Path | None = None) -> Path:
    """Enable file-based DEBUG logging.

    Args:
        log_path: Path for the log file.  If ``None``, auto-determined
            from the running executable via :func:`get_log_file_path`.

    Returns:
        The resolved log file path.
    """
    global _FILE_HANDLER

    # Remove existing file handler if any
    disable_file_logging()

    if log_path is None:
        log_path = get_log_file_path()
    else:
        log_path = Path(log_path)

    logger = logging.getLogger("shruggie_feedtools")
    logger.setLevel(logging.DEBUG)

    _FILE_HANDLER = logging.FileHandler(str(log_path), encoding="utf-8")
    _FILE_HANDLER.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s.%(funcName)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    _FILE_HANDLER.setFormatter(formatter)
    logger.addHandler(_FILE_HANDLER)

    logger.debug("Debug file logging enabled — log file: %s", log_path)
    logger.debug("Python %s on %s", sys.version, sys.platform)
    return log_path


def disable_file_logging() -> None:
    """Remove the file handler and revert to console-only logging."""
    global _FILE_HANDLER
    if _FILE_HANDLER is not None:
        logger = logging.getLogger("shruggie_feedtools")
        logger.debug("Debug file logging disabled")
        logger.removeHandler(_FILE_HANDLER)
        _FILE_HANDLER.close()
        _FILE_HANDLER = None
        # Restore logger level to WARNING if no file handler
        logger.setLevel(logging.WARNING)


def is_file_logging_enabled() -> bool:
    """Return whether file logging is currently active."""
    return _FILE_HANDLER is not None
