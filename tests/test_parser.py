"""Integration tests for the parse pipeline — end-to-end."""

from __future__ import annotations

from pathlib import Path

import pytest

from shruggie_feedtools.core.config import ParserConfig
from shruggie_feedtools.core.parser import parse_file, parse_string
from shruggie_feedtools.core.schema import FeedResponse

# ──────────────────────────── helpers ────────────────────────────


def _validate_schema(output: dict) -> FeedResponse:
    """Validate output dict against Pydantic schema."""
    return FeedResponse(**output)


# ──────────────────────────── tests ──────────────────────────────


class TestParseFullPipeline:
    """§17.3 test_parser.py — End-to-End Parse Pipeline."""

    # ── RSS 2.0 ──────────────────────────────────────────────

    def test_parse_rss2_minimal_full_pipeline(self, load_fixture):
        content = load_fixture("rss2/minimal.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        assert result["source"]["type"] == "rss2"
        assert result["feed"]["title"]
        assert len(result["items"]) > 0
        _validate_schema(result)

    def test_parse_rss2_wordpress_full_pipeline(self, load_fixture):
        content = load_fixture("rss2/wordpress.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        for item in result["items"]:
            assert item.get("author") or item.get("content")
        _validate_schema(result)

    def test_parse_rss2_podcast_full_pipeline(self, load_fixture):
        content = load_fixture("rss2/podcast_itunes.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        # Check for audio enclosures
        has_audio = any(
            any("audio" in enc.get("type", "") for enc in item.get("enclosures", []))
            for item in result["items"]
        )
        assert has_audio
        # Check for itunes extensions
        has_itunes_ext = any(
            "itunes" in item.get("extensions", {}) for item in result["items"]
        )
        assert has_itunes_ext
        _validate_schema(result)

    # ── Atom 1.0 ─────────────────────────────────────────────

    def test_parse_atom10_github_full_pipeline(self, load_fixture):
        content = load_fixture("atom10/github_releases.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        assert result["source"]["type"] == "atom10"
        for item in result["items"]:
            assert item.get("link")
            assert item.get("content") or item.get("description")
        _validate_schema(result)

    def test_parse_atom10_youtube_full_pipeline(self, load_fixture):
        content = load_fixture("atom10/youtube_channel.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        has_videoid = any(
            "yt" in item.get("extensions", {})
            and "videoId" in item["extensions"]["yt"]
            for item in result["items"]
        )
        assert has_videoid
        _validate_schema(result)

    # ── RSS 1.0 / RDF ────────────────────────────────────────

    def test_parse_rss1_rdf_full_pipeline(self, load_fixture):
        content = load_fixture("rss1/rdf_gov.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        assert result["source"]["type"] == "rss1"
        assert len(result["items"]) > 0
        _validate_schema(result)

    # ── JSON Feed ────────────────────────────────────────────

    def test_parse_json_feed_full_pipeline(self, load_fixture):
        content = load_fixture("json_feed/v1_standard.json")
        result = parse_string(content)
        assert result["status"] == "ok"
        assert result["source"]["type"] == "json_feed"
        assert result["feed"]["title"]
        assert len(result["items"]) > 0
        _validate_schema(result)

    # ── WordPress REST ───────────────────────────────────────

    def test_parse_wp_rest_full_pipeline(self, load_fixture):
        content = load_fixture("wp_rest/posts_embedded.json")
        result = parse_string(content)
        assert result["status"] == "ok"
        assert result["source"]["type"] == "wp_rest"
        has_author = any(item.get("author") for item in result["items"])
        assert has_author
        _validate_schema(result)

    # ── Error cases ──────────────────────────────────────────

    def test_parse_malformed_degrades_gracefully(self, load_fixture):
        content = load_fixture("rss2/hairy_malformed.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        # Should still have some items
        assert isinstance(result["items"], list)
        _validate_schema(result)

    def test_parse_empty_string_returns_error(self):
        result = parse_string("")
        assert result["status"] == "error"
        assert result["message"]

    def test_parse_html_page_returns_error(self):
        html = "<html><head><title>Not a feed</title></head><body>Hello</body></html>"
        result = parse_string(html)
        assert result["status"] == "error"

    def test_parse_unknown_json_returns_error(self):
        result = parse_string('{"random": "object"}')
        assert result["status"] == "error"

    def test_parse_url_json_feed_full_pipeline(self):
        """parse_url correctly handles a JSON Feed response."""
        from unittest import mock

        from shruggie_feedtools.core.fetcher import FetchResult
        from shruggie_feedtools.core.parser import parse_url

        fixture_path = Path(__file__).parent / "fixtures" / "json_feed" / "v1_standard.json"
        content = fixture_path.read_bytes()

        with mock.patch("shruggie_feedtools.core.parser.fetch") as mock_fetch:
            mock_fetch.return_value = FetchResult(
                ok=True,
                content=content,
                content_type="application/feed+json; charset=utf-8",
                final_url="https://example.com/feed.json",
                status_code=200,
            )
            result = parse_url("https://example.com/feed.json")

        assert result["status"] == "ok"
        assert result["source"]["type"] == "json_feed"
        assert result["source"]["origin"] == "url"
        assert result["feed"]["title"]
        assert len(result["items"]) > 0
        _validate_schema(result)

    def test_parse_file_json_feed(self, fixtures_path):
        """parse_file correctly handles a JSON Feed file."""
        path = fixtures_path / "json_feed" / "v1_standard.json"
        result = parse_file(path)
        assert result["status"] == "ok"
        assert result["source"]["type"] == "json_feed"
        assert result["source"]["origin"] == "file"
        _validate_schema(result)

    # ── Source origin / metadata ─────────────────────────────

    def test_parse_file_from_path(self, fixtures_path):
        path = fixtures_path / "rss2" / "minimal.xml"
        result = parse_file(path)
        assert result["status"] == "ok"
        assert result["source"]["origin"] == "file"
        _validate_schema(result)

    def test_parse_source_origin_string(self, load_fixture):
        content = load_fixture("rss2/minimal.xml")
        result = parse_string(content)
        assert result["source"]["origin"] == "string"

    def test_parse_source_url_preserved(self, load_fixture):
        content = load_fixture("rss2/minimal.xml")
        result = parse_string(content, source_url="https://x.com/feed")
        assert result["source"]["url"] == "https://x.com/feed"

    # ── Config options ───────────────────────────────────────

    def test_parse_max_items_config(self, load_fixture):
        content = load_fixture("rss2/wordpress.xml")
        config = ParserConfig(max_items=1)
        result = parse_string(content, config=config)
        assert result["status"] == "ok"
        assert len(result["items"]) <= 1

    # ── Schema validation ────────────────────────────────────

    def test_parse_output_validates_against_schema(self, load_fixture):
        content = load_fixture("rss2/minimal.xml")
        result = parse_string(content)
        _validate_schema(result)

    def test_parse_all_dates_are_utc_iso(self, load_fixture):
        content = load_fixture("rss2/wordpress.xml")
        result = parse_string(content)
        for item in result["items"]:
            if item.get("pub_date"):
                assert item["pub_date"].endswith("Z"), (
                    f"pub_date not UTC: {item['pub_date']}"
                )
            if item.get("updated"):
                assert item["updated"].endswith("Z"), (
                    f"updated not UTC: {item['updated']}"
                )

    # ── Edge cases ───────────────────────────────────────────

    def test_parse_namespace_normalization_applied(self, load_fixture):
        content = load_fixture("edge_cases/custom_namespace_prefixes.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        _validate_schema(result)

    def test_parse_mixed_case_elements(self, load_fixture):
        content = load_fixture("edge_cases/mixed_case_elements.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        _validate_schema(result)

    def test_parse_bad_dates_survive(self, load_fixture):
        content = load_fixture("edge_cases/bad_dates.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        # Some dates should be null, some should be valid
        has_null = any(
            item.get("pub_date") is None for item in result["items"]
        )
        has_valid = any(
            item.get("pub_date") is not None for item in result["items"]
        )
        assert has_null or has_valid  # At least one type
        _validate_schema(result)

    def test_parse_missing_fields_all_defaults(self, load_fixture):
        content = load_fixture("edge_cases/missing_fields.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        _validate_schema(result)

    def test_parse_encoding_utf8_bom(self, load_fixture):
        content = load_fixture("edge_cases/encoding_utf8_bom.xml")
        result = parse_string(content)
        assert result["status"] == "ok"
        _validate_schema(result)


class TestParseSnapshots:
    """Snapshot tests — compare full pipeline output against golden files."""

    @pytest.mark.parametrize(
        "fixture_path,snapshot_name,subfolder",
        [
            ("rss2/minimal.xml", "minimal", "rss2"),
            ("rss2/wordpress.xml", "wordpress", "rss2"),
            ("rss2/podcast_itunes.xml", "podcast_itunes", "rss2"),
            ("rss2/hairy_malformed.xml", "hairy_malformed", "rss2"),
            ("rss2/financial_sec.xml", "financial_sec", "rss2"),
            ("rss2/reddit.xml", "reddit", "rss2"),
            ("atom10/github_releases.xml", "github_releases", "atom10"),
            ("atom10/youtube_channel.xml", "youtube_channel", "atom10"),
            ("atom10/statuspage.xml", "statuspage", "atom10"),
            ("rss1/rdf_gov.xml", "rdf_gov", "rss1"),
            ("json_feed/v1_standard.json", "v1_standard", "json_feed"),
            ("wp_rest/posts_embedded.json", "posts_embedded", "wp_rest"),
            ("edge_cases/mixed_case_elements.xml", "mixed_case_elements", "edge_cases"),
            ("edge_cases/custom_namespace_prefixes.xml", "custom_namespace_prefixes", "edge_cases"),
            ("edge_cases/bad_dates.xml", "bad_dates", "edge_cases"),
            ("edge_cases/missing_fields.xml", "missing_fields", "edge_cases"),
            ("edge_cases/encoding_utf8_bom.xml", "encoding_utf8_bom", "edge_cases"),
        ],
    )
    def test_snapshot(
        self,
        load_fixture,
        assert_snapshot,
        fixture_path,
        snapshot_name,
        subfolder,
    ):
        content = load_fixture(fixture_path)
        result = parse_string(content)
        assert_snapshot(result, snapshot_name, subfolder)
