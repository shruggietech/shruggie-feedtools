"""Parser configuration object.

Passed explicitly to parse functions — no global state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shruggie_feedtools._version import __version__


def _default_user_agent() -> str:
    return f"shruggie-feedtools/{__version__}"


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
    user_agent: str = field(default_factory=_default_user_agent)
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
