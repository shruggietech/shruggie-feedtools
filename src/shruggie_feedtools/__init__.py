"""shruggie-feedtools — Normalize web feeds into a single predictable JSON schema."""

from shruggie_feedtools._version import __version__
from shruggie_feedtools.construct import construct, construct_batch
from shruggie_feedtools.core.parser import (
    parse,
    parse_file,
    parse_files,
    parse_string,
    parse_url,
    parse_urls,
)

__all__ = [
    "__version__",
    "construct",
    "construct_batch",
    "parse",
    "parse_file",
    "parse_files",
    "parse_string",
    "parse_url",
    "parse_urls",
]
