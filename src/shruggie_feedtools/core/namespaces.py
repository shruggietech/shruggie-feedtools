"""Namespace URI → canonical prefix normalization.

Feed XML documents declare namespace prefixes that vary per publisher.
This module maps namespace URIs to canonical prefixes so that extension
data is always bucketed under consistent keys regardless of how the
source feed declared them.
"""

from __future__ import annotations

# Maps namespace URIs to their canonical prefix names.
# Both HTTP and HTTPS variants are included where applicable.
NAMESPACE_MAP: dict[str, str] = {
    # Dublin Core
    "http://purl.org/dc/elements/1.1/": "dc",
    "https://purl.org/dc/elements/1.1/": "dc",
    # Dublin Core Terms
    "http://purl.org/dc/terms/": "dcterms",
    "https://purl.org/dc/terms/": "dcterms",
    # Content Module
    "http://purl.org/rss/1.0/modules/content/": "content",
    # Media RSS
    "http://search.yahoo.com/mrss/": "media",
    "https://search.yahoo.com/mrss/": "media",
    # iTunes / Podcast
    "http://www.itunes.com/dtds/podcast-1.0.dtd": "itunes",
    "https://www.itunes.com/dtds/podcast-1.0.dtd": "itunes",
    # Atom
    "http://www.w3.org/2005/Atom": "atom",
    "https://www.w3.org/2005/Atom": "atom",
    # Syndication
    "http://purl.org/rss/1.0/modules/syndication/": "sy",
    # Slash
    "http://purl.org/rss/1.0/modules/slash/": "slash",
    # YouTube
    "http://www.youtube.com/xml/schemas/2015": "yt",
    "https://www.youtube.com/xml/schemas/2015": "yt",
    # GeoRSS
    "http://www.georss.org/georss": "georss",
    "https://www.georss.org/georss": "georss",
    # Podcast Index
    "https://podcastindex.org/namespace/1.0": "podcast",
    "http://podcastindex.org/namespace/1.0": "podcast",
}


def normalize_prefix(uri: str, declared_prefix: str) -> str:
    """Map a namespace URI to its canonical prefix.

    Performs URI tolerance: strips trailing slashes, lowercases scheme and host
    for comparison. Falls back to ``declared_prefix`` if the URI is not recognized.

    Args:
        uri: The namespace URI from the feed.
        declared_prefix: The prefix the feed declared for this namespace.

    Returns:
        The canonical prefix string (e.g. ``"dc"``, ``"itunes"``) or the
        declared prefix if the URI is unknown.
    """
    normalized = uri.rstrip("/").lower()

    for known_uri, canonical in NAMESPACE_MAP.items():
        if normalized == known_uri.rstrip("/").lower():
            return canonical

    return declared_prefix
