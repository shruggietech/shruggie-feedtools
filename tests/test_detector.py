"""Tests for feed type auto-detection."""

from __future__ import annotations

from shruggie_feedtools.core.detector import derive_wp_rest_posts_url, detect_feed_type


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

    # -- Hardened JSON detection (bare version, missing _links) ---------------

    def test_detect_json_feed_bare_version(self):
        """JSON Feed with bare version string (non-compliant generators)."""
        content = b'{"version": "1.1", "title": "My Feed", "items": []}'
        assert detect_feed_type(content) == "json_feed"

    def test_detect_json_feed_bare_version_10(self):
        """JSON Feed with bare version '1.0'."""
        content = b'{"version": "1.0", "title": "Old Feed", "items": []}'
        assert detect_feed_type(content) == "json_feed"

    def test_detect_json_feed_bare_version_no_items(self):
        """Bare version without items key should NOT match."""
        content = b'{"version": "1.1", "title": "Not enough"}'
        assert detect_feed_type(content) is None

    def test_detect_wp_rest_without_links(self):
        """WP REST array without _links (CDN/cache stripped)."""
        import json
        data = [
            {
                "title": {"rendered": "Hello World"},
                "slug": "hello-world",
                "date_gmt": "2026-02-10T12:00:00",
                "type": "post",
                "status": "publish",
                "guid": {"rendered": "https://example.com/?p=1"},
            }
        ]
        assert detect_feed_type(json.dumps(data).encode()) == "wp_rest"

    def test_detect_wp_rest_single_without_links(self):
        """Single WP REST object without _links."""
        import json
        data = {
            "title": {"rendered": "Hello World"},
            "slug": "hello-world",
            "date_gmt": "2026-02-10T12:00:00",
            "type": "post",
            "guid": {"rendered": "https://example.com/?p=1"},
        }
        assert detect_feed_type(json.dumps(data).encode()) == "wp_rest"

    def test_detect_wp_rest_without_links_insufficient_markers(self):
        """title.rendered alone without enough markers should NOT match."""
        import json
        data = [{"title": {"rendered": "Hello World"}, "foo": "bar"}]
        assert detect_feed_type(json.dumps(data).encode()) is None

    # -- Content-type fallback detection --------------------------------------

    def test_detect_json_feed_with_content_type_hint(self, load_fixture):
        """JSON Feed detected via content-type when byte-sniffing succeeds directly."""
        content = load_fixture("json_feed/v1_standard.json")
        assert detect_feed_type(content, content_type="application/feed+json") == "json_feed"

    def test_detect_json_feed_with_content_type_fallback(self):
        """Content-type hint helps detect JSON when first byte is unexpected."""
        # Simulate BOM + JSON where BOM removal reveals JSON
        content = b'\xef\xbb\xbf{"version": "https://jsonfeed.org/version/1.1", "title": "T", "items": []}'
        assert detect_feed_type(content) == "json_feed"

    def test_detect_utf16_bom_json_feed(self):
        """JSON Feed encoded as UTF-16 LE with BOM is detected."""
        json_str = '{"version": "https://jsonfeed.org/version/1.1", "title": "T", "items": []}'
        content = b'\xff\xfe' + json_str.encode("utf-16-le")
        assert detect_feed_type(content) == "json_feed"

    def test_detect_content_type_json_non_feed_still_none(self):
        """Content-type says JSON but content is not a feed → still None."""
        content = b'{"random": "object"}'
        assert detect_feed_type(content, content_type="application/json") is None

    def test_detect_xml_with_content_type_hint(self, load_fixture):
        """XML feed detected with content-type hint."""
        content = load_fixture("rss2/minimal.xml")
        assert detect_feed_type(content, content_type="application/rss+xml") == "rss2"

    def test_detect_content_type_none_still_works(self, load_fixture):
        """Passing content_type=None doesn't break existing detection."""
        content = load_fixture("json_feed/v1_standard.json")
        assert detect_feed_type(content, content_type=None) == "json_feed"

    # -- WP REST API root / namespace index detection -------------------------

    def test_detect_wp_rest_namespace_index(self):
        """WP REST namespace index (/wp-json/wp/v2) with namespace + routes."""
        import json
        data = {
            "namespace": "wp/v2",
            "routes": {
                "/wp/v2": {"namespace": "wp/v2", "methods": ["GET"]},
                "/wp/v2/posts": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
            },
            "_links": {
                "self": [{"href": "https://example.com/wp-json/wp/v2"}],
            },
        }
        assert detect_feed_type(json.dumps(data).encode()) == "wp_rest_index"

    def test_detect_wp_rest_site_root(self):
        """WP REST site root (/wp-json/) with namespaces array."""
        import json
        data = {
            "name": "My Site",
            "description": "A WordPress site",
            "url": "https://example.com",
            "namespaces": ["oembed/1.0", "wp/v2", "wp-site-health/v1"],
        }
        assert detect_feed_type(json.dumps(data).encode()) == "wp_rest_index"

    def test_detect_wp_rest_site_root_no_wp_namespace(self):
        """Site root with namespaces but no wp/* entries should NOT match."""
        import json
        data = {
            "name": "Some API",
            "url": "https://example.com",
            "namespaces": ["custom/v1", "other/v2"],
        }
        assert detect_feed_type(json.dumps(data).encode()) is None


class TestDeriveWpRestPostsUrl:
    """Tests for derive_wp_rest_posts_url URL derivation."""

    def test_namespace_index_url(self):
        url = "https://example.com/wp-json/wp/v2"
        assert derive_wp_rest_posts_url(url) == "https://example.com/wp-json/wp/v2/posts?_embed"

    def test_namespace_index_url_trailing_slash(self):
        url = "https://example.com/wp-json/wp/v2/"
        assert derive_wp_rest_posts_url(url) == "https://example.com/wp-json/wp/v2/posts?_embed"

    def test_site_root_url(self):
        url = "https://example.com/wp-json/"
        assert derive_wp_rest_posts_url(url) == "https://example.com/wp-json/wp/v2/posts?_embed"

    def test_site_root_url_no_trailing_slash(self):
        url = "https://example.com/wp-json"
        assert derive_wp_rest_posts_url(url) == "https://example.com/wp-json/wp/v2/posts?_embed"

    def test_subdir_wp_install(self):
        url = "https://example.com/blog/wp-json/wp/v2"
        assert derive_wp_rest_posts_url(url) == "https://example.com/blog/wp-json/wp/v2/posts?_embed"

    def test_non_wp_url_returns_none(self):
        url = "https://example.com/api/v1"
        assert derive_wp_rest_posts_url(url) is None
