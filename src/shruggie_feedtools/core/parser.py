"""Parse orchestrator — detect → adapt → normalize.

Public API: ``parse_string``, ``parse_file``, ``parse_url``, ``parse``,
``parse_urls``, ``parse_files``.  Every function returns a ``FeedResponse``
dict (or list thereof).  Errors are captured in the response — these
functions never raise.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from shruggie_feedtools.adapters.feedparser_adapter import parse_feed as _feedparser_parse
from shruggie_feedtools.adapters.json_feed_adapter import parse_json_feed as _json_feed_parse
from shruggie_feedtools.adapters.wp_rest_adapter import parse_wp_rest as _wp_rest_parse
from shruggie_feedtools.core.config import ParserConfig
from shruggie_feedtools.core.detector import detect_feed_type
from shruggie_feedtools.core.fetcher import fetch
from shruggie_feedtools.core.normalizer import normalize_feed, normalize_item
from shruggie_feedtools.core.schema import (
    FeedItem,
    FeedMeta,
    FeedResponse,
    SourceInfo,
    SourceOrigin,
    SourceType,
    Status,
)

logger = logging.getLogger("shruggie_feedtools")

_SCHEMA_VERSION = "1.0"

# Maps detector output to SourceType enum values
_SOURCE_TYPE_MAP: dict[str, SourceType] = {
    "rss2": SourceType.RSS2,
    "rss1": SourceType.RSS1,
    "rss091": SourceType.RSS091,
    "atom10": SourceType.ATOM10,
    "atom03": SourceType.ATOM03,
    "json_feed": SourceType.JSON_FEED,
    "wp_rest": SourceType.WP_REST,
}

# Maps detector output to the adapter function
_XML_TYPES = frozenset({"rss2", "rss1", "rss091", "atom10", "atom03"})


def _error_response(
    message: str,
    origin: SourceOrigin,
    url: str | None = None,
) -> dict[str, Any]:
    """Build a schema-compliant error response dict."""
    resp = FeedResponse(
        status=Status.ERROR,
        message=message,
        schema_version=_SCHEMA_VERSION,
        source=SourceInfo(
            type=SourceType.RSS2,  # placeholder — unknown on error
            url=url,
            origin=origin,
        ),
    )
    return resp.to_dict()


def _build_response(
    adapter_result: dict[str, Any],
    origin: SourceOrigin,
    url: str | None,
    config: ParserConfig,
) -> dict[str, Any]:
    """Normalize adapter output and validate through Pydantic."""
    source_type_str = adapter_result.get("source_type", "rss2")
    source_type = _SOURCE_TYPE_MAP.get(source_type_str, SourceType.RSS2)

    feed_intermediate = adapter_result.get("feed", {})
    items_intermediate = adapter_result.get("items", [])

    # Normalize
    feed_data = normalize_feed(feed_intermediate, items_intermediate, config)
    items_data = [normalize_item(item, config) for item in items_intermediate]

    # Validate via Pydantic
    try:
        feed_meta = FeedMeta(**feed_data)
        feed_items = [FeedItem(**item) for item in items_data]

        resp = FeedResponse(
            status=Status.OK,
            schema_version=_SCHEMA_VERSION,
            source=SourceInfo(type=source_type, url=url, origin=origin),
            feed=feed_meta,
            items=feed_items,
        )
        return resp.to_dict()
    except Exception as exc:
        logger.error("Pydantic validation failed: %s", exc)
        return _error_response(f"Schema validation error: {exc}", origin, url)


def parse_string(
    content: str | bytes,
    source_url: str | None = None,
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Parse feed content from a string or bytes.

    Args:
        content: Raw feed content (XML, JSON, etc.).
        source_url: Optional URL for the ``source.url`` field.
        config: Parser configuration.

    Returns:
        Schema-compliant response dict with ``status``, ``feed``, ``items``.
    """
    if config is None:
        config = ParserConfig()

    raw = content.encode("utf-8") if isinstance(content, str) else content
    logger.debug("parse_string: %d bytes, source_url=%s", len(raw), source_url)

    if not raw or not raw.strip():
        return _error_response("Empty content", SourceOrigin.STRING, source_url)

    # Detect format
    feed_type = detect_feed_type(raw)
    logger.debug("parse_string: detected feed_type=%s", feed_type)
    if feed_type is None:
        return _error_response(
            "Content does not match any known feed format",
            SourceOrigin.STRING,
            source_url,
        )

    # Route to adapter
    try:
        adapter_result = _route_to_adapter(raw, feed_type, source_url, config)
    except Exception as exc:
        logger.error("Adapter error: %s", exc)
        return _error_response(f"Parse error: {exc}", SourceOrigin.STRING, source_url)

    return _build_response(adapter_result, SourceOrigin.STRING, source_url, config)


