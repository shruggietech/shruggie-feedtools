"""Tests for feed type auto-detection."""

from __future__ import annotations

from shruggie_feedtools.core.detector import detect_feed_type


class TestDetectFeedType:
    """§17.3 test_detector.py — Format Detection."""

    def test_detect_rss2_standard(self, load_fixture):
        content = load_fixture("rss2/minimal.xml")
        assert detect_feed_type(content) == "rss2"

    def test_detect_atom10_standard(self, load_fixture):
        content = load_fixture("atom10/github_releases.xml")
        assert detect_feed_type(content) == "atom10"

    def test_detect_rss1_rdf(self, load_fixture):
        content = load_fixture("rss1/rdf_gov.xml")
        assert detect_feed_type(content) == "rss1"

    def test_detect_json_feed(self, load_fixture):
        content = load_fixture("json_feed/v1_standard.json")
        assert detect_feed_type(content) == "json_feed"

    def test_detect_wp_rest(self, load_fixture):
        content = load_fixture("wp_rest/posts_embedded.json")
        assert detect_feed_type(content) == "wp_rest"

    def test_detect_xml_with_bom(self, load_fixture):
        content = load_fixture("edge_cases/encoding_utf8_bom.xml")
        result = detect_feed_type(content)
        assert result is not None
        # BOM should not prevent detection — should detect as some RSS type
        assert result in ("rss2", "rss1", "atom10", "atom03", "rss091")

    def test_detect_empty_bytes(self):
        assert detect_feed_type(b"") is None

    def test_detect_html_page(self):
        html = b"<html><head><title>Not a feed</title></head><body>Hello</body></html>"
        assert detect_feed_type(html) is None

    def test_detect_plain_text(self):
        assert detect_feed_type(b"Hello world") is None

    def test_detect_json_non_feed(self):
        assert detect_feed_type(b'{"name": "not a feed"}') is None
