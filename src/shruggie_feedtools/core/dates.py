"""Date parsing and normalization.

All dates in shruggie-feedtools output are ISO 8601 in UTC (YYYY-MM-DDTHH:MM:SSZ).
This module handles conversion from any supported input format to that canonical form.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

logger = logging.getLogger("shruggie_feedtools")


def normalize_date(value: str | int | float | None) -> str | None:
    """Normalize a date value to ISO 8601 UTC string (``...Z``).

    Accepts:
        - RFC 822 / RFC 2822 strings
        - ISO 8601 strings (with or without timezone offset)
        - Loose date formats (e.g. "February 9, 2026", "2026-02-09")
        - Naive datetimes (assumed UTC)
        - Unix epoch integers or floats

    Returns:
        ISO 8601 UTC string (e.g. ``"2026-02-09T12:00:00Z"``) or ``None``
        if the input cannot be parsed.

    Never raises on bad input.
    """
    if value is None:
        return None

    # Handle numeric epoch values
    if isinstance(value, (int, float)):
        logger.debug("normalize_date: handling epoch value %r", value)
        try:
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
            return _format_utc(dt)
        except (OSError, OverflowError, ValueError):
            logger.warning("Unparseable epoch value: %r", value)
            return None

    if not isinstance(value, str):
        logger.warning("Unparseable date type: %r", type(value))
        return None

    value = value.strip()
    if not value:
        return None

    # Try parsing as a numeric string (epoch)
    if re.match(r"^\d+\.?\d*$", value):
        try:
            epoch = float(value)
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            return _format_utc(dt)
        except (OSError, OverflowError, ValueError):
            pass

    # Try dateutil parsing
    try:
        # Use a default datetime with day=1, hour=0, minute=0, second=0
        # so partial dates like "Feb 2026" resolve to the first of the month
        default_dt = datetime(2000, 1, 1, 0, 0, 0)
        dt = dateutil_parser.parse(value, default=default_dt)
        # If naive (no timezone info), assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return _format_utc(dt)
    except (ValueError, OverflowError, TypeError):
        pass

    logger.warning("Unparseable date value: %r", value)
    return None


def _format_utc(dt: datetime) -> str:
    """Format a UTC datetime as ISO 8601 with Z suffix, truncated to seconds."""
    # Truncate microseconds
    dt = dt.replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
