"""Entry parsing for JSONL and per-entry overrides.

Parses JSONL files (or lists of strings) into entry dicts.  Each line must
contain at least ``text`` and ``timestamp``.  Additional fields become per-entry
overrides that take precedence over template ``item_defaults``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("shruggie_feedtools")


def parse_entries(jsonl_path_or_lines: str | Path | list[str]) -> list[dict[str, Any]]:
    """Parse JSONL entries from a file path or a list of JSON strings.

    Parameters
    ----------
    jsonl_path_or_lines:
        Either a filesystem path to a ``.jsonl`` file, or a list of JSON
        strings (one JSON object per string).

    Returns
    -------
    list[dict]
        Parsed entry dicts, each guaranteed to contain ``text`` and ``timestamp``.
        Malformed lines are skipped with a warning.
    """
    if isinstance(jsonl_path_or_lines, (str, Path)):
        path = Path(jsonl_path_or_lines)
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = jsonl_path_or_lines

    entries: list[dict[str, Any]] = []

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Skipping malformed JSON on line %d: %s", line_no, raw_line)
            continue

        if not isinstance(obj, dict):
            logger.warning("Skipping non-object on line %d", line_no)
            continue

        if "text" not in obj:
            logger.warning("Skipping line %d: missing 'text' field", line_no)
            continue

        if "timestamp" not in obj:
            logger.warning("Skipping line %d: missing 'timestamp' field", line_no)
            continue

        entries.append(obj)

    return entries
