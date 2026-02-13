"""Tests for format-specific feed adapters."""

from __future__ import annotations

from shruggie_feedtools.adapters.feedparser_adapter import parse_feed

# ──────────────────────────────────────────────
# feedparser adapter — RSS 2.0
# ──────────────────────────────────────────────


class TestRSS2Adapter:
    """feedparser adapter tests for RSS 2.0 fixtures."""

    def test_rss2_minimal_extracts_title(self, load_fixture):
        content = load_fixture("rss2/minimal.xml")
        result = parse_feed(content)
        assert result["feed"]["title"]

    def test_rss2_minimal_extracts_items(self, load_fixture):
        content = load_fixture("rss2/minimal.xml")
        result = parse_feed(content)
        assert isinstance(result["items"], list)
        assert len(result["items"]) > 0

    def test_rss2_wordpress_dc_creator(self, load_fixture):
        content = load_fixture("rss2/wordpress.xml")
        result = parse_feed(content)
        # At least one item should have dc:creator
        has_creator = any(
            item.get("dc:creator") or item.get("author")
            for item in result["items"]
        )
        assert has_creator

    def test_rss2_wordpress_content_encoded(self, load_fixture):
        content = load_fixture("rss2/wordpress.xml")
        result = parse_feed(content)
        # Items should have content from content:encoded
        has_content = any(
            item.get("content") for item in result["items"]
        )
        assert has_content

    def test_rss2_wordpress_categories(self, load_fixture):
        content = load_fixture("rss2/wordpress.xml")
        result = parse_feed(content)
        has_cats = any(
            len(item.get("categories", [])) > 0 for item in result["items"]
        )
        assert has_cats

    def test_rss2_podcast_itunes_fields(self, load_fixture):
        content = load_fixture("rss2/podcast_itunes.xml")
        result = parse_feed(content)
        items = result["items"]
        assert len(items) > 0
        first = items[0]
        # Should have itunes fields
        has_itunes = any(
            key.startswith("itunes:") for key in first
        )
        assert has_itunes

    def test_rss2_podcast_enclosure(self, load_fixture):
        content = load_fixture("rss2/podcast_itunes.xml")
        result = parse_feed(content)
        has_enclosure = any(
            len(item.get("enclosures", [])) > 0 for item in result["items"]
        )
        assert has_enclosure
        # Check enclosure structure
        for item in result["items"]:
            for enc in item.get("enclosures", []):
                assert "url" in enc

    def test_rss2_malformed_does_not_crash(self, load_fixture):
        content = load_fixture("rss2/hairy_malformed.xml")
        result = parse_feed(content)
        assert "source_type" in result
        assert "items" in result

    def test_rss2_malformed_bozo_flag(self, load_fixture):
        """Adapter should handle bozo flag gracefully."""
        content = load_fixture("rss2/hairy_malformed.xml")
        # Should not raise — adapter logs warning and continues
        result = parse_feed(content)
        assert result is not None

    def test_rss2_reddit_media_thumbnail(self, load_fixture):
        content = load_fixture("rss2/reddit.xml")
        result = parse_feed(content)
        has_media = any(
            item.get("media:thumbnail") for item in result["items"]
        )
        assert has_media

    def test_rss2_sec_minimal_descriptions(self, load_fixture):
        content = load_fixture("rss2/financial_sec.xml")
        result = parse_feed(content)
        # Should parse successfully even with missing/empty descriptions
        assert len(result["items"]) > 0


# ──────────────────────────────────────────────
# feedparser adapter — Atom 1.0
# ──────────────────────────────────────────────


class TestAtom10Adapter:
    """feedparser adapter tests for Atom 1.0 fixtures."""

    def test_atom10_github_link_alternate(self, load_fixture):
        content = load_fixture("atom10/github_releases.xml")
        result = parse_feed(content)
        for item in result["items"]:
            assert item.get("link"), "Item should have a link from rel=alternate"

    def test_atom10_github_updated_dates(self, load_fixture):
        content = load_fixture("atom10/github_releases.xml")
        result = parse_feed(content)
        has_updated = any(item.get("updated") for item in result["items"])
        assert has_updated

    def test_atom10_github_content_html(self, load_fixture):
        content = load_fixture("atom10/github_releases.xml")
        result = parse_feed(content)
        has_content = any(item.get("content") for item in result["items"])
        assert has_content

    def test_atom10_youtube_yt_videoid(self, load_fixture):
        content = load_fixture("atom10/youtube_channel.xml")
        result = parse_feed(content)
        has_videoid = any(
            item.get("yt:videoId") for item in result["items"]
        )
        assert has_videoid

    def test_atom10_youtube_media_group(self, load_fixture):
        content = load_fixture("atom10/youtube_channel.xml")
        result = parse_feed(content)
        has_media = any(
            item.get("media:thumbnail") for item in result["items"]
        )
        assert has_media

    def test_atom10_statuspage_multiple_updates(self, load_fixture):
        content = load_fixture("atom10/statuspage.xml")
        result = parse_feed(content)
        assert len(result["items"]) > 0
        # Entries should have updated values
        for item in result["items"]:
            assert item.get("updated") or item.get("published")


# ──────────────────────────────────────────────
# feedparser adapter — RSS 1.0 / RDF
# ──────────────────────────────────────────────


class TestRSS1Adapter:
    """feedparser adapter tests for RSS 1.0 (RDF) fixtures."""

    def test_rss1_rdf_parses_items(self, load_fixture):
        content = load_fixture("rss1/rdf_gov.xml")
        result = parse_feed(content)
        assert len(result["items"]) > 0

    def test_rss1_rdf_dc_namespace(self, load_fixture):
        content = load_fixture("rss1/rdf_gov.xml")
        result = parse_feed(content)
        # feedparser absorbs dc:creator into author, dc:date into updated, etc.
        # Verify at least one item has author (from dc:creator)
        has_author = any(item.get("author") for item in result["items"])
        assert has_author

    def test_rss1_source_type(self, load_fixture):
        content = load_fixture("rss1/rdf_gov.xml")
        result = parse_feed(content)
        assert result["source_type"] == "rss1"
