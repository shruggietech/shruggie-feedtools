"""feedparser-based adapter for XML feeds.

Wraps ``feedparser.parse()`` to handle RSS 2.0, RSS 1.0/RDF, RSS 0.9x,
Atom 1.0, and Atom 0.3. Extracts feed metadata and entries into intermediate
dicts that the normalizer maps to the output schema.
"""

from __future__ import annotations

import logging
from typing import Any

import feedparser

from shruggie_feedtools.core.config import ParserConfig
from shruggie_feedtools.core.namespaces import normalize_prefix

logger = logging.getLogger("shruggie_feedtools")

# feedparser version → canonical source type
_VERSION_MAP: dict[str, str] = {
    "rss20": "rss2",
    "rss10": "rss1",
    "rss091": "rss091",
    "rss092": "rss091",
    "rss093": "rss091",
    "atom10": "atom10",
    "atom03": "atom03",
}


def parse_feed(
    content: bytes | str,
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Parse XML feed content via feedparser.

    Args:
        content: Raw XML feed bytes or string.
        config: Parser configuration.

    Returns:
        Dict with ``source_type``, ``feed`` (intermediate dict),
        and ``items`` (list of intermediate dicts).
    """
    if config is None:
        config = ParserConfig()

    result = feedparser.parse(content)

    # Handle bozo flag (malformed XML)
    if result.get("bozo"):
        exc = result.get("bozo_exception")
        logger.warning("feedparser bozo flag set: %s", exc)

    # Determine source type
    version = result.get("version", "") or ""
    source_type = _VERSION_MAP.get(version, "rss2")
    logger.debug("feedparser_adapter: version=%s, source_type=%s, entries=%d",
                 version, source_type, len(result.entries or []))

    # Extract namespace declarations for prefix normalization
    namespaces = result.get("namespaces", {})
    # namespaces is {prefix: uri} — we need to build a reverse map
    prefix_map = {}
    if config.normalize_namespaces and namespaces:
        for declared_prefix, uri in namespaces.items():
            canonical = normalize_prefix(uri, declared_prefix)
            prefix_map[declared_prefix] = canonical

    # Map feed metadata
    feed_data = _map_feed(result.feed, prefix_map, config) if result.feed else {}

    # Map entries
    items = []
    entries = result.entries or []
    if config.max_items is not None:
        entries = entries[: config.max_items]

    for entry in entries:
        item = _map_entry(entry, prefix_map, config)
        items.append(item)

    return {
        "source_type": source_type,
        "feed": feed_data,
        "items": items,
    }


def _map_feed(
    feed: feedparser.FeedParserDict,
    prefix_map: dict[str, str],
    config: ParserConfig,
) -> dict[str, Any]:
    """Map feedparser feed object to intermediate dict."""
    data: dict[str, Any] = {}

    data["title"] = feed.get("title", "")
    data["link"] = _get_best_link(feed)
    data["description"] = feed.get("subtitle", "") or feed.get("description", "")
    data["language"] = feed.get("language", "")
    data["image"] = _get_feed_image(feed)
    data["updated"] = feed.get("updated", "") or feed.get("published", "")
    data["generator"] = feed.get("generator", "")

    # Author
    author = feed.get("author", "")
    author_detail = feed.get("author_detail")
    if not author and isinstance(author_detail, dict):
        author = author_detail.get("name", "")
    data["author"] = author

    # Categories (feedparser uses "tags")
    data["categories"] = feed.get("tags", [])

    # TTL (RSS 2.0)
    data["ttl"] = feed.get("ttl")

    # Namespace-prefixed fields
    _extract_namespaced_fields(feed, data, prefix_map, config)

    return data


def _map_entry(
    entry: feedparser.FeedParserDict,
    prefix_map: dict[str, str],
    config: ParserConfig,
) -> dict[str, Any]:
    """Map feedparser entry to intermediate dict."""
    data: dict[str, Any] = {}

    data["title"] = entry.get("title", "")
    data["link"] = _get_best_link(entry)

    # GUID
    data["guid"] = entry.get("id", "")
    guidislink = entry.get("guidislink")
    if guidislink is not None:
        data["guid_is_permalink"] = bool(guidislink)

    # Dates
    data["published"] = entry.get("published", "") or entry.get("created", "")
    data["updated"] = entry.get("updated", "")

    # Author
    author = entry.get("author", "")
    author_detail = entry.get("author_detail")
    if not author and isinstance(author_detail, dict):
        author = author_detail.get("name", "")
    data["author"] = author

    # Content — feedparser puts content in entry.content (list of dicts)
    content_list = entry.get("content")
    if content_list and isinstance(content_list, list):
        # Prefer the HTML version
        best_content = ""
        for c in content_list:
            if isinstance(c, dict):
                ctype = c.get("type", "")
                val = c.get("value", "")
                if "html" in ctype:
                    best_content = val
                    break
                if not best_content:
                    best_content = val
        data["content"] = best_content
    else:
        data["content"] = ""

    # Description/Summary
    data["summary"] = entry.get("summary", "") or entry.get("description", "")

    # Enclosures
    enclosures_raw = entry.get("enclosures", [])
    enclosures = []
    for enc in enclosures_raw:
        if isinstance(enc, dict):
            enclosures.append({
                "url": enc.get("href", "") or enc.get("url", ""),
                "type": enc.get("type", ""),
                "length": enc.get("length"),
            })
    data["enclosures"] = enclosures

    # Categories (feedparser uses "tags")
    data["categories"] = entry.get("tags", [])

    # Comments
    data["comments_url"] = entry.get("comments")

    # Media fields for thumbnail extraction
    _extract_media_fields(entry, data)

    # Namespace-prefixed fields
    _extract_namespaced_fields(entry, data, prefix_map, config)

    return data


def _get_best_link(obj: feedparser.FeedParserDict) -> str:
    """Get the best link from a feedparser object.

    Prefers ``rel=alternate`` links, falls back to the ``link`` attribute.
    """
    links = obj.get("links", [])
    if links:
        for link in links:
            if isinstance(link, dict) and link.get("rel") == "alternate":
                href = link.get("href", "")
                if href:
                    return href
        # Fallback to first link
        first = links[0]
        if isinstance(first, dict):
            return first.get("href", "")

    return obj.get("link", "")


def _get_feed_image(feed: feedparser.FeedParserDict) -> str:
    """Extract feed image URL."""
    # RSS image element
    image = feed.get("image")
    if isinstance(image, dict):
        return image.get("href", "") or image.get("url", "")

    # Atom logo
    logo = feed.get("logo", "")
    if logo:
        return logo

    # Atom icon
    icon = feed.get("icon", "")
    if icon:
        return icon

    return ""


def _extract_media_fields(entry: feedparser.FeedParserDict, data: dict) -> None:
    """Extract media RSS fields from a feedparser entry."""
    # media:thumbnail
    media_thumbnail = entry.get("media_thumbnail")
    if media_thumbnail and isinstance(media_thumbnail, list) and media_thumbnail:
        first = media_thumbnail[0]
        if isinstance(first, dict):
            data["media:thumbnail"] = first.get("url", "")

    # media:content
    media_content = entry.get("media_content")
    if media_content and isinstance(media_content, list):
        for mc in media_content:
            if isinstance(mc, dict):
                medium = mc.get("medium", "")
                mtype = mc.get("type", "")
                if medium == "image" or (isinstance(mtype, str) and mtype.startswith("image/")):
                    data.setdefault("media:content", mc)
                    break


def _extract_namespaced_fields(
    obj: feedparser.FeedParserDict,
    data: dict,
    prefix_map: dict[str, str],
    config: ParserConfig,
) -> None:
    """Extract namespace-prefixed fields into the intermediate dict.

    feedparser flattens namespace-prefixed fields by replacing the prefix
    separator with ``_``. For example, ``dc:creator`` becomes
    ``dc_creator`` or just ``author``. We reconstruct the prefixed keys.
    """
    if not config.include_extensions:
        return

    # feedparser exposes some namespaced fields directly
    # We look for common patterns

    # Dublin Core
    for dc_field in ("creator", "date", "subject", "rights", "publisher", "language"):
        key = f"dc_{dc_field}"
        val = obj.get(key)
        if val:
            prefix = prefix_map.get("dc", "dc") if config.normalize_namespaces else "dc"
            data[f"{prefix}:{dc_field}"] = val

    # Dublin Core Terms
    for dct_field in ("modified", "created", "issued"):
        key = f"dcterms_{dct_field}"
        val = obj.get(key)
        if val:
            prefix = prefix_map.get("dcterms", "dcterms")
            data[f"{prefix}:{dct_field}"] = val

    # Content module
    content_encoded = obj.get("content")
    if isinstance(content_encoded, list) and content_encoded:
        for c in content_encoded:
            if isinstance(c, dict) and c.get("base", ""):
                pass  # feedparser handles this via content field

    # Slash
    slash_comments = obj.get("slash_comments")
    if slash_comments:
        prefix = prefix_map.get("slash", "slash") if config.normalize_namespaces else "slash"
        data[f"{prefix}:comments"] = slash_comments

    # iTunes
    for itunes_field in (
        "duration", "explicit", "image", "author", "subtitle", "summary",
        "episode", "episodetype", "season", "block", "order",
    ):
        key = f"itunes_{itunes_field}"
        val = obj.get(key)
        if val is not None:
            prefix = prefix_map.get("itunes", "itunes") if config.normalize_namespaces else "itunes"
            # Normalize field names
            field_name = itunes_field
            if field_name == "episodetype":
                field_name = "episodeType"
            if isinstance(val, dict) and "href" in val:
                val = val["href"]
            data[f"{prefix}:{field_name}"] = val

    # YouTube
    for yt_field in ("videoid", "channelid"):
        key = f"yt_{yt_field}"
        val = obj.get(key)
        if val:
            prefix = prefix_map.get("yt", "yt") if config.normalize_namespaces else "yt"
            # Normalize field names
            field_name = "videoId" if yt_field == "videoid" else "channelId"
            data[f"{prefix}:{field_name}"] = val

    # Syndication module
    for sy_field in ("updateperiod", "updatefrequency", "updatebase"):
        key = f"sy_{sy_field}"
        val = obj.get(key)
        if val:
            prefix = prefix_map.get("sy", "sy") if config.normalize_namespaces else "sy"
            data[f"{prefix}:{sy_field}"] = val


# Convenience wrappers for format-specific parsing


def parse_rss(content: bytes | str, config: ParserConfig | None = None) -> dict[str, Any]:
    """Parse RSS 2.0 content."""
    return parse_feed(content, config)


def parse_atom(content: bytes | str, config: ParserConfig | None = None) -> dict[str, Any]:
    """Parse Atom 1.0 content."""
    return parse_feed(content, config)


def parse_rdf(content: bytes | str, config: ParserConfig | None = None) -> dict[str, Any]:
    """Parse RSS 1.0 (RDF) content."""
    return parse_feed(content, config)
