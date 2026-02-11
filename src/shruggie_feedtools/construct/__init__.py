"""Feed construction from templates.

Public API
----------
- ``construct(text, timestamp, template)`` — single-item convenience
- ``construct_batch(entries, template)`` — multi-item from list or JSONL
- ``load_template(path_or_dict)`` — load and validate a template
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shruggie_feedtools.construct.builder import build_feed
from shruggie_feedtools.construct.entry import parse_entries
from shruggie_feedtools.construct.template import (
    FeedTemplate,
    TemplateValidationError,
    load_template,
)

__all__ = [
    "construct",
    "construct_batch",
    "load_template",
    "FeedTemplate",
    "TemplateValidationError",
]


def _resolve_template(
    template: str | Path | dict[str, Any] | FeedTemplate,
) -> FeedTemplate:
    """Resolve a template argument to a ``FeedTemplate`` instance."""
    if isinstance(template, FeedTemplate):
        return template
    return load_template(template)


def construct(
    text: str,
    timestamp: str | int | float,
    template: str | Path | dict[str, Any] | FeedTemplate,
) -> dict[str, Any]:
    """Construct a single-item feed from text, a timestamp, and a template.

    Parameters
    ----------
    text:
        Raw text content for the item body.
    timestamp:
        When this entry occurred (ISO 8601 string or Unix epoch).
    template:
        A file path, dict, or pre-loaded ``FeedTemplate``.

    Returns
    -------
    dict
        Schema-compliant feed output with one item.
    """
    tmpl = _resolve_template(template)
    entries = [{"text": text, "timestamp": str(timestamp)}]
    return build_feed(entries, tmpl)


def construct_batch(
    entries: list[dict[str, Any]] | str | Path,
    template: str | Path | dict[str, Any] | FeedTemplate,
) -> dict[str, Any]:
    """Construct a multi-item feed from entries and a template.

    Parameters
    ----------
    entries:
        A list of entry dicts (each with ``text`` and ``timestamp``), or a
        path to a JSONL file.
    template:
        A file path, dict, or pre-loaded ``FeedTemplate``.

    Returns
    -------
    dict
        Schema-compliant feed output with one item per entry.
    """
    tmpl = _resolve_template(template)

    if isinstance(entries, (str, Path)):
        parsed = parse_entries(entries)
    else:
        parsed = entries

    return build_feed(parsed, tmpl)
