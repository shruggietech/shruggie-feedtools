"""WordPress REST API adapter.

Parses WordPress REST API ``/wp-json/wp/v2/posts?_embed`` responses into
intermediate dicts for normalization. Handles ``_embedded`` data for author,
featured media, and taxonomy terms.
"""

from __future__ import annotations

import html as html_module
import json
import logging
from typing import Any
from urllib.parse import urlparse

from shruggie_feedtools.core.config import ParserConfig

logger = logging.getLogger("shruggie_feedtools")


def parse_wp_rest(
    content: bytes | str,
    base_url: str = "",
    config: ParserConfig | None = None,
) -> dict[str, Any]:
    """Parse WordPress REST API JSON response.

    Args:
        content: Raw JSON response (array of post objects).
        base_url: Base URL of the WordPress site. If provided, used to
            derive ``feed.link``. Otherwise inferred from post links.
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

    # Support both array (multiple posts) and single object
    if isinstance(data, dict):
        posts = [data]
    elif isinstance(data, list):
        posts = data
    else:
        posts = []

    logger.debug("wp_rest_adapter: %d posts, base_url=%s", len(posts), base_url)

    if config.max_items is not None:
        posts = posts[: config.max_items]

    # Derive base URL from posts if not provided
    site_url = _extract_base_url(base_url, posts)

    feed: dict[str, Any] = {
        "title": "",
        "link": site_url,
        "description": "",
    }

    items = [_map_post(post) for post in posts if isinstance(post, dict)]

    return {
        "source_type": "wp_rest",
        "feed": feed,
        "items": items,
    }


def _extract_base_url(base_url: str, posts: list) -> str:
    """Extract site base URL from the base_url parameter or post data."""
    if base_url:
        # Strip /wp-json/... path if present
        parsed = urlparse(base_url)
        path = parsed.path
        wp_json_idx = path.find("/wp-json")
        if wp_json_idx >= 0:
            path = path[:wp_json_idx]
        return f"{parsed.scheme}://{parsed.netloc}{path}".rstrip("/")

    # Try to infer from post links
    if posts:
        first = posts[0]
        if isinstance(first, dict):
            links = first.get("_links", {})
            self_links = links.get("self", [])
            if self_links and isinstance(self_links, list):
                href = self_links[0].get("href", "")
                if "/wp-json/" in href:
                    idx = href.index("/wp-json/")
                    return href[:idx]

            # Fallback: use post link domain
            post_link = first.get("link", "")
            if post_link:
                parsed = urlparse(post_link)
                return f"{parsed.scheme}://{parsed.netloc}"

    return ""


def _map_post(post: dict) -> dict[str, Any]:
    """Map a WordPress REST post object to intermediate dict."""
    data: dict[str, Any] = {}

    # Title — decode HTML entities
    title_obj = post.get("title", {})
    raw_title = title_obj.get("rendered", "") if isinstance(title_obj, dict) else ""
    data["title"] = html_module.unescape(raw_title)

    # Link
    data["link"] = post.get("link", "")

    # GUID
    guid_obj = post.get("guid", {})
    data["guid"] = guid_obj.get("rendered", "") if isinstance(guid_obj, dict) else ""

    # Dates: date_gmt + "Z" suffix for UTC
    date_gmt = post.get("date_gmt", "")
    if date_gmt and not date_gmt.endswith("Z"):
        date_gmt = date_gmt + "Z"
    data["pub_date"] = date_gmt

    modified_gmt = post.get("modified_gmt", "")
    if modified_gmt and not modified_gmt.endswith("Z"):
        modified_gmt = modified_gmt + "Z"
    data["updated"] = modified_gmt

    # Content
    content_obj = post.get("content", {})
    data["content"] = content_obj.get("rendered", "") if isinstance(content_obj, dict) else ""

    # Excerpt → description
    excerpt_obj = post.get("excerpt", {})
    data["description"] = (
        excerpt_obj.get("rendered", "") if isinstance(excerpt_obj, dict) else ""
    )

    # Embedded data
    embedded = post.get("_embedded", {})

    # Author from _embedded
    authors = embedded.get("author", [])
    if authors and isinstance(authors, list):
        first_author = authors[0]
        if isinstance(first_author, dict):
            data["author"] = first_author.get("name", "")

    # Featured media (thumbnail) from _embedded
    featured = embedded.get("wp:featuredmedia", [])
    if featured and isinstance(featured, list):
        first_media = featured[0]
        if isinstance(first_media, dict):
            data["thumbnail"] = first_media.get("source_url", "")

    # Categories from _embedded wp:term
    wp_terms = embedded.get("wp:term", [])
    categories: list[str] = []
    if isinstance(wp_terms, list):
        for term_group in wp_terms:
            if isinstance(term_group, list):
                for term in term_group:
                    if isinstance(term, dict):
                        name = term.get("name", "")
                        if name:
                            categories.append(name)
    data["categories"] = categories

    return data
