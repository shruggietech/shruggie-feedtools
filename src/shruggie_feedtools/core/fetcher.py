"""HTTP client for fetching feeds.

Uses httpx for HTTP requests with configurable timeouts, retries,
redirect limits, response size caps, and custom headers.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

from shruggie_feedtools.core.config import ParserConfig

logger = logging.getLogger("shruggie_feedtools")

# Accept header for feed-friendly content types
_ACCEPT_HEADER = (
    "application/rss+xml, application/atom+xml, application/xml, "
    "application/json, application/feed+json, text/xml, text/html;q=0.5, */*;q=0.1"
)


@dataclass
class FetchResult:
    """Result of an HTTP fetch operation."""

    ok: bool
    content: bytes = b""
    content_type: str = ""
    final_url: str = ""
    etag: str = ""
    last_modified: str = ""
    status_code: int = 0
    error: str = ""
    headers: dict[str, str] = field(default_factory=dict)


def fetch(url: str, config: ParserConfig | None = None) -> FetchResult:
    """Fetch feed content from a URL.

    Implements timeouts, retries with exponential backoff, redirect limits,
    response size caps, and custom User-Agent.

    Args:
        url: The URL to fetch.
        config: Parser configuration. Uses defaults if not provided.

    Returns:
        A ``FetchResult`` with the response data or error information.
    """
    if config is None:
        config = ParserConfig()

    timeout = httpx.Timeout(
        connect=config.timeout_connect,
        read=config.timeout_read,
        write=30.0,
        pool=30.0,
    )

    headers = {
        "User-Agent": config.user_agent,
        "Accept": _ACCEPT_HEADER,
    }

    last_error = ""
    attempts = 1 + config.retries  # initial + retries

    for attempt in range(attempts):
        if attempt > 0:
            # Exponential backoff: 1s, 2s, 4s, ...
            backoff = 2 ** (attempt - 1)
            logger.debug("Retry %d/%d after %ds backoff", attempt, config.retries, backoff)
            time.sleep(backoff)

        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=config.max_redirects,
                verify=config.verify_ssl,
            ) as client:
                response = client.get(url, headers=headers)

            # Check response size
            content_length = len(response.content)
            if content_length > config.max_response_bytes:
                return FetchResult(
                    ok=False,
                    status_code=response.status_code,
                    error=(
                        f"Response too large: {content_length} bytes "
                        f"(limit: {config.max_response_bytes} bytes)"
                    ),
                    final_url=str(response.url),
                )

            # HTTP error status
            if response.status_code >= 400:
                last_error = f"HTTP {response.status_code}: {response.reason_phrase}"
                # Retry on 5xx, not on 4xx
                if response.status_code >= 500:
                    logger.debug("Server error %d, will retry", response.status_code)
                    continue
                return FetchResult(
                    ok=False,
                    status_code=response.status_code,
                    error=last_error,
                    final_url=str(response.url),
                )

            # Success
            resp_headers = dict(response.headers)
            return FetchResult(
                ok=True,
                content=response.content,
                content_type=resp_headers.get("content-type", ""),
                final_url=str(response.url),
                etag=resp_headers.get("etag", ""),
                last_modified=resp_headers.get("last-modified", ""),
                status_code=response.status_code,
                headers=resp_headers,
            )

        except httpx.TooManyRedirects:
            return FetchResult(
                ok=False,
                error=f"Too many redirects (limit: {config.max_redirects})",
            )

        except httpx.ConnectTimeout:
            last_error = f"Connection timeout after {config.timeout_connect}s"
            logger.debug(last_error)
            continue

        except httpx.ReadTimeout:
            last_error = f"Read timeout after {config.timeout_read}s"
            logger.debug(last_error)
            continue

        except httpx.ConnectError as e:
            last_error = f"Connection error: {e}"
            logger.debug(last_error)
            continue

        except httpx.HTTPError as e:
            last_error = f"HTTP error: {e}"
            logger.debug(last_error)
            continue

    # All attempts exhausted
    return FetchResult(ok=False, error=last_error)
