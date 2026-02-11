"""Tests for date parsing and normalization.

Covers: RFC 2822, ISO 8601, loose formats, Unix epoch, garbage input,
empty strings, partial dates, and UTC enforcement.
"""

from __future__ import annotations

import pytest

from shruggie_feedtools.core.dates import normalize_date


class TestRFC2822:
    """Test RFC 822 / RFC 2822 date parsing."""

    def test_parse_rfc2822(self):
        """Standard RFC 2822 date with GMT timezone."""
        result = normalize_date("Thu, 09 Feb 2026 12:00:00 GMT")
        assert result == "2026-02-09T12:00:00Z"

    def test_parse_rfc2822_with_offset(self):
        """RFC 2822 date with -0500 offset converted to UTC."""
        result = normalize_date("Thu, 09 Feb 2026 07:00:00 -0500")
        assert result == "2026-02-09T12:00:00Z"


class TestISO8601:
    """Test ISO 8601 date parsing."""

    def test_parse_iso8601_utc(self):
        """ISO 8601 with Z suffix passes through unchanged."""
        result = normalize_date("2026-02-09T12:00:00Z")
        assert result == "2026-02-09T12:00:00Z"

    def test_parse_iso8601_offset(self):
        """ISO 8601 with +05:00 offset converted to UTC."""
        result = normalize_date("2026-02-09T12:00:00+05:00")
        assert result == "2026-02-09T07:00:00Z"

    def test_parse_iso8601_no_tz(self):
        """ISO 8601 without timezone assumed UTC."""
        result = normalize_date("2026-02-09T12:00:00")
        assert result == "2026-02-09T12:00:00Z"


class TestLooseFormats:
    """Test loose / informal date parsing."""

    def test_parse_loose_date_only(self):
        """Human-readable date string parsed to midnight UTC."""
        result = normalize_date("February 9, 2026")
        assert result == "2026-02-09T00:00:00Z"

    def test_parse_loose_ymd(self):
        """Year-month-day string parsed to midnight UTC."""
        result = normalize_date("2026-02-09")
        assert result == "2026-02-09T00:00:00Z"


class TestUnixEpoch:
    """Test Unix epoch timestamp handling."""

    def test_parse_unix_epoch_int(self):
        """Integer epoch value converted to ISO 8601 UTC."""
        result = normalize_date(1770638400)
        assert result == "2026-02-09T12:00:00Z"

    def test_parse_unix_epoch_float(self):
        """Float epoch value converted to ISO 8601 UTC (truncated to seconds)."""
        result = normalize_date(1770638400.5)
        assert result == "2026-02-09T12:00:00Z"


class TestEdgeCases:
    """Test garbage, empty, partial, and edge case inputs."""

    def test_parse_garbage_returns_none(self):
        """Completely nonsensical string returns None."""
        result = normalize_date("not a date at all")
        assert result is None

    def test_parse_empty_returns_none(self):
        """Empty string returns None."""
        result = normalize_date("")
        assert result is None

    def test_parse_none_returns_none(self):
        """None input returns None."""
        result = normalize_date(None)
        assert result is None

    def test_parse_partial_date(self):
        """Partial date 'Feb 2026' parsed best-effort to first of month."""
        result = normalize_date("Feb 2026")
        assert result == "2026-02-01T00:00:00Z"


class TestUTCEnforcement:
    """Test that all outputs are always in UTC with Z suffix."""

    @pytest.mark.parametrize(
        "input_date",
        [
            "Thu, 09 Feb 2026 07:00:00 -0500",
            "2026-02-09T12:00:00+05:00",
            "2026-02-09T12:00:00Z",
            "2026-02-09T12:00:00",
            "February 9, 2026",
            1770638400,
        ],
    )
    def test_all_outputs_are_utc(self, input_date):
        """Every non-None output ends in Z (no offset strings)."""
        result = normalize_date(input_date)
        assert result is not None
        assert result.endswith("Z"), f"Expected Z suffix, got: {result}"
        assert "+" not in result[:-1], f"Unexpected offset in: {result}"
