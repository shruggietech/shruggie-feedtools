"""Tests for template loading and validation (§17.3 test_template.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shruggie_feedtools.construct.template import (
    FeedTemplate,
    TemplateValidationError,
    _template_cache,
    load_template,
)

TEMPLATES_DIR = Path(__file__).parent / "fixtures" / "templates"


# ── Valid templates ──────────────────────────────────────────────────────────


def test_load_minimal_template() -> None:
    """Minimal template loads; template_version is '1.0', feed.title is set."""
    tmpl = load_template(TEMPLATES_DIR / "minimal.feedtemplate.json")
    assert tmpl.template_version == "1.0"
    assert tmpl.feed.title == "My Feed"


def test_load_full_template() -> None:
    """Full template (incident_log) — all fields populated, no defaults needed."""
    tmpl = load_template(TEMPLATES_DIR / "incident_log.feedtemplate.json")
    assert tmpl.feed.title == "Server Incident Log"
    assert tmpl.feed.link == "https://status.example.com"
    assert tmpl.feed.description == "Automated incident reports from monitoring"
    assert tmpl.feed.language == "en-us"
    assert tmpl.feed.author == "ops-bot"
    assert tmpl.feed.image == "https://status.example.com/logo.png"
    assert tmpl.feed.categories == ["infrastructure", "monitoring"]
    assert tmpl.feed.ttl == 15
    assert tmpl.item_mapping.text_target.value == "content"
    assert tmpl.item_mapping.title_strategy.value == "first_line"
    assert tmpl.item_mapping.title_max_length == 120
    assert tmpl.item_mapping.description_strategy.value == "truncate"
    assert tmpl.item_mapping.description_max_length == 280
    assert tmpl.item_mapping.guid_strategy.value == "sha256"
    assert tmpl.item_defaults.author == "ops-bot"
    assert tmpl.item_defaults.categories == ["incident"]


# ── Default application ─────────────────────────────────────────────────────


def test_load_template_defaults_item_mapping() -> None:
    """Minimal template with item_mapping containing only text_target gets defaults."""
    tmpl = load_template({
        "template_version": "1.0",
        "feed": {"title": "T"},
        "item_mapping": {"text_target": "content"},
    })
    assert tmpl.item_mapping.title_strategy.value == "first_line"
    assert tmpl.item_mapping.title_max_length == 120
    assert tmpl.item_mapping.description_strategy.value == "truncate"
    assert tmpl.item_mapping.description_max_length == 280
    assert tmpl.item_mapping.guid_strategy.value == "sha256"
    assert tmpl.item_mapping.link_pattern is None


def test_load_template_defaults_item_defaults() -> None:
    """Minimal template with no item_defaults section gets correct defaults."""
    tmpl = load_template({
        "template_version": "1.0",
        "feed": {"title": "T"},
        "item_mapping": {"text_target": "content"},
    })
    assert tmpl.item_defaults.author == ""
    assert tmpl.item_defaults.categories == []
    assert tmpl.item_defaults.thumbnail == ""
    assert tmpl.item_defaults.link == ""
    assert tmpl.item_defaults.extensions == {}


def test_load_template_defaults_feed_optional_fields() -> None:
    """Template with only feed.title gets defaults for all optional feed fields."""
    tmpl = load_template({
        "template_version": "1.0",
        "feed": {"title": "T"},
        "item_mapping": {"text_target": "content"},
    })
    assert tmpl.feed.link == ""
    assert tmpl.feed.description == ""
    assert tmpl.feed.language == ""
    assert tmpl.feed.author == ""
    assert tmpl.feed.image == ""
    assert tmpl.feed.categories == []
    assert tmpl.feed.ttl is None


# ── Validation errors ───────────────────────────────────────────────────────


def test_load_missing_template_version() -> None:
    """Missing template_version raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError, match="template_version"):
        load_template({
            "feed": {"title": "T"},
            "item_mapping": {"text_target": "content"},
        })


def test_load_missing_feed_title() -> None:
    """Missing feed.title (fixture file) raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError, match="title"):
        load_template(TEMPLATES_DIR / "invalid_missing_title.feedtemplate.json")


def test_load_missing_item_mapping() -> None:
    """Missing item_mapping section raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError, match="item_mapping"):
        load_template({
            "template_version": "1.0",
            "feed": {"title": "T"},
        })


def test_load_invalid_text_target() -> None:
    """Invalid text_target value raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError):
        load_template({
            "template_version": "1.0",
            "feed": {"title": "T"},
            "item_mapping": {"text_target": "title"},
        })


def test_load_invalid_title_strategy() -> None:
    """Invalid title_strategy value raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError):
        load_template({
            "template_version": "1.0",
            "feed": {"title": "T"},
            "item_mapping": {"text_target": "content", "title_strategy": "random"},
        })


def test_load_invalid_description_strategy() -> None:
    """Invalid description_strategy raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError):
        load_template({
            "template_version": "1.0",
            "feed": {"title": "T"},
            "item_mapping": {"text_target": "content", "description_strategy": "ai_summary"},
        })


def test_load_invalid_guid_strategy() -> None:
    """Invalid guid_strategy raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError):
        load_template({
            "template_version": "1.0",
            "feed": {"title": "T"},
            "item_mapping": {"text_target": "content", "guid_strategy": "md5"},
        })


def test_load_title_max_length_must_be_positive() -> None:
    """title_max_length of 0 raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError):
        load_template({
            "template_version": "1.0",
            "feed": {"title": "T"},
            "item_mapping": {"text_target": "content", "title_max_length": 0},
        })


def test_load_description_max_length_must_be_positive() -> None:
    """description_max_length of -1 raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError):
        load_template({
            "template_version": "1.0",
            "feed": {"title": "T"},
            "item_mapping": {"text_target": "content", "description_max_length": -1},
        })


# ── Loading modes ────────────────────────────────────────────────────────────


def test_load_template_from_dict() -> None:
    """Loading from a Python dict validates identically to file-based loading."""
    tmpl = load_template({
        "template_version": "1.0",
        "feed": {"title": "Dict Feed"},
        "item_mapping": {"text_target": "content", "guid_strategy": "uuid4"},
    })
    assert isinstance(tmpl, FeedTemplate)
    assert tmpl.feed.title == "Dict Feed"
    assert tmpl.item_mapping.guid_strategy.value == "uuid4"


def test_load_nonexistent_file() -> None:
    """Path to a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_template("/nonexistent/path/template.feedtemplate.json")


def test_load_invalid_json(tmp_path: Path) -> None:
    """File with broken JSON raises TemplateValidationError."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{broken json", encoding="utf-8")
    with pytest.raises(TemplateValidationError, match="JSON"):
        load_template(bad_file)


def test_load_template_caching() -> None:
    """Same file path loaded twice returns a functionally identical result."""
    _template_cache.clear()
    path = TEMPLATES_DIR / "minimal.feedtemplate.json"
    tmpl1 = load_template(path)
    tmpl2 = load_template(path)
    assert tmpl1 is tmpl2


def test_template_version_unsupported() -> None:
    """Unsupported template_version raises TemplateValidationError."""
    with pytest.raises(TemplateValidationError, match="Unsupported"):
        load_template({
            "template_version": "2.0",
            "feed": {"title": "T"},
            "item_mapping": {"text_target": "content"},
        })
