"""Feed format adapters.

Public API: ``parse_rss``, ``parse_atom``, ``parse_rdf``.
"""

from shruggie_feedtools.adapters.feedparser_adapter import parse_atom, parse_rdf, parse_rss

__all__ = [
    "parse_atom",
    "parse_rdf",
    "parse_rss",
]
