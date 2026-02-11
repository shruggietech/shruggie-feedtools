"""Tests for namespace prefix normalization.

Covers: Dublin Core (HTTP/HTTPS/trailing-slash/uppercase), iTunes, Media RSS,
unknown URI fallback, YouTube, and exhaustive map check.
"""

from __future__ import annotations

import pytest

from shruggie_feedtools.core.namespaces import NAMESPACE_MAP, normalize_prefix


class TestDublinCore:
    """Test Dublin Core namespace resolution with URI variants."""

    def test_dc_http(self):
        """Standard HTTP DC URI resolves to 'dc'."""
        result = normalize_prefix("http://purl.org/dc/elements/1.1/", "x")
        assert result == "dc"

    def test_dc_https(self):
        """HTTPS variant of DC URI resolves to 'dc'."""
        result = normalize_prefix("https://purl.org/dc/elements/1.1/", "x")
        assert result == "dc"

    def test_dc_trailing_slash(self):
        """DC URI without trailing slash resolves to 'dc'."""
        result = normalize_prefix("http://purl.org/dc/elements/1.1", "x")
        assert result == "dc"

    def test_dc_uppercase_scheme(self):
        """DC URI with uppercase scheme resolves to 'dc'."""
        result = normalize_prefix("HTTP://purl.org/dc/elements/1.1/", "x")
        assert result == "dc"


class TestKnownNamespaces:
    """Test other known namespace URIs."""

    def test_itunes_standard(self):
        """iTunes namespace URI with matching prefix resolves to 'itunes'."""
        result = normalize_prefix(
            "http://www.itunes.com/dtds/podcast-1.0.dtd", "itunes"
        )
        assert result == "itunes"

    def test_itunes_custom_prefix(self):
        """iTunes namespace URI with custom prefix still resolves to 'itunes'."""
        result = normalize_prefix(
            "http://www.itunes.com/dtds/podcast-1.0.dtd", "podcast"
        )
        assert result == "itunes"

    def test_media_rss(self):
        """Media RSS namespace URI resolves to 'media'."""
        result = normalize_prefix("http://search.yahoo.com/mrss/", "media")
        assert result == "media"

    def test_youtube_namespace(self):
        """YouTube namespace URI resolves to 'yt'."""
        result = normalize_prefix(
            "http://www.youtube.com/xml/schemas/2015", "yt"
        )
        assert result == "yt"


class TestUnknownURI:
    """Test fallback behavior for unrecognized URIs."""

    def test_unknown_uri_uses_declared(self):
        """Unknown namespace URI falls back to the declared prefix."""
        result = normalize_prefix("http://example.com/custom/ns", "myns")
        assert result == "myns"


class TestExhaustiveMap:
    """Test that all entries in NAMESPACE_MAP resolve correctly."""

    def test_all_known_uris_resolve(self):
        """Every URI in NAMESPACE_MAP resolves to its canonical prefix."""
        for uri, expected_prefix in NAMESPACE_MAP.items():
            result = normalize_prefix(uri, "should_not_be_used")
            assert result == expected_prefix, (
                f"URI {uri!r} expected prefix {expected_prefix!r}, got {result!r}"
            )
