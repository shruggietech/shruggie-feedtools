"""Feed type auto-detection.

Determines the format of raw feed content (bytes) by inspecting structure:
- XML feeds are routed through feedparser for version sniffing
- JSON content is checked for JSON Feed or WordPress REST signatures
- An optional content-type hint (from HTTP headers or file extension) is used
  as a fallback when byte-level sniffing is inconclusive.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import feedparser

logger = logging.getLogger("shruggie_feedtools")

# Maps feedparser version strings to our canonical source type strings
_FEEDPARSER_VERSION_MAP: dict[str, str] = {
    "rss20": "rss2",
    "rss10": "rss1",
    "rss091": "rss091",
    "rss092": "rss091",
    "rss093": "rss091",
    "atom10": "atom10",
    "atom03": "atom03",
}

# Content-type substrings that indicate JSON content
_JSON_CONTENT_TYPES = (
    "application/json",
    "application/feed+json",
    "text/json",
    "application/vnd.api+json",
)

# Content-type substrings that indicate XML/feed content
_XML_CONTENT_TYPES = (
    "application/rss+xml",
    "application/atom+xml",
    "application/xml",
    "text/xml",
    "application/rdf+xml",
)

# BOMs to strip before detection
_BOM_MAP: list[tuple[bytes, str]] = [
    (b"\xef\xbb\xbf", "utf-8-sig"),       # UTF-8 BOM
    (b"\xff\xfe\x00\x00", "utf-32-le"),    # UTF-32 LE (check before UTF-16 LE)
    (b"\x00\x00\xfe\xff", "utf-32-be"),    # UTF-32 BE
    (b"\xff\xfe", "utf-16-le"),            # UTF-16 LE
    (b"\xfe\xff", "utf-16-be"),            # UTF-16 BE
]


def detect_feed_type(
    content: bytes,
    content_type: str | None = None,
) -> str | None:
    """Detect the feed format from raw bytes.

    Routes content through either the XML path (via feedparser) or the
    JSON path (structure sniffing) based on the first non-whitespace byte.
    Falls back to content-type hints when byte-sniffing is inconclusive.

    Args:
        content: Raw bytes of the feed content.
        content_type: Optional HTTP Content-Type header value (e.g.
            ``"application/feed+json; charset=utf-8"``).  Used as a
            fallback when byte-level detection fails.

    Returns:
        A format string (``"rss2"``, ``"atom10"``, ``"rss1"``, ``"json_feed"``,
        ``"wp_rest"``, etc.) or ``None`` if the content does not match any
        known feed format.
    """
    if not content:
        logger.debug("detect_feed_type: empty content")
        return None

    # Strip BOM if present and re-encode to UTF-8 for non-UTF-8 encodings
    stripped = content.lstrip()
    decoded_content: bytes = content
    for bom_bytes, encoding in _BOM_MAP:
        if content.startswith(bom_bytes):
            try:
                text = content[len(bom_bytes):].decode(encoding, errors="replace")
                decoded_content = text.encode("utf-8")
                stripped = decoded_content.lstrip()
            except Exception:
                # Fallback: just strip the BOM bytes
                stripped = content[len(bom_bytes):].lstrip()
                decoded_content = stripped
            break

    if not stripped:
        return None

    first_byte = stripped[0:1]

    # JSON path
    if first_byte in (b"{", b"["):
        result = _detect_json_type(stripped)
        logger.debug("detect_feed_type: JSON path -> %s", result)
        if result is not None:
            return result

    # XML path
    if first_byte == b"<":
        result = _detect_xml_type(stripped)
        logger.debug("detect_feed_type: XML path -> %s", result)
        if result is not None:
            return result

    # ----- Content-type fallback -----
    # When byte-sniffing fails (e.g. unusual encoding, leading whitespace after
    # BOM stripping that still left garbage, or an unexpected wrapper), use the
    # content-type header as a hint to try the other detection path.
    ct_lower = (content_type or "").lower().split(";")[0].strip()

    if ct_lower and first_byte not in (b"{", b"["):
        # Content-Type says JSON but first byte wasn't { or [
        if any(jct in ct_lower for jct in _JSON_CONTENT_TYPES):
            logger.debug(
                "detect_feed_type: content-type '%s' suggests JSON; "
                "attempting JSON detection despite first_byte=%r",
                ct_lower, first_byte,
            )
            result = _detect_json_type(decoded_content)
            if result is not None:
                return result

    if ct_lower and first_byte != b"<":
        # Content-Type says XML but first byte wasn't <
        if any(xct in ct_lower for xct in _XML_CONTENT_TYPES):
            logger.debug(
                "detect_feed_type: content-type '%s' suggests XML; "
                "attempting XML detection despite first_byte=%r",
                ct_lower, first_byte,
            )
            result = _detect_xml_type(decoded_content)
            if result is not None:
                return result

    # ----- File extension fallback for local files -----
    # (content_type might be a filename hint like ".json")
    if ct_lower.endswith(".json") or ct_lower.endswith(".json\""):
        result = _detect_json_type(decoded_content)
        if result is not None:
            return result

    logger.debug(
        "detect_feed_type: unrecognized (first_byte=%r, content_type=%r)",
        first_byte, content_type,
    )
    return None


def _detect_json_type(content: bytes) -> str | None:
    """Detect JSON-based feed types: JSON Feed or WordPress REST."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.debug("JSON parse failed during detection")
        return None

    # JSON Feed: object with "version" containing "jsonfeed.org"
    if isinstance(data, dict):
        version = data.get("version", "")
        if isinstance(version, str):
            # Primary: full spec URL (e.g. "https://jsonfeed.org/version/1.1")
            if "jsonfeed.org" in version:
                return "json_feed"
            # Fallback: bare version strings used by non-compliant generators
            if version in ("1", "1.0", "1.1"):
                # Only if other JSON Feed markers are present
                if "items" in data and ("title" in data or "home_page_url" in data):
                    logger.debug(
                        "JSON Feed detected via bare version '%s' (non-standard)", version
                    )
                    return "json_feed"

    # WordPress REST: array of objects with title.rendered and _links
    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        if isinstance(first, dict):
            title = first.get("title")
            if isinstance(title, dict) and "rendered" in title:
                if "_links" in first:
                    return "wp_rest"
                # Fallback: _links stripped by cache/CDN — check secondary markers
                if _has_wp_rest_markers(first):
                    logger.debug(
                        "WP REST detected without _links (secondary markers)"
                    )
                    return "wp_rest"

    # Single WP REST post object (less common but possible)
    if isinstance(data, dict):
        title = data.get("title")
        if isinstance(title, dict) and "rendered" in title:
            if "_links" in data:
                return "wp_rest"
            if _has_wp_rest_markers(data):
                logger.debug(
                    "WP REST single object detected without _links (secondary markers)"
                )
                return "wp_rest"

    # Log unrecognized JSON for diagnostics
    if isinstance(data, dict):
        logger.debug(
            "JSON detected but unrecognized; top-level keys: %s",
            list(data.keys())[:10],
        )
    elif isinstance(data, list):
        first_keys = list(data[0].keys())[:10] if data and isinstance(data[0], dict) else "N/A"
        logger.debug(
            "JSON array detected but unrecognized; length=%d, first-item keys: %s",
            len(data), first_keys,
        )

    return None


