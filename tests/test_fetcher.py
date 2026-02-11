"""Tests for the HTTP fetcher module."""

from __future__ import annotations

import httpx

from shruggie_feedtools.core.config import ParserConfig
from shruggie_feedtools.core.fetcher import fetch


def _patch_client(monkeypatch, handler):
    """Monkeypatch httpx.Client to use a mock transport.

    We replace the entire Client class with a wrapper that injects
    the mock transport while preserving other kwargs.
    """
    _original_client = httpx.Client

    class MockClient(_original_client):
        def __init__(self, **kwargs):
            kwargs.pop("verify", None)
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(**kwargs)

    monkeypatch.setattr("shruggie_feedtools.core.fetcher.httpx.Client", MockClient)


class TestFetcher:
    """§17.3 test_fetcher.py — HTTP Fetching."""

    def test_fetch_returns_bytes(self, monkeypatch):
        body = b"<rss><channel><title>Test</title></channel></rss>"

        def handler(request):
            return httpx.Response(200, content=body)

        _patch_client(monkeypatch, handler)
        result = fetch("http://example.com/feed")
        assert result.ok
        assert result.content == body

    def test_fetch_captures_content_type(self, monkeypatch):
        def handler(request):
            return httpx.Response(
                200,
                content=b"<rss/>",
                headers={"content-type": "application/rss+xml"},
            )

        _patch_client(monkeypatch, handler)
        result = fetch("http://example.com/feed")
        assert result.ok
        assert "rss" in result.content_type

    def test_fetch_captures_etag(self, monkeypatch):
        def handler(request):
            return httpx.Response(
                200,
                content=b"<rss/>",
                headers={"etag": '"abc123"'},
            )

        _patch_client(monkeypatch, handler)
        result = fetch("http://example.com/feed")
        assert result.ok
        assert result.etag == '"abc123"'

    def test_fetch_captures_last_modified(self, monkeypatch):
        def handler(request):
            return httpx.Response(
                200,
                content=b"<rss/>",
                headers={"last-modified": "Sat, 01 Jan 2026 00:00:00 GMT"},
            )

        _patch_client(monkeypatch, handler)
        result = fetch("http://example.com/feed")
        assert result.ok
        assert "2026" in result.last_modified

    def test_fetch_http_404_returns_error(self, monkeypatch):
        def handler(request):
            return httpx.Response(404, content=b"Not Found")

        _patch_client(monkeypatch, handler)
        result = fetch("http://example.com/missing")
        assert not result.ok
        assert "404" in result.error

    def test_fetch_http_500_returns_error(self, monkeypatch):
        def handler(request):
            return httpx.Response(500, content=b"Server Error")

        _patch_client(monkeypatch, handler)
        config = ParserConfig(retries=0)
        result = fetch("http://example.com/broken", config)
        assert not result.ok
        assert "500" in result.error

    def test_fetch_max_response_size(self, monkeypatch):
        big_body = b"x" * (1024 * 1024 + 1)  # Just over 1MB

        def handler(request):
            return httpx.Response(200, content=big_body)

        _patch_client(monkeypatch, handler)
        config = ParserConfig(max_response_bytes=1024 * 1024)  # 1MB limit
        result = fetch("http://example.com/big", config)
        assert not result.ok
        assert "too large" in result.error.lower()

    def test_fetch_retry_on_transient_error(self, monkeypatch):
        call_count = 0

        def handler(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(503, content=b"Service Unavailable")
            return httpx.Response(200, content=b"<rss/>")

        _patch_client(monkeypatch, handler)
        monkeypatch.setattr("shruggie_feedtools.core.fetcher.time.sleep", lambda _: None)
        config = ParserConfig(retries=2)
        result = fetch("http://example.com/flaky", config)
        assert result.ok
        assert call_count == 2

    def test_fetch_retry_exhaustion(self, monkeypatch):
        call_count = 0

        def handler(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(503, content=b"Service Unavailable")

        _patch_client(monkeypatch, handler)
        monkeypatch.setattr("shruggie_feedtools.core.fetcher.time.sleep", lambda _: None)
        config = ParserConfig(retries=2)
        result = fetch("http://example.com/down", config)
        assert not result.ok
        # 1 initial + 2 retries = 3 total
        assert call_count == 3

    def test_fetch_user_agent_header(self, monkeypatch):
        captured_headers = {}

        def handler(request):
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, content=b"<rss/>")

        _patch_client(monkeypatch, handler)
        fetch("http://example.com/feed")
        assert "shruggie-feedtools" in captured_headers.get("user-agent", "")

    def test_fetch_custom_user_agent(self, monkeypatch):
        captured_headers = {}

        def handler(request):
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, content=b"<rss/>")

        _patch_client(monkeypatch, handler)
        config = ParserConfig(user_agent="custom/1.0")
        fetch("http://example.com/feed", config)
        assert captured_headers.get("user-agent") == "custom/1.0"

    def test_fetch_accept_header(self, monkeypatch):
        captured_headers = {}

        def handler(request):
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, content=b"<rss/>")

        _patch_client(monkeypatch, handler)
        fetch("http://example.com/feed")
        accept = captured_headers.get("accept", "")
        assert "rss" in accept or "xml" in accept or "json" in accept
