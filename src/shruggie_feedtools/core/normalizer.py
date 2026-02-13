"""Adapter output → schema mapping normalizer.

Takes intermediate dicts from any adapter and maps them into the final
output schema fields. Implements fallback chains, date normalization,
thumbnail extraction, category deduplication, and extension bucketing.
"""

from __future__ import annotations

import logging
from typing import Any

from shruggie_feedtools.core.config import ParserConfig
from shruggie_feedtools.core.dates import normalize_date
from shruggie_feedtools.utils.html import extract_thumbnail

logger = logging.getLogger("shruggie_feedtools")

# Namespace prefixes that map to first-class schema fields (not extensions)
_KNOWN_FIRST_CLASS_PREFIXES = frozenset()


def normalize_feed(
    intermediate: dict[str, Any],
    items_intermediate: list[dict[str, Any]],
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Normalize adapter feed-level output to schema fields.

    Args:
        intermediate: Feed-level intermediate dict from an adapter.
        items_intermediate: List of item intermediate dicts (used to compute
            ``last_updated`` if not present in feed data).
        config: Parser configuration.

    Returns:
        Dict matching the FeedMeta schema fields.
    """
    if config is None:
        config = ParserConfig()

    feed: dict[str, Any] = {}
    logger.debug("normalize_feed: processing feed-level fields")

    feed["title"] = _str(intermediate, "title")
    feed["link"] = _str(intermediate, "link")
    feed["description"] = (
        _str(intermediate, "description")
        or _str(intermediate, "subtitle")
    )
    feed["language"] = _str(intermediate, "language")
    feed["author"] = _extract_author(intermediate)
    feed["image"] = (
        _str(intermediate, "image")
        or _str(intermediate, "logo")
        or _str(intermediate, "icon")
    )

    # last_updated: from feed data, or computed from item dates
    raw_updated = intermediate.get("updated") or intermediate.get("last_updated")
    if raw_updated:
        feed["last_updated"] = normalize_date(raw_updated)
    else:
        # Compute from latest item pub_date
        feed["last_updated"] = _compute_latest_date(items_intermediate)

    feed["generator"] = _str(intermediate, "generator")

    # Categories
    raw_cats = intermediate.get("categories", [])
    feed["categories"] = _normalize_categories(raw_cats)

    # TTL
    raw_ttl = intermediate.get("ttl")
    feed["ttl"] = _parse_int(raw_ttl)

    # Extensions
    if config.include_extensions:
        feed["extensions"] = _extract_extensions(intermediate, _FEED_SKIP_KEYS)
    else:
        feed["extensions"] = {}

    return feed


def normalize_item(
    intermediate: dict[str, Any],
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Normalize adapter item output to schema fields.

    Implements fallback chains for description, author, guid, and thumbnail.

    Args:
        intermediate: Item intermediate dict from an adapter.
        config: Parser configuration.

    Returns:
        Dict matching the FeedItem schema fields.
    """
    if config is None:
        config = ParserConfig()

    item: dict[str, Any] = {}
    logger.debug("normalize_item: processing item title=%s", _str(intermediate, "title")[:60])

    item["title"] = _str(intermediate, "title")
    item["link"] = _str(intermediate, "link")

    # GUID: prefer guid, fall back to id, then link
    item["guid"] = (
        _str(intermediate, "guid")
        or _str(intermediate, "id")
        or _str(intermediate, "link")
    )
    item["guid_is_permalink"] = _parse_bool(intermediate.get("guid_is_permalink", False))

    # Dates
    raw_pub = (
        intermediate.get("pub_date")
        or intermediate.get("published")
        or intermediate.get("date")
    )
    item["pub_date"] = normalize_date(raw_pub) if raw_pub else None

    raw_updated = intermediate.get("updated") or intermediate.get("modified")
    item["updated"] = normalize_date(raw_updated) if raw_updated else None

    # Author fallback chain: author > dc:creator > author_detail.name
    item["author"] = _extract_item_author(intermediate)

    # Content: prefer content:encoded > content > content_html > content_text
    content_val = (
        _str(intermediate, "content:encoded")
        or _str(intermediate, "content_encoded")
        or _str(intermediate, "content")
        or _str(intermediate, "content_html")
        or _str(intermediate, "content_text")
    )
    item["content"] = content_val

    # Description fallback chain: description > summary > excerpt > truncated content
    desc_val = (
        _str(intermediate, "description")
        or _str(intermediate, "summary")
        or _str(intermediate, "excerpt")
    )
    if not desc_val and content_val:
        desc_val = _truncate_text(content_val, 280)
    item["description"] = desc_val

    # If content and description are the same and we have a summary, prefer it
    if (
        item["content"]
        and item["description"]
        and item["content"] == item["description"]
        and _str(intermediate, "summary")
    ):
        item["description"] = _str(intermediate, "summary")

    # Thumbnail fallback chain
    if config.thumbnail_extraction:
        item["thumbnail"] = _extract_thumbnail_chain(intermediate, content_val)
    else:
        item["thumbnail"] = ""

    # Enclosures
    item["enclosures"] = _normalize_enclosures(intermediate)

    # Categories
    raw_cats = intermediate.get("categories") or intermediate.get("tags") or []
    item["categories"] = _normalize_categories(raw_cats)

    # Comments
    item["comments_url"] = intermediate.get("comments_url") or intermediate.get("comments") or None
    raw_cc = intermediate.get("comments_count") or intermediate.get("slash:comments")
    item["comments_count"] = _parse_int(raw_cc)

    # Extensions
    if config.include_extensions:
        item["extensions"] = _extract_extensions(intermediate, _ITEM_SKIP_KEYS)
    else:
        item["extensions"] = {}

    return item


# --------------------------------------------------------------------------
# Keys to skip when building extensions (these are mapped to first-class fields)
# --------------------------------------------------------------------------

_FEED_SKIP_KEYS = frozenset({
    "title", "link", "description", "subtitle", "language", "author",
    "author_detail", "image", "logo", "icon", "updated", "last_updated",
    "generator", "categories", "ttl", "links", "href", "type",
    "publisher", "publisher_detail", "id", "rights", "rights_detail",
    "tags", "cloud", "docs", "managing_editor",
})

_ITEM_SKIP_KEYS = frozenset({
    "title", "link", "guid", "id", "guid_is_permalink", "pub_date",
    "published", "date", "updated", "modified", "author", "author_detail",
    "dc:creator", "content:encoded", "content_encoded", "content",
    "content_html", "content_text", "description", "summary", "excerpt",
    "thumbnail", "enclosures", "enclosure", "categories", "tags",
    "comments_url", "comments", "comments_count", "slash:comments",
    "links", "source", "attachments", "image", "banner_image",
    "media:thumbnail", "media:content",
})


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------


def _str(d: dict, key: str) -> str:
    """Get a string value from a dict, returning '' for missing/None."""
    val = d.get(key)
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    return str(val).strip()


def _parse_int(val: Any) -> int | None:
    """Parse a value as integer, returning None on failure."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_bool(val: Any) -> bool:
    """Parse a value to boolean."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def _extract_author(data: dict) -> str:
    """Extract author from feed-level intermediate dict."""
    # Direct author string
    author = _str(data, "author")
    if author:
        return author

    # author_detail (feedparser style)
    detail = data.get("author_detail")
    if isinstance(detail, dict):
        name = detail.get("name", "")
        if name:
            return name.strip()

    # dc:creator
    creator = _str(data, "dc:creator")
    if creator:
        return creator

    return ""


def _extract_item_author(data: dict) -> str:
    """Extract author from item-level intermediate dict."""
    # Direct author string
    author = _str(data, "author")
    if author:
        return author

    # dc:creator fallback
    creator = _str(data, "dc:creator")
    if creator:
        return creator

    # author_detail (feedparser Atom style)
    detail = data.get("author_detail")
    if isinstance(detail, dict):
        name = detail.get("name", "")
        if name:
            return name.strip()

    return ""


def _extract_thumbnail_chain(data: dict, content: str) -> str:
    """Extract thumbnail URL via fallback chain."""
    # Direct thumbnail field
    thumb = _str(data, "thumbnail")
    if thumb:
        return thumb

    # media:thumbnail
    media_thumb = data.get("media:thumbnail")
    if isinstance(media_thumb, str) and media_thumb:
        return media_thumb
    if isinstance(media_thumb, dict):
        url = media_thumb.get("url", "") or media_thumb.get("href", "")
        if url:
            return url

    # media:content with image type
    media_content = data.get("media:content")
    if isinstance(media_content, dict):
        medium = media_content.get("medium", "")
        mtype = media_content.get("type", "")
        if medium == "image" or (isinstance(mtype, str) and mtype.startswith("image/")):
            url = media_content.get("url", "")
            if url:
                return url
    if isinstance(media_content, list):
        for mc in media_content:
            if isinstance(mc, dict):
                medium = mc.get("medium", "")
                mtype = mc.get("type", "")
                if medium == "image" or (isinstance(mtype, str) and mtype.startswith("image/")):
                    url = mc.get("url", "")
                    if url:
                        return url

    # Image enclosure
    enclosures = data.get("enclosures") or data.get("enclosure") or []
    if isinstance(enclosures, dict):
        enclosures = [enclosures]
    for enc in enclosures:
        if isinstance(enc, dict):
            etype = enc.get("type", "")
            if isinstance(etype, str) and etype.startswith("image/"):
                url = enc.get("url", "") or enc.get("href", "")
                if url:
                    return url

    # Extract from content HTML
    if content:
        img_url = extract_thumbnail(content)
        if img_url:
            return img_url

    return ""


def _normalize_enclosures(data: dict) -> list[dict[str, Any]]:
    """Normalize enclosure data to list of {url, type, length} dicts."""
    result = []

    # feedparser style enclosures
    enclosures = data.get("enclosures") or data.get("enclosure") or []
    if isinstance(enclosures, dict):
        enclosures = [enclosures]

    for enc in enclosures:
        if isinstance(enc, dict):
            url = enc.get("url", "") or enc.get("href", "")
            if url:
                result.append({
                    "url": url,
                    "type": enc.get("type", "") or enc.get("mime_type", ""),
                    "length": _parse_int(
                        enc.get("length") or enc.get("size_in_bytes")
                    ),
                })

    return result


def _normalize_categories(raw: Any) -> list[str]:
    """Normalize categories to a deduplicated list of strings."""
    if not raw:
        return []

    cats: list[str] = []

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                val = item.strip()
                if val:
                    cats.append(val)
            elif isinstance(item, dict):
                # feedparser style: {"term": "Category"}
                term = item.get("term", "") or item.get("label", "") or item.get("name", "")
                if isinstance(term, str):
                    val = term.strip()
                    if val:
                        cats.append(val)

    # Deduplicate, preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for cat in cats:
        if cat not in seen:
            seen.add(cat)
            deduped.append(cat)

    return deduped


def _extract_extensions(data: dict, skip_keys: frozenset) -> dict[str, Any]:
    """Extract namespace-prefixed fields into extension buckets.

    Keys containing ``:`` are treated as namespace-prefixed and bucketed
    by their prefix. Keys without ``:`` that aren't in skip_keys are ignored
    (they're either first-class fields or adapter internals).
    """
    extensions: dict[str, dict[str, Any]] = {}

    for key, value in data.items():
        if key in skip_keys:
            continue

        if ":" in key:
            prefix, _, local = key.partition(":")
            if prefix and local:
                if prefix not in extensions:
                    extensions[prefix] = {}
                extensions[prefix][local] = value

    return extensions


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text at a word boundary with ellipsis."""
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    # Find last space for word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated.rstrip() + "…"


def _compute_latest_date(items: list[dict[str, Any]]) -> str | None:
    """Compute the latest pub_date from a list of item intermediates."""
    latest: str | None = None

    for item in items:
        raw = item.get("pub_date") or item.get("published") or item.get("date")
        if raw:
            normalized = normalize_date(raw)
            if normalized and (latest is None or normalized > latest):
                latest = normalized

    return latest