def parse_file(
    path: str | Path,
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Parse a feed from a local file.

    Args:
        path: Path to the feed file.
        config: Parser configuration.

    Returns:
        Schema-compliant response dict.
    """
    if config is None:
        config = ParserConfig()

    file_path = Path(path)
    if not file_path.exists():
        return _error_response(
            f"File not found: {file_path}",
            SourceOrigin.FILE,
        )

    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        return _error_response(f"File read error: {exc}", SourceOrigin.FILE)

    logger.debug("parse_file: %s (%d bytes)", file_path, len(raw))

    if not raw or not raw.strip():
        return _error_response("Empty file content", SourceOrigin.FILE)

    feed_type = detect_feed_type(raw)
    logger.debug("parse_file: detected feed_type=%s", feed_type)
    if feed_type is None:
        return _error_response(
            "File content does not match any known feed format",
            SourceOrigin.FILE,
        )

    try:
        adapter_result = _route_to_adapter(raw, feed_type, None, config)
    except Exception as exc:
        logger.error("Adapter error: %s", exc)
        return _error_response(f"Parse error: {exc}", SourceOrigin.FILE)

    return _build_response(adapter_result, SourceOrigin.FILE, None, config)


def parse_url(
    url: str,
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Fetch and parse a feed from a URL.

    Args:
        url: Feed URL to fetch.
        config: Parser configuration.

    Returns:
        Schema-compliant response dict.
    """
    if config is None:
        config = ParserConfig()

    logger.debug("parse_url: fetching %s", url)
    result = fetch(url, config)

    if not result.ok:
        logger.debug("parse_url: fetch failed — %s", result.error)
        return _error_response(result.error, SourceOrigin.URL, url)

    raw = result.content
    final_url = result.final_url or url
    logger.debug("parse_url: received %d bytes from %s", len(raw), final_url)

    if not raw or not raw.strip():
        return _error_response("Empty response body", SourceOrigin.URL, final_url)

    feed_type = detect_feed_type(raw)
    if feed_type is None:
        return _error_response(
            "Response does not match any known feed format",
            SourceOrigin.URL,
            final_url,
        )

    try:
        adapter_result = _route_to_adapter(raw, feed_type, final_url, config)
    except Exception as exc:
        logger.error("Adapter error: %s", exc)
        return _error_response(f"Parse error: {exc}", SourceOrigin.URL, final_url)

    return _build_response(adapter_result, SourceOrigin.URL, final_url, config)


def parse(
    input_value: str,
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Convenience parser — accepts a URL, file path, or raw content string.

    Sniffs the input to determine which specific parser to call:
    - Starts with ``http://`` or ``https://`` → ``parse_url``
    - Exists as a file path → ``parse_file``
    - Otherwise → ``parse_string``

    Args:
        input_value: URL, file path, or raw feed content.
        config: Parser configuration.

    Returns:
        Schema-compliant response dict.
    """
    if config is None:
        config = ParserConfig()

    stripped = input_value.strip()

    # URL detection
    if stripped.startswith(("http://", "https://")):
        return parse_url(stripped, config)

    # File path detection
    path = Path(stripped)
    if path.exists() and path.is_file():
        return parse_file(path, config)

    # Raw content
    return parse_string(input_value, config=config)


def parse_urls(
    urls: list[str],
    config: ParserConfig | None = None,
) -> list[dict[str, Any]]:
    """Parse multiple feeds from URLs.

    Args:
        urls: List of feed URLs.
        config: Parser configuration.

    Returns:
        List of schema-compliant response dicts (one per URL).
    """
    if config is None:
        config = ParserConfig()
    return [parse_url(url, config) for url in urls]


def parse_files(
    paths: list[str | Path],
    config: ParserConfig | None = None,
) -> list[dict[str, Any]]:
    """Parse multiple feeds from local files.

    Args:
        paths: List of file paths.
        config: Parser configuration.

    Returns:
        List of schema-compliant response dicts (one per file).
    """
    if config is None:
        config = ParserConfig()
    return [parse_file(p, config) for p in paths]


def _route_to_adapter(
    raw: bytes,
    feed_type: str,
    source_url: str | None,
    config: ParserConfig,
) -> dict[str, Any]:
    """Route content to the appropriate adapter based on detected type."""
    logger.debug("Routing to adapter for feed_type=%s", feed_type)
    if feed_type in _XML_TYPES:
        return _feedparser_parse(raw, config)

    if feed_type == "json_feed":
        return _json_feed_parse(raw, config)

    if feed_type == "wp_rest":
        return _wp_rest_parse(raw, base_url=source_url or "", config=config)

    msg = f"No adapter for detected type: {feed_type}"
    raise ValueError(msg)
