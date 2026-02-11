"""HTML utilities — thumbnail extraction and helpers.

Provides functions for extracting image URLs from HTML content,
used by the normalizer for thumbnail fallback chains.
"""

from __future__ import annotations

import re

_IMG_SRC_RE = re.compile(
    r'<img\s[^>]*?\bsrc\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def extract_thumbnail(html_content: str) -> str:
    """Extract the first image URL from HTML content.

    Scans for ``<img>`` tags and returns the ``src`` attribute of the first
    one found. Does not validate that the URL is reachable.

    Args:
        html_content: HTML string potentially containing ``<img>`` tags.

    Returns:
        The URL of the first image found, or ``""`` if none.
    """
    if not html_content:
        return ""

    match = _IMG_SRC_RE.search(html_content)
    if match:
        return match.group(1)

    return ""
