"""Title, description, and GUID derivation strategies.

All functions in this module are pure — they take input data and configuration,
and return a derived string. No side effects, no I/O.
"""

from __future__ import annotations

import hashlib
import math
import re
import uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate_at_word_boundary(text: str, max_length: int) -> str:
    """Truncate *text* to at most *max_length* chars, breaking at a word boundary.

    If truncation is needed, the result ends with ``…`` (U+2026) and the total
    length including the ellipsis is ≤ *max_length*.
    """
    if len(text) <= max_length:
        return text

    # Reserve one char for ellipsis
    limit = max_length - 1
    if limit <= 0:
        return "…"

    truncated = text[:limit]

    # If we cut mid-word, back up to the last space
    if not text[limit:limit + 1].isspace() and " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]

    return truncated + "…"


def _slugify(text: str) -> str:
    """Convert *text* to a URL-safe slug (lowercase alphanumerics + hyphens)."""
    # Lowercase and replace non-alphanumeric chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug or "feed"


def _format_timestamp_title(timestamp: str) -> str:
    """Format an ISO 8601 UTC timestamp for use as a title.

    ``"2026-02-10T08:30:00Z"`` → ``"2026-02-10 08:30:00 UTC"``
    """
    ts = timestamp.replace("T", " ").replace("Z", "")
    return f"{ts} UTC"


# ---------------------------------------------------------------------------
# Title strategies
# ---------------------------------------------------------------------------


def derive_title(
    text: str,
    strategy: str,
    max_length: int = 120,
    timestamp: str = "",
    index: int = 0,
    title_template: str | None = None,
) -> str:
    """Derive an item title from text using the given strategy.

    Parameters
    ----------
    text:
        The raw text input.
    strategy:
        One of ``first_line``, ``truncate``, ``timestamp``, ``template``, ``none``.
    max_length:
        Maximum title length for ``first_line`` and ``truncate`` strategies.
    timestamp:
        ISO 8601 timestamp (used by ``timestamp`` and ``template`` strategies).
    index:
        1-based item index within a batch (used by ``template`` strategy).
    title_template:
        Template string with ``{timestamp}`` and ``{index}`` placeholders.
    """
    if strategy == "first_line":
        first = text.split("\n", 1)[0]
        return _truncate_at_word_boundary(first, max_length)
    if strategy == "truncate":
        return _truncate_at_word_boundary(text, max_length)
    if strategy == "timestamp":
        return _format_timestamp_title(timestamp)
    if strategy == "template":
        tmpl = title_template or ""
        formatted_ts = _format_timestamp_title(timestamp)
        return tmpl.replace("{timestamp}", formatted_ts).replace("{index}", str(index))
    if strategy == "none":
        return ""

    return ""


# ---------------------------------------------------------------------------
# Description strategies
# ---------------------------------------------------------------------------


def derive_description(
    text: str,
    strategy: str,
    max_length: int = 280,
) -> str:
    """Derive an item description from text using the given strategy.

    Parameters
    ----------
    text:
        The raw text input.
    strategy:
        One of ``truncate``, ``first_line``, ``same``, ``none``.
    max_length:
        Maximum length for the ``truncate`` strategy.
    """
    if strategy == "truncate":
        return _truncate_at_word_boundary(text, max_length)
    if strategy == "first_line":
        return text.split("\n", 1)[0]
    if strategy == "same":
        return text
    if strategy == "none":
        return ""

    return ""


# ---------------------------------------------------------------------------
# GUID strategies
# ---------------------------------------------------------------------------


def generate_guid(
    text: str,
    timestamp: str,
    strategy: str,
    feed_title: str = "",
    index: int = 0,
    batch_size: int = 1,
) -> str:
    """Generate a GUID for an item.

    Parameters
    ----------
    text:
        The raw text input.
    timestamp:
        ISO 8601 timestamp string.
    strategy:
        One of ``sha256``, ``uuid4``, ``timestamp``, ``sequential``.
    feed_title:
        Feed title (used by ``sequential`` strategy for the slug).
    index:
        1-based item index (used by ``sequential`` strategy).
    batch_size:
        Total items in the batch (used by ``sequential`` for zero-padding width).
    """
    if strategy == "sha256":
        content = text + timestamp
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    if strategy == "uuid4":
        return str(uuid.uuid4())
    if strategy == "timestamp":
        return timestamp
    if strategy == "sequential":
        slug = _slugify(feed_title)
        # Determine padding width: at least 3 digits
        width = max(3, len(str(batch_size)))
        return f"{slug}-{str(index).zfill(width)}"

    return ""


# ---------------------------------------------------------------------------
# Link generation
# ---------------------------------------------------------------------------


def generate_link(pattern: str | None, guid: str) -> str:
    """Generate an item link from a URL pattern by substituting ``{guid}``.

    Returns an empty string if *pattern* is ``None``.
    """
    if pattern is None:
        return ""
    return pattern.replace("{guid}", guid)
