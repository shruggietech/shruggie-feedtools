"""Tests for the normalizer module — schema mapping and field normalization."""

from __future__ import annotations

from shruggie_feedtools.core.config import ParserConfig
from shruggie_feedtools.core.normalizer import normalize_feed, normalize_item


class TestNormalizeItem:
    """Item-level normalization tests per §17.3."""

    def test_title_passthrough(self):
        result = normalize_item({"title": "Hello"})
        assert result["title"] == "Hello"

    def test_title_missing_defaults_empty(self):
        result = normalize_item({})
        assert result["title"] == ""

    def test_description_from_summary(self):
        result = normalize_item({"summary": "A summary"})
        assert result["description"] == "A summary"

    def test_description_fallback_to_content_truncated(self):
        long_content = "A" * 500
        result = normalize_item({"content": long_content})
        assert result["description"]
        assert len(result["description"]) < len(long_content)
        assert result["description"].endswith("…")

    def test_content_from_content_encoded(self):
        result = normalize_item({"content:encoded": "<p>Encoded HTML</p>"})
        assert result["content"] == "<p>Encoded HTML</p>"

    def test_content_prefers_full_over_summary(self):
        result = normalize_item({
            "content": "<p>Full content here</p>",
            "summary": "Short summary",
        })
        assert result["content"] == "<p>Full content here</p>"
        assert result["description"] == "Short summary"

    def test_author_from_dc_creator(self):
        result = normalize_item({"dc:creator": "Jane Doe"})
        assert result["author"] == "Jane Doe"

    def test_author_from_atom_author_name(self):
        result = normalize_item({"author_detail": {"name": "John Smith"}})
        assert result["author"] == "John Smith"

    def test_guid_passthrough(self):
        result = normalize_item({"guid": "urn:uuid:1234"})
        assert result["guid"] == "urn:uuid:1234"

    def test_guid_missing_falls_back_to_link(self):
        result = normalize_item({"link": "https://example.com/article"})
        assert result["guid"] == "https://example.com/article"

    def test_guid_is_permalink_true(self):
        result = normalize_item({"guid_is_permalink": True})
        assert result["guid_is_permalink"] is True

    def test_guid_is_permalink_default_false(self):
        result = normalize_item({})
        assert result["guid_is_permalink"] is False

    def test_pub_date_normalized_to_utc(self):
        result = normalize_item({"pub_date": "Thu, 09 Feb 2026 12:00:00 GMT"})
        assert result["pub_date"] is not None
        assert result["pub_date"].endswith("Z")

    def test_pub_date_missing_is_null(self):
        result = normalize_item({})
        assert result["pub_date"] is None

    def test_updated_separate_from_pub_date(self):
        result = normalize_item({
            "published": "2026-02-09T12:00:00Z",
            "updated": "2026-02-10T12:00:00Z",
        })
        assert result["pub_date"] != result["updated"]

    def test_thumbnail_from_media_thumbnail(self):
        result = normalize_item({"media:thumbnail": "https://example.com/thumb.jpg"})
        assert result["thumbnail"] == "https://example.com/thumb.jpg"

    def test_thumbnail_from_media_content_image(self):
        result = normalize_item({
            "media:content": {"url": "https://example.com/img.jpg", "medium": "image"},
        })
        assert result["thumbnail"] == "https://example.com/img.jpg"

    def test_thumbnail_from_enclosure_image(self):
        result = normalize_item({
            "enclosures": [{"url": "https://example.com/photo.jpg", "type": "image/jpeg"}],
        })
        assert result["thumbnail"] == "https://example.com/photo.jpg"

    def test_thumbnail_extraction_disabled(self):
        config = ParserConfig(thumbnail_extraction=False)
        result = normalize_item(
            {"media:thumbnail": "https://example.com/thumb.jpg"},
            config=config,
        )
        assert result["thumbnail"] == ""

    def test_enclosures_mapped(self):
        result = normalize_item({
            "enclosures": [
                {"url": "https://example.com/ep.mp3", "type": "audio/mpeg", "length": "12345"},
            ],
        })
        assert len(result["enclosures"]) == 1
        assert result["enclosures"][0]["url"] == "https://example.com/ep.mp3"
        assert result["enclosures"][0]["type"] == "audio/mpeg"
        assert result["enclosures"][0]["length"] == 12345

    def test_enclosures_empty_when_none(self):
        result = normalize_item({})
        assert result["enclosures"] == []

    def test_categories_from_tags(self):
        result = normalize_item({"tags": ["Python", "Coding"]})
        assert result["categories"] == ["Python", "Coding"]

    def test_categories_deduplication(self):
        result = normalize_item({"tags": ["Python", "python", "Python"]})
        # Case-sensitive dedup — "Python" appears once, "python" appears once
        assert len(result["categories"]) < 3

    def test_extensions_bucket_namespaced(self):
        result = normalize_item({
            "itunes:duration": "01:23:45",
            "yt:videoId": "abc123",
        })
        assert "itunes" in result["extensions"]
        assert result["extensions"]["itunes"]["duration"] == "01:23:45"
        assert "yt" in result["extensions"]
        assert result["extensions"]["yt"]["videoId"] == "abc123"

    def test_extensions_uses_normalized_prefix(self):
        """Extension keys should use canonical prefix names."""
        normalize_item({"dc:creator": "Author Name"})
        # dc:creator is extracted as author, not as extension
        # But other dc fields should use canonical prefix
        result2 = normalize_item({"dc:rights": "Copyright 2026"})
        assert "dc" in result2["extensions"]

    def test_extensions_disabled(self):
        config = ParserConfig(include_extensions=False)
        result = normalize_item(
            {"itunes:duration": "01:23:45"},
            config=config,
        )
        assert result["extensions"] == {}


class TestNormalizeFeed:
    """Feed-level normalization tests per §17.3."""

    def test_feed_language_passthrough(self):
        result = normalize_feed({"language": "en-us"}, [])
        assert result["language"] == "en-us"

    def test_feed_generator_passthrough(self):
        result = normalize_feed({"generator": "WordPress 6.7"}, [])
        assert result["generator"] == "WordPress 6.7"

    def test_feed_ttl_integer(self):
        result = normalize_feed({"ttl": "60"}, [])
        assert result["ttl"] == 60

    def test_feed_ttl_missing_is_null(self):
        result = normalize_feed({}, [])
        assert result["ttl"] is None

    def test_feed_image_from_logo(self):
        result = normalize_feed({"logo": "https://example.com/logo.png"}, [])
        assert result["image"] == "https://example.com/logo.png"

    def test_feed_last_updated_computed(self):
        items = [
            {"pub_date": "2026-02-09T12:00:00Z"},
            {"pub_date": "2026-02-10T12:00:00Z"},
            {"pub_date": "2026-02-08T12:00:00Z"},
        ]
        result = normalize_feed({}, items)
        assert result["last_updated"] == "2026-02-10T12:00:00Z"
