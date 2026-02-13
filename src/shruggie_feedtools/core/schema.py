"""Pydantic models for the shruggie-feedtools output schema.

All output — from both parse mode and construct mode — conforms to these models.
The schema is versioned (currently 1.0) and designed for stability.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Status(str, Enum):
    """Response status."""

    OK = "ok"
    ERROR = "error"


class SourceType(str, Enum):
    """Feed source format type."""

    RSS2 = "rss2"
    RSS1 = "rss1"
    RSS091 = "rss091"
    ATOM10 = "atom10"
    ATOM03 = "atom03"
    CONSTRUCTED = "constructed"


class SourceOrigin(str, Enum):
    """How the feed content was obtained."""

    URL = "url"
    FILE = "file"
    STRING = "string"
    TEMPLATE = "template"


class SourceInfo(BaseModel):
    """Source metadata for the feed response."""

    model_config = {"extra": "forbid"}

    type: SourceType
    url: str | None = None
    origin: SourceOrigin


class Enclosure(BaseModel):
    """Media enclosure attached to a feed item."""

    model_config = {"extra": "forbid"}

    url: str
    type: str = ""
    length: int | None = None


class FeedMeta(BaseModel):
    """Feed-level metadata."""

    model_config = {"extra": "forbid"}

    title: str = ""
    link: str = ""
    description: str = ""
    language: str = ""
    author: str = ""
    image: str = ""
    last_updated: str | None = None
    generator: str = ""
    categories: list[str] = Field(default_factory=list)
    ttl: int | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)


class FeedItem(BaseModel):
    """Individual feed entry/item."""

    model_config = {"extra": "forbid"}

    title: str = ""
    link: str = ""
    guid: str = ""
    guid_is_permalink: bool = Field(default=False, strict=True)
    pub_date: str | None = None
    updated: str | None = None
    author: str = ""
    description: str = ""
    content: str = ""
    thumbnail: str = ""
    enclosures: list[Enclosure] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    comments_url: str | None = None
    comments_count: int | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)


class FeedResponse(BaseModel):
    """Top-level response object — the root of all shruggie-feedtools output."""

    model_config = {"extra": "forbid"}

    status: Status
    message: str | None = None
    schema_version: str
    source: SourceInfo
    feed: FeedMeta = Field(default_factory=FeedMeta)
    items: list[FeedItem] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict, suitable for JSON output."""
        return self.model_dump(mode="python")

    def to_json(self, *, indent: int | None = None, sort_keys: bool = False) -> str:
        """Serialize to a JSON string."""
        import json

        data = self.model_dump(mode="python")
        # Convert enums to their values for clean JSON
        return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
