"""JSON Feed adapter.

Parses JSON Feed 1.0/1.1 format into intermediate dicts for normalization.
Handles all fields per §8.3 of the specification.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from shruggie_feedtools.core.config import ParserConfig

logger = logging.getLogger("shruggie_feedtools")


def parse_json_feed(
    content: bytes | str,
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Parse JSON Feed content.

    Args:
        content: Raw JSON Feed string or bytes.
        config: Parser configuration.

    Returns:
        Dict with ``source_type``, ``feed`` (intermediate dict),
        and ``items`` (list of intermediate dicts).
    """
    if config is None:
        config = ParserConfig()

    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    data = json.loads(content)

    feed = _map_feed(data)
    items_raw = data.get("items", [])
    if config.max_items is not None:
        items_raw = items_raw[: config.max_items]

    items = [_map_item(item) for item in items_raw if isinstance(item, dict)]

    return {
        "source_type": "json_feed",
        "feed": feed,
        "items": items,
    }


def _map_feed(data: dict) -> dict[str, Any]:
    """Map JSON Feed top-level fields to intermediate dict."""
    feed: dict[str, Any] = {}

    feed["title"] = data.get("title", "")
    feed["link"] = data.get("home_page_url", "")
    feed["description"] = data.get("description", "")
    feed["image"] = data.get("icon", "") or data.get("favicon", "")
    feed["language"] = data.get("language", "")

    # Author — v1.1 uses authors array, v1.0 uses author object
    authors = data.get("authors")
    if isinstance(authors, list) and authors:
        first_author = authors[0]
        if isinstance(first_author, dict):
            feed["author"] = first_author.get("name", "")
    else:
        author = data.get("author")
        if isinstance(author, dict):
            feed["author"] = author.get("name", "")

    return feed


def _map_item(item: dict) -> dict[str, Any]:
    """Map a JSON Feed item to intermediate dict."""
    data: dict[str, Any] = {}

    data["title"] = item.get("title", "")
    data["link"] = item.get("url", "")
    data["guid"] = item.get("id", "")

    # Dates
    data["pub_date"] = item.get("date_published")
    data["updated"] = item.get("date_modified")

    # Content — prefer content_html over content_text
    data["content_html"] = item.get("content_html", "")
    data["content_text"] = item.get("content_text", "")
    data["content"] = data["content_html"] or data["content_text"]

    # Summary
    data["summary"] = item.get("summary", "")

    # Image / thumbnail
    data["thumbnail"] = item.get("image", "") or item.get("banner_image", "")

    # Tags → categories
    data["tags"] = item.get("tags", [])

    # Authors
    authors = item.get("authors")
    if isinstance(authors, list) and authors:
        first = authors[0]
        if isinstance(first, dict):
            data["author"] = first.get("name", "")
    else:
        author = item.get("author")
        if isinstance(author, dict):
            data["author"] = author.get("name", "")

    # Attachments → enclosures
    attachments = item.get("attachments", [])
    enclosures = []
    for att in attachments:
        if isinstance(att, dict):
            url = att.get("url", "")
            if url:
                enclosures.append({
                    "url": url,
                    "type": att.get("mime_type", ""),
                    "length": att.get("size_in_bytes"),
                })
    data["enclosures"] = enclosures

    # External URL
    data["external_url"] = item.get("external_url", "")

    return data
