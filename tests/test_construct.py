"""Tests for feed construction pipeline (§17.3 test_construct.py).

Integration tests for construct mode — template + text + timestamp → builder
→ Pydantic validation → output.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from shruggie_feedtools.construct import construct, construct_batch, load_template
from shruggie_feedtools.construct.entry import parse_entries
from shruggie_feedtools.core.schema import FeedResponse

TEMPLATES_DIR = Path(__file__).parent / "fixtures" / "templates"
ENTRIES_DIR = Path(__file__).parent / "fixtures" / "entries"

MINIMAL_TEMPLATE = TEMPLATES_DIR / "minimal.feedtemplate.json"
INCIDENT_LOG_TEMPLATE = TEMPLATES_DIR / "incident_log.feedtemplate.json"
CHANGELOG_TEMPLATE = TEMPLATES_DIR / "changelog.feedtemplate.json"


# ── Single-item construction ────────────────────────────────────────────────


def test_construct_single_item() -> None:
    """Single construct call produces status=ok, source.type=constructed, 1 item."""
    result = construct(
        text="Hello world",
        timestamp="2026-02-10T08:30:00Z",
        template=MINIMAL_TEMPLATE,
    )
    assert result["status"] == "ok"
    assert result["source"]["type"] == "constructed"
    assert result["source"]["origin"] == "template"
    assert len(result["items"]) == 1


def test_construct_item_content_from_text() -> None:
    """text_target=content → items[0].content is the text."""
    result = construct(
        text="Hello world",
        timestamp="2026-02-10T08:30:00Z",
        template=MINIMAL_TEMPLATE,
    )
    assert result["items"][0]["content"] == "Hello world"


def test_construct_item_content_to_description() -> None:
    """text_target=description → text goes to description, content is empty."""
    tmpl = {
        "template_version": "1.0",
        "feed": {"title": "T"},
        "item_mapping": {"text_target": "description", "title_strategy": "first_line", "guid_strategy": "sha256"},
    }
    result = construct(text="Desc text", timestamp="2026-02-10T08:30:00Z", template=tmpl)
    assert result["items"][0]["description"] == "Desc text"
    assert result["items"][0]["content"] == ""


def test_construct_item_content_to_both() -> None:
    """text_target=both → content is text, description is derived from text."""
    tmpl = {
        "template_version": "1.0",
        "feed": {"title": "T"},
        "item_mapping": {"text_target": "both", "title_strategy": "first_line", "guid_strategy": "sha256"},
    }
    result = construct(text="Both text", timestamp="2026-02-10T08:30:00Z", template=tmpl)
    assert result["items"][0]["content"] == "Both text"
    assert result["items"][0]["description"] != ""


# ── Timestamps ──────────────────────────────────────────────────────────────


def test_construct_pub_date_from_timestamp() -> None:
    """ISO 8601 UTC timestamp passes through to pub_date."""
    result = construct(text="x", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    assert result["items"][0]["pub_date"] == "2026-02-10T08:30:00Z"


def test_construct_pub_date_normalizes_offset() -> None:
    """Offset timestamp is normalized to UTC."""
    result = construct(text="x", timestamp="2026-02-10T03:30:00-05:00", template=MINIMAL_TEMPLATE)
    assert result["items"][0]["pub_date"] == "2026-02-10T08:30:00Z"


def test_construct_pub_date_from_epoch() -> None:
    """Unix epoch timestamp produces a valid ISO 8601 UTC string."""
    result = construct(text="x", timestamp="1770595200", template=MINIMAL_TEMPLATE)
    pub_date = result["items"][0]["pub_date"]
    assert pub_date is not None
    assert pub_date.endswith("Z")


# ── Feed metadata ───────────────────────────────────────────────────────────


def test_construct_feed_metadata_from_template() -> None:
    """Feed metadata fields match the template."""
    result = construct(text="x", timestamp="2026-02-10T08:30:00Z", template=INCIDENT_LOG_TEMPLATE)
    feed = result["feed"]
    assert feed["title"] == "Server Incident Log"
    assert feed["link"] == "https://status.example.com"
    assert feed["description"] == "Automated incident reports from monitoring"
    assert feed["language"] == "en-us"
    assert feed["author"] == "ops-bot"


def test_construct_feed_generator_forced() -> None:
    """Generator is always 'shruggie-feedtools/0.1.1'."""
    result = construct(text="x", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    assert result["feed"]["generator"] == "shruggie-feedtools/0.1.1"


def test_construct_feed_last_updated_computed() -> None:
    """last_updated equals the latest pub_date across all items."""
    entries = [
        {"text": "a", "timestamp": "2026-02-10T08:00:00Z"},
        {"text": "b", "timestamp": "2026-02-10T10:00:00Z"},
        {"text": "c", "timestamp": "2026-02-10T09:00:00Z"},
    ]
    result = construct_batch(entries=entries, template=MINIMAL_TEMPLATE)
    assert result["feed"]["last_updated"] == "2026-02-10T10:00:00Z"


# ── Item defaults and overrides ─────────────────────────────────────────────


def test_construct_item_defaults_applied() -> None:
    """Template item_defaults are applied to items."""
    result = construct(text="x", timestamp="2026-02-10T08:30:00Z", template=INCIDENT_LOG_TEMPLATE)
    item = result["items"][0]
    assert item["author"] == "ops-bot"
    assert item["categories"] == ["incident"]


def test_construct_item_defaults_overridden_by_entry() -> None:
    """Per-entry override takes precedence over template defaults."""
    entries = [{"text": "x", "timestamp": "2026-02-10T08:30:00Z", "author": "jdoe"}]
    result = construct_batch(entries=entries, template=INCIDENT_LOG_TEMPLATE)
    assert result["items"][0]["author"] == "jdoe"


# ── Link pattern ────────────────────────────────────────────────────────────


def test_construct_link_pattern() -> None:
    """link_pattern with {guid} generates item links."""
    tmpl = {
        "template_version": "1.0",
        "feed": {"title": "T"},
        "item_mapping": {
            "text_target": "content",
            "title_strategy": "first_line",
            "guid_strategy": "sha256",
            "link_pattern": "https://x.com/{guid}",
        },
    }
    result = construct(text="test", timestamp="2026-02-10T08:30:00Z", template=tmpl)
    guid = result["items"][0]["guid"]
    assert result["items"][0]["link"] == f"https://x.com/{guid}"


def test_construct_source_url_null() -> None:
    """source.url is always null for constructed feeds."""
    result = construct(text="x", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    assert result["source"]["url"] is None


# ── Batch construction ──────────────────────────────────────────────────────


def test_construct_batch_multiple_items() -> None:
    """3 entries produce 3 items with correct pub_dates."""
    entries = [
        {"text": "a", "timestamp": "2026-02-10T08:00:00Z"},
        {"text": "b", "timestamp": "2026-02-10T09:00:00Z"},
        {"text": "c", "timestamp": "2026-02-10T10:00:00Z"},
    ]
    result = construct_batch(entries=entries, template=MINIMAL_TEMPLATE)
    assert len(result["items"]) == 3
    assert result["items"][0]["pub_date"] == "2026-02-10T08:00:00Z"
    assert result["items"][1]["pub_date"] == "2026-02-10T09:00:00Z"
    assert result["items"][2]["pub_date"] == "2026-02-10T10:00:00Z"


def test_construct_batch_ordering() -> None:
    """Items appear in the order provided (no automatic sorting)."""
    entries = [
        {"text": "c", "timestamp": "2026-02-10T10:00:00Z"},
        {"text": "a", "timestamp": "2026-02-10T08:00:00Z"},
        {"text": "b", "timestamp": "2026-02-10T09:00:00Z"},
    ]
    result = construct_batch(entries=entries, template=MINIMAL_TEMPLATE)
    dates = [item["pub_date"] for item in result["items"]]
    assert dates == [
        "2026-02-10T10:00:00Z",
        "2026-02-10T08:00:00Z",
        "2026-02-10T09:00:00Z",
    ]


def test_construct_batch_from_jsonl() -> None:
    """batch_entries.jsonl fixture produces all 10 entries."""
    result = construct_batch(
        entries=ENTRIES_DIR / "batch_entries.jsonl",
        template=INCIDENT_LOG_TEMPLATE,
    )
    assert len(result["items"]) == 10


def test_construct_batch_entry_overrides() -> None:
    """Per-entry title, author, categories override template defaults."""
    result = construct_batch(
        entries=ENTRIES_DIR / "entries_with_overrides.jsonl",
        template=INCIDENT_LOG_TEMPLATE,
    )
    items = result["items"]
    # First entry has title, author, and categories overrides
    assert items[0]["title"] == "CRITICAL: web-03 Down"
    assert items[0]["author"] == "jdoe"
    assert items[0]["categories"] == ["critical", "web-03"]
    # Second entry has only author override
    assert items[1]["author"] == "jsmith"
    assert items[1]["categories"] == ["incident"]  # from template defaults
    # Third entry has only categories override
    assert items[2]["categories"] == ["resolved"]
    assert items[2]["author"] == "ops-bot"  # from template defaults


def test_construct_batch_bad_entry_skipped(caplog: pytest.LogCaptureFixture) -> None:
    """Malformed JSONL lines are skipped with warning; valid entries succeed."""
    lines = [
        '{"text": "good1", "timestamp": "2026-02-10T08:00:00Z"}',
        "{broken json",
        '{"text": "good2", "timestamp": "2026-02-10T09:00:00Z"}',
    ]
    with caplog.at_level(logging.WARNING, logger="shruggie_feedtools"):
        entries = parse_entries(lines)
    assert len(entries) == 2
    assert any("malformed" in r.message.lower() for r in caplog.records)


# ── Inline template ────────────────────────────────────────────────────────


def test_construct_inline_template_dict() -> None:
    """Template passed as Python dict produces valid output."""
    tmpl = {
        "template_version": "1.0",
        "feed": {"title": "Inline Feed"},
        "item_mapping": {"text_target": "content", "title_strategy": "first_line", "guid_strategy": "sha256"},
    }
    result = construct(text="Inline entry", timestamp="2026-02-10T08:30:00Z", template=tmpl)
    assert result["status"] == "ok"
    assert result["feed"]["title"] == "Inline Feed"
    assert len(result["items"]) == 1


# ── Edge cases ──────────────────────────────────────────────────────────────


def test_construct_output_validates_against_schema() -> None:
    """Output passes Pydantic model validation with zero errors."""
    result = construct(text="Validate me", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    # This will raise if the output doesn't conform to the schema
    FeedResponse.model_validate(result)


def test_construct_empty_text() -> None:
    """Empty text produces status=ok with content=''."""
    result = construct(text="", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    assert result["status"] == "ok"
    assert result["items"][0]["content"] == ""


def test_construct_guid_deterministic_sha256() -> None:
    """Same text + same timestamp produces the same GUID (sha256)."""
    r1 = construct(text="same", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    r2 = construct(text="same", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    assert r1["items"][0]["guid"] == r2["items"][0]["guid"]


def test_construct_guid_different_inputs() -> None:
    """Different text with same timestamp produces different GUIDs."""
    r1 = construct(text="text_a", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    r2 = construct(text="text_b", timestamp="2026-02-10T08:30:00Z", template=MINIMAL_TEMPLATE)
    assert r1["items"][0]["guid"] != r2["items"][0]["guid"]


# ── Snapshots ───────────────────────────────────────────────────────────────


def test_snapshot_construct_minimal_single(assert_snapshot) -> None:
    """Snapshot: minimal template + single entry."""
    result = construct(
        text="Server web-03 is experiencing elevated latency on port 443.",
        timestamp="2026-02-10T08:30:00Z",
        template=MINIMAL_TEMPLATE,
    )
    assert_snapshot(result, "minimal_single", subfolder="construct")


def test_snapshot_construct_incident_log_batch(assert_snapshot) -> None:
    """Snapshot: incident_log template + batch_entries.jsonl."""
    result = construct_batch(
        entries=ENTRIES_DIR / "batch_entries.jsonl",
        template=INCIDENT_LOG_TEMPLATE,
    )
    assert_snapshot(result, "incident_log_batch", subfolder="construct")


def test_snapshot_construct_changelog_with_link_pattern(assert_snapshot) -> None:
    """Snapshot: changelog template with link_pattern + single entry."""
    result = construct(
        text="Refactored the adapter pipeline\nSplit feedparser_adapter into per-format modules for clarity.",
        timestamp="2026-02-10T14:00:00Z",
        template=CHANGELOG_TEMPLATE,
    )
    assert_snapshot(result, "changelog_with_link_pattern", subfolder="construct")


def test_snapshot_construct_entry_overrides(assert_snapshot) -> None:
    """Snapshot: incident_log template + entries_with_overrides.jsonl."""
    result = construct_batch(
        entries=ENTRIES_DIR / "entries_with_overrides.jsonl",
        template=INCIDENT_LOG_TEMPLATE,
    )
    assert_snapshot(result, "entry_overrides", subfolder="construct")