def _has_wp_rest_markers(obj: dict[str, Any]) -> bool:
    """Check for secondary WordPress REST API markers when _links is absent."""
    # A WP REST post typically has several of these fields
    wp_markers = ("slug", "date_gmt", "modified_gmt", "guid", "type", "status")
    hits = sum(1 for k in wp_markers if k in obj)
    if hits < 2:
        return False
    # Extra confidence: "type" is usually "post" or "page"
    obj_type = obj.get("type", "")
    if isinstance(obj_type, str) and obj_type in ("post", "page", "attachment", "revision"):
        return True
    # Or "guid" is a dict with "rendered"
    guid = obj.get("guid")
    if isinstance(guid, dict) and "rendered" in guid:
        return True
    return hits >= 3


def _detect_xml_type(content: bytes) -> str | None:
    """Detect XML feed type using feedparser's version sniffing."""
    try:
        result = feedparser.parse(content)
    except Exception:
        logger.debug("feedparser raised an exception during detection")
        return None

    version = getattr(result, "version", "") or ""

    if not version:
        # feedparser couldn't identify it (e.g., an HTML page)
        return None

    canonical = _FEEDPARSER_VERSION_MAP.get(version)
    if canonical:
        return canonical

    # Fallback: if feedparser reports a version we don't have mapped,
    # but it's clearly RSS or Atom, try to match
    version_lower = version.lower()
    if version_lower.startswith("rss"):
        return "rss2"  # Default RSS variant
    if version_lower.startswith("atom"):
        return "atom10"  # Default Atom variant

    return None
