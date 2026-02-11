"""Tests for title, description, and GUID derivation strategies (§17.3 test_strategies.py)."""

from __future__ import annotations

import re

from shruggie_feedtools.construct.strategies import (
    derive_description,
    derive_title,
    generate_guid,
    generate_link,
)


# ════════════════════════════════════════════════════════════════════════════
# Title strategies (12 tests)
# ════════════════════════════════════════════════════════════════════════════


def test_title_first_line_basic() -> None:
    """first_line strategy extracts the first line."""
    assert derive_title("First line\nSecond line", "first_line") == "First line"


def test_title_first_line_no_newline() -> None:
    """Single-line text returns the entire text."""
    assert derive_title("Only one line", "first_line") == "Only one line"


def test_title_first_line_truncated() -> None:
    """First line exceeding max_length is truncated with …."""
    long_line = "A" * 200
    result = derive_title(long_line, "first_line", max_length=120)
    assert len(result) <= 120
    assert result.endswith("…")


def test_title_first_line_empty_text() -> None:
    """Empty text produces empty title."""
    assert derive_title("", "first_line") == ""


def test_title_first_line_leading_newline() -> None:
    """Leading newline means first line is empty."""
    assert derive_title("\nActual first line", "first_line") == ""


def test_title_truncate_basic() -> None:
    """truncate strategy truncates long text at word boundary."""
    text = "A " * 75  # 150 chars
    result = derive_title(text, "truncate", max_length=80)
    assert len(result) <= 80
    assert result.endswith("…")


def test_title_truncate_short_text() -> None:
    """Short text passes through without truncation or …."""
    assert derive_title("Short", "truncate", max_length=120) == "Short"


def test_title_truncate_word_boundary() -> None:
    """Truncation breaks at word boundary, not mid-word."""
    result = derive_title("Hello world goodbye", "truncate", max_length=12)
    assert result == "Hello world…"


def test_title_timestamp_format() -> None:
    """timestamp strategy formats as 'YYYY-MM-DD HH:MM:SS UTC'."""
    result = derive_title("ignored", "timestamp", timestamp="2026-02-10T08:30:00Z")
    assert result == "2026-02-10 08:30:00 UTC"


def test_title_template_with_placeholders() -> None:
    """template strategy resolves {index} and {timestamp} placeholders."""
    result = derive_title(
        "ignored",
        "template",
        timestamp="2026-02-10T08:30:00Z",
        index=5,
        title_template="Entry #{index} — {timestamp}",
    )
    assert result == "Entry #5 — 2026-02-10 08:30:00 UTC"


def test_title_template_missing_placeholder() -> None:
    """Static template string passes through unchanged."""
    result = derive_title(
        "ignored",
        "template",
        timestamp="2026-02-10T08:30:00Z",
        index=1,
        title_template="Static title",
    )
    assert result == "Static title"


def test_title_none_strategy() -> None:
    """none strategy always produces empty string."""
    assert derive_title("Any text here", "none") == ""


# ════════════════════════════════════════════════════════════════════════════
# Description strategies (6 tests)
# ════════════════════════════════════════════════════════════════════════════


def test_desc_truncate_basic() -> None:
    """truncate strategy truncates long text with …."""
    text = "W " * 250  # 500 chars
    result = derive_description(text, "truncate", max_length=280)
    assert len(result) <= 280
    assert result.endswith("…")


def test_desc_truncate_short_text() -> None:
    """Short text passes through without …."""
    text = "A " * 50  # 100 chars
    result = derive_description(text, "truncate", max_length=280)
    assert result == text
    assert not result.endswith("…")


def test_desc_truncate_word_boundary() -> None:
    """Truncation breaks at word boundary."""
    result = derive_description("one two three four five", "truncate", max_length=15)
    assert result == "one two three…"


def test_desc_first_line() -> None:
    """first_line strategy returns the first line."""
    assert derive_description("Summary line\nDetail paragraph...", "first_line") == "Summary line"


def test_desc_same_mirrors_content() -> None:
    """same strategy returns the input text as-is."""
    assert derive_description("Full content here", "same") == "Full content here"


def test_desc_none_strategy() -> None:
    """none strategy returns empty string."""
    assert derive_description("Any text", "none") == ""


# ════════════════════════════════════════════════════════════════════════════
# GUID strategies (10 tests)
# ════════════════════════════════════════════════════════════════════════════


def test_guid_sha256_deterministic() -> None:
    """Same input produces the same SHA-256 GUID."""
    g1 = generate_guid("hello", "2026-02-10T08:30:00Z", "sha256")
    g2 = generate_guid("hello", "2026-02-10T08:30:00Z", "sha256")
    assert g1 == g2


def test_guid_sha256_different_text() -> None:
    """Different text produces different GUIDs."""
    g1 = generate_guid("hello", "2026-02-10T08:30:00Z", "sha256")
    g2 = generate_guid("world", "2026-02-10T08:30:00Z", "sha256")
    assert g1 != g2


def test_guid_sha256_different_timestamp() -> None:
    """Different timestamps produce different GUIDs."""
    g1 = generate_guid("hello", "2026-02-10T08:30:00Z", "sha256")
    g2 = generate_guid("hello", "2026-02-11T08:30:00Z", "sha256")
    assert g1 != g2


def test_guid_sha256_format() -> None:
    """SHA-256 GUID is a 64-character lowercase hex string."""
    g = generate_guid("test", "2026-02-10T08:30:00Z", "sha256")
    assert len(g) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", g)


def test_guid_uuid4_format() -> None:
    """UUID4 GUID matches the 8-4-4-4-12 hex format with version nibble 4."""
    g = generate_guid("test", "2026-02-10T08:30:00Z", "uuid4")
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        g,
    )


def test_guid_uuid4_not_deterministic() -> None:
    """Two UUID4 calls produce different values."""
    g1 = generate_guid("test", "2026-02-10T08:30:00Z", "uuid4")
    g2 = generate_guid("test", "2026-02-10T08:30:00Z", "uuid4")
    assert g1 != g2


def test_guid_timestamp_format() -> None:
    """timestamp strategy uses the ISO string as the GUID."""
    g = generate_guid("test", "2026-02-10T08:30:00Z", "timestamp")
    assert g == "2026-02-10T08:30:00Z"


def test_guid_sequential_format() -> None:
    """sequential strategy produces '{slug}-{padded_index}'."""
    g = generate_guid("", "", "sequential", feed_title="Server Incident Log", index=3)
    assert g == "server-incident-log-003"


def test_guid_sequential_slug_generation() -> None:
    """Slug contains only lowercase alphanumerics and hyphens."""
    g = generate_guid(
        "", "", "sequential",
        feed_title="My Feed — Special (Chars!)",
        index=1,
    )
    # The slug portion (before the last dash+digits) should be clean
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*-\d{3,}", g)


def test_guid_sequential_zero_padded() -> None:
    """Index 1 with batch_size < 1000 produces 3-digit zero-padded index."""
    g = generate_guid(
        "", "", "sequential",
        feed_title="Feed",
        index=1,
        batch_size=50,
    )
    assert g.endswith("-001")


# ════════════════════════════════════════════════════════════════════════════
# Link generation (supplementary)
# ════════════════════════════════════════════════════════════════════════════


def test_generate_link_with_pattern() -> None:
    """Substitutes {guid} into the pattern."""
    assert generate_link("https://x.com/{guid}", "abc123") == "https://x.com/abc123"


def test_generate_link_none_pattern() -> None:
    """None pattern returns empty string."""
    assert generate_link(None, "abc123") == ""
