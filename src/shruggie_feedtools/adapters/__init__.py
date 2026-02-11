"""Feed format adapters.

Public API: ``parse_rss``, ``parse_atom``, ``parse_rdf``, ``parse_json_feed``, ``parse_wp_rest``.
"""

from shruggie_feedtools.adapters.feedparser_adapter import parse_atom, parse_rdf, parse_rss
from shruggie_feedtools.adapters.json_feed_adapter import parse_json_feed
from shruggie_feedtools.adapters.wp_rest_adapter import parse_wp_rest

__all__ = [
    "parse_atom",
    "parse_json_feed",
    "parse_rdf",
    "parse_rss",
    "parse_wp_rest",
]
