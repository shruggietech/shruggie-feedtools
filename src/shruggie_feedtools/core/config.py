"""Parser configuration object.

Passed explicitly to parse functions — no global state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParserConfig:
    """Configuration for parse operations.

    All settings have sensible defaults. Pass an instance to any parse
    function to customize behavior.
    """

    # HTTP
    timeout_connect: float = 10.0
    timeout_read: float = 30.0
    max_response_bytes: int = 10 * 1024 * 1024  # 10 MB
    user_agent: str = "shruggie-feedtools/0.1.1"
    verify_ssl: bool = True
    max_redirects: int = 5
    retries: int = 2

    # Parsing
    max_items: int | None = None
    include_extensions: bool = True
    thumbnail_extraction: bool = True
    normalize_namespaces: bool = True

    # Output
    pretty_print: bool = False
    indent: int = 2
