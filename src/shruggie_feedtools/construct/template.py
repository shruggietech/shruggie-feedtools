"""Template loading and validation.

Pydantic models for ``.feedtemplate.json`` files. Templates are validated on load
with ``extra = "forbid"`` on all models to reject unknown fields.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("shruggie_feedtools")


class TemplateValidationError(Exception):
    """Raised when a template fails Pydantic validation or structural checks."""


# ---------------------------------------------------------------------------
# Enums for constrained strategy fields
# ---------------------------------------------------------------------------


class TextTarget(str, Enum):
    """Allowed values for ``item_mapping.text_target``."""

    CONTENT = "content"
    DESCRIPTION = "description"
    BOTH = "both"


class TitleStrategy(str, Enum):
    """Allowed values for ``item_mapping.title_strategy``."""

    FIRST_LINE = "first_line"
    TRUNCATE = "truncate"
    TIMESTAMP = "timestamp"
    TEMPLATE = "template"
    NONE = "none"


class DescriptionStrategy(str, Enum):
    """Allowed values for ``item_mapping.description_strategy``."""

    TRUNCATE = "truncate"
    FIRST_LINE = "first_line"
    SAME = "same"
    NONE = "none"


class GuidStrategy(str, Enum):
    """Allowed values for ``item_mapping.guid_strategy``."""

    SHA256 = "sha256"
    UUID4 = "uuid4"
    TIMESTAMP = "timestamp"
    SEQUENTIAL = "sequential"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FeedSection(BaseModel):
    """Feed-level metadata from the template."""

    model_config = {"extra": "forbid"}

    title: str
    link: str = ""
    description: str = ""
    language: str = ""
    author: str = ""
    image: str = ""
    categories: list[str] = Field(default_factory=list)
    ttl: int | None = None


class ItemMapping(BaseModel):
    """Controls how text + timestamp are transformed into item fields."""

    model_config = {"extra": "forbid"}

    text_target: TextTarget = TextTarget.CONTENT
    title_strategy: TitleStrategy = TitleStrategy.FIRST_LINE
    title_max_length: int = 120
    description_strategy: DescriptionStrategy = DescriptionStrategy.TRUNCATE
    description_max_length: int = 280
    guid_strategy: GuidStrategy = GuidStrategy.SHA256
    link_pattern: str | None = None

    @field_validator("title_max_length")
    @classmethod
    def _title_max_length_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("title_max_length must be a positive integer")
        return v

    @field_validator("description_max_length")
    @classmethod
    def _description_max_length_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("description_max_length must be a positive integer")
        return v


class ItemDefaults(BaseModel):
    """Static default values applied to every constructed item."""

    model_config = {"extra": "forbid"}

    author: str = ""
    categories: list[str] = Field(default_factory=list)
    thumbnail: str = ""
    link: str = ""
    extensions: dict[str, Any] = Field(default_factory=dict)
    title_template: str | None = None


class FeedTemplate(BaseModel):
    """Root model for a ``.feedtemplate.json`` file."""

    model_config = {"extra": "forbid"}

    template_version: str
    feed: FeedSection
    item_mapping: ItemMapping
    item_defaults: ItemDefaults = Field(default_factory=ItemDefaults)

    @model_validator(mode="after")
    def _check_version(self) -> FeedTemplate:
        if self.template_version != "1.0":
            raise ValueError(
                f"Unsupported template_version: {self.template_version!r}. "
                "Only '1.0' is supported."
            )
        return self


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

_template_cache: dict[str, FeedTemplate] = {}


def load_template(path_or_dict: str | Path | dict[str, Any]) -> FeedTemplate:
    """Load and validate a feed template.

    Parameters
    ----------
    path_or_dict:
        A filesystem path to a ``.feedtemplate.json`` file, or a Python dict
        with the same structure.

    Returns
    -------
    FeedTemplate
        Validated template model.

    Raises
    ------
    TemplateValidationError
        If the template fails validation.
    FileNotFoundError
        If *path_or_dict* is a path that does not exist.
    """
    if isinstance(path_or_dict, dict):
        return _validate_template(path_or_dict)

    path = Path(path_or_dict)

    # Check cache
    cache_key = str(path.resolve())
    if cache_key in _template_cache:
        return _template_cache[cache_key]

    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TemplateValidationError(
            f"Invalid JSON in template file {path}: {exc}"
        ) from exc

    template = _validate_template(data)
    _template_cache[cache_key] = template
    return template


def _validate_template(data: dict[str, Any]) -> FeedTemplate:
    """Validate a template dict against the Pydantic model."""
    try:
        return FeedTemplate.model_validate(data)
    except Exception as exc:
        raise TemplateValidationError(str(exc)) from exc
