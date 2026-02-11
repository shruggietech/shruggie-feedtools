"""Tests for Pydantic schema models — output schema contract enforcement.

Covers: roundtrip serialization, validation errors, default application,
enum validation, and field type enforcement.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from shruggie_feedtools.core.schema import (
    Enclosure,
    FeedItem,
    FeedMeta,
    FeedResponse,
    SourceInfo,
    SourceOrigin,
    SourceType,
    Status,
)


def _make_valid_response(**overrides) -> dict:
    """Build a minimal valid FeedResponse dict with optional overrides."""
    base = {
        "status": "ok",
        "schema_version": "1.0",
        "source": {"type": "rss2", "url": "https://example.com/feed", "origin": "url"},
        "feed": {"title": "Test Feed"},
        "items": [],
    }
    base.update(overrides)
    return base


def _make_full_response() -> dict:
    """Build a fully populated FeedResponse dict."""
    return {
        "status": "ok",
        "schema_version": "1.0",
        "source": {"type": "rss2", "url": "https://example.com/feed.xml", "origin": "url"},
        "feed": {
            "title": "Test Feed",
            "link": "https://example.com",
            "description": "A test feed",
            "language": "en-us",
            "author": "Test Author",
            "image": "https://example.com/logo.png",
            "last_updated": "2026-02-09T12:00:00Z",
            "generator": "TestGen 1.0",
            "categories": ["Tech", "News"],
            "ttl": 60,
            "extensions": {"dc": {"creator": "admin"}},
        },
        "items": [
            {
                "title": "Article One",
                "link": "https://example.com/article-1",
                "guid": "https://example.com/article-1",
                "guid_is_permalink": True,
                "pub_date": "2026-02-09T08:30:00Z",
                "updated": "2026-02-09T10:00:00Z",
                "author": "John Doe",
                "description": "Short summary",
                "content": "<p>Full HTML content</p>",
                "thumbnail": "https://example.com/thumb.jpg",
                "enclosures": [
                    {"url": "https://example.com/audio.mp3", "type": "audio/mpeg", "length": 12345}
                ],
                "categories": ["Tech", "Python"],
                "comments_url": "https://example.com/article-1#comments",
                "comments_count": 42,
                "extensions": {"itunes": {"duration": "01:23:45"}},
            }
        ],
    }


class TestValidResponseRoundtrip:
    """Test that valid response dicts roundtrip through Pydantic models."""

    def test_valid_response_roundtrips(self):
        """Fully populated response dict accepted; model_dump matches input structure."""
        data = _make_full_response()
        model = FeedResponse(**data)
        dumped = model.model_dump(mode="python")
        assert dumped["status"] == "ok"
        assert dumped["schema_version"] == "1.0"
        assert dumped["source"]["type"] == "rss2"
        assert dumped["feed"]["title"] == "Test Feed"
        assert len(dumped["items"]) == 1
        assert dumped["items"][0]["title"] == "Article One"

    def test_minimal_response_roundtrips(self):
        """Response with only required fields; all optionals at defaults."""
        data = _make_valid_response()
        model = FeedResponse(**data)
        dumped = model.model_dump(mode="python")
        assert dumped["status"] == "ok"
        assert dumped["items"] == []
        assert dumped["feed"]["title"] == "Test Feed"
        assert dumped["feed"]["categories"] == []
        assert dumped["feed"]["ttl"] is None
        assert dumped["feed"]["extensions"] == {}


class TestStatusEnum:
    """Test status field enum validation."""

    def test_status_enum_ok(self):
        """status: 'ok' is accepted."""
        data = _make_valid_response(status="ok")
        model = FeedResponse(**data)
        assert model.status == Status.OK

    def test_status_enum_error(self):
        """status: 'error' is accepted."""
        data = _make_valid_response(status="error")
        model = FeedResponse(**data)
        assert model.status == Status.ERROR

    def test_status_enum_invalid(self):
        """status: 'maybe' raises ValidationError."""
        data = _make_valid_response(status="maybe")
        with pytest.raises(ValidationError):
            FeedResponse(**data)


class TestSchemaVersion:
    """Test schema_version field."""

    def test_schema_version_required(self):
        """Missing schema_version raises ValidationError."""
        data = _make_valid_response()
        del data["schema_version"]
        with pytest.raises(ValidationError):
            FeedResponse(**data)


class TestSourceFields:
    """Test source type and origin enum validation."""

    @pytest.mark.parametrize(
        "source_type",
        ["rss2", "rss1", "atom10", "json_feed", "wp_rest", "constructed"],
    )
    def test_source_type_valid_values(self, source_type: str):
        """All valid source.type values are accepted."""
        data = _make_valid_response()
        data["source"]["type"] = source_type
        model = FeedResponse(**data)
        assert model.source.type.value == source_type

    @pytest.mark.parametrize("origin", ["url", "file", "string", "template"])
    def test_source_origin_valid_values(self, origin: str):
        """All valid source.origin values are accepted."""
        data = _make_valid_response()
        data["source"]["origin"] = origin
        model = FeedResponse(**data)
        assert model.source.origin.value == origin

    def test_source_url_nullable(self):
        """source.url: null is accepted (valid for file/string/template origins)."""
        data = _make_valid_response()
        data["source"]["url"] = None
        model = FeedResponse(**data)
        assert model.source.url is None


class TestFeedMetaValidation:
    """Test feed metadata field validation."""

    def test_feed_title_is_string(self):
        """feed.title: 123 (integer) raises ValidationError."""
        data = _make_valid_response()
        data["feed"]["title"] = 123
        with pytest.raises(ValidationError):
            FeedResponse(**data)

    def test_feed_categories_is_string_array(self):
        """feed.categories: ['a', 'b'] is accepted."""
        data = _make_valid_response()
        data["feed"]["categories"] = ["a", "b"]
        model = FeedResponse(**data)
        assert model.feed.categories == ["a", "b"]

    def test_feed_categories_rejects_non_strings(self):
        """feed.categories: [1, 2] raises ValidationError."""
        data = _make_valid_response()
        data["feed"]["categories"] = [1, 2]
        with pytest.raises(ValidationError):
            FeedResponse(**data)

    def test_feed_ttl_nullable_int(self):
        """feed.ttl accepts both null and integer values."""
        data = _make_valid_response()
        data["feed"]["ttl"] = None
        model = FeedResponse(**data)
        assert model.feed.ttl is None

        data["feed"]["ttl"] = 60
        model = FeedResponse(**data)
        assert model.feed.ttl == 60

    def test_feed_ttl_rejects_string(self):
        """feed.ttl: 'sixty' raises ValidationError."""
        data = _make_valid_response()
        data["feed"]["ttl"] = "sixty"
        with pytest.raises(ValidationError):
            FeedResponse(**data)

    def test_feed_extensions_is_dict(self):
        """feed.extensions: {'dc': {'creator': 'X'}} is accepted."""
        data = _make_valid_response()
        data["feed"]["extensions"] = {"dc": {"creator": "X"}}
        model = FeedResponse(**data)
        assert model.feed.extensions == {"dc": {"creator": "X"}}


class TestItemDefaults:
    """Test item default value application."""

    def test_item_defaults_applied(self):
        """Item dict with no optional fields gets defaults."""
        item = FeedItem()
        assert item.title == ""
        assert item.guid == ""
        assert item.categories == []
        assert item.enclosures == []
        assert item.pub_date is None
        assert item.updated is None
        assert item.comments_url is None
        assert item.comments_count is None
        assert item.guid_is_permalink is False
        assert item.thumbnail == ""
        assert item.extensions == {}


class TestItemFieldValidation:
    """Test individual item field validation."""

    def test_item_pub_date_nullable(self):
        """pub_date: null is accepted."""
        item = FeedItem(pub_date=None)
        assert item.pub_date is None

    def test_item_pub_date_accepts_iso_string(self):
        """pub_date: '2026-02-09T12:00:00Z' is accepted."""
        item = FeedItem(pub_date="2026-02-09T12:00:00Z")
        assert item.pub_date == "2026-02-09T12:00:00Z"

    def test_item_enclosure_structure(self):
        """Enclosure with all fields is accepted."""
        enc = Enclosure(url="https://example.com/audio.mp3", type="audio/mpeg", length=12345)
        assert enc.url == "https://example.com/audio.mp3"
        assert enc.type == "audio/mpeg"
        assert enc.length == 12345

    def test_item_enclosure_missing_fields(self):
        """Enclosure with only URL accepted; optional fields get defaults."""
        enc = Enclosure(url="https://example.com/file.mp3")
        assert enc.url == "https://example.com/file.mp3"
        assert enc.type == ""
        assert enc.length is None

    def test_item_guid_is_permalink_bool(self):
        """guid_is_permalink: 'yes' (string) raises ValidationError."""
        with pytest.raises(ValidationError):
            FeedItem(guid_is_permalink="yes")  # type: ignore

    def test_item_comments_count_nullable_int(self):
        """comments_count accepts both null and integer values."""
        item = FeedItem(comments_count=None)
        assert item.comments_count is None

        item = FeedItem(comments_count=5)
        assert item.comments_count == 5


class TestSerialization:
    """Test JSON serialization methods."""

    def test_response_serialization_json(self):
        """model_dump_json() produces valid JSON string."""
        data = _make_full_response()
        model = FeedResponse(**data)
        json_str = model.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["status"] == "ok"
        assert parsed["schema_version"] == "1.0"

    def test_response_serialization_excludes_none(self):
        """Serialized output includes null for None optional fields."""
        data = _make_valid_response()
        model = FeedResponse(**data)
        dumped = model.model_dump(mode="python")
        # message is None and should be in the dump
        assert "message" in dumped
        assert dumped["message"] is None

    def test_error_response_includes_message(self):
        """Error response with message field present in output."""
        data = _make_valid_response(status="error", message="Timeout connecting to server")
        model = FeedResponse(**data)
        dumped = model.model_dump(mode="python")
        assert dumped["status"] == "error"
        assert dumped["message"] == "Timeout connecting to server"
