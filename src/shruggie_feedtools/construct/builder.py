"""Feed construction builder.

Assembles feed metadata from a template and applies strategy derivations per
item.  The output is a schema-compliant dict validated through the Pydantic
models in ``core.schema``.
"""

from __future__ import annotations

from typing import Any

from shruggie_feedtools._version import __version__
from shruggie_feedtools.construct.strategies import (
    derive_description,
    derive_title,
    generate_guid,
    generate_link,
)
from shruggie_feedtools.construct.template import FeedTemplate, TextTarget
from shruggie_feedtools.core.dates import normalize_date
from shruggie_feedtools.core.schema import (
    FeedItem,
    FeedMeta,
    FeedResponse,
    SourceInfo,
    SourceOrigin,
    SourceType,
    Status,
)

logger = __import__("logging").getLogger("shruggie_feedtools")

GENERATOR = f"shruggie-feedtools/{__version__}"


def build_feed(entries: list[dict[str, Any]], template: FeedTemplate) -> dict[str, Any]:
    """Build a schema-compliant feed from entries and a validated template.

    Parameters
    ----------
    entries:
        List of entry dicts, each with at least ``text`` and ``timestamp``.
        May also contain per-entry overrides (``title``, ``author``,
        ``categories``, ``link``, etc.).
    template:
        Validated :class:`FeedTemplate` instance.

    Returns
    -------
    dict
        Full schema-compliant output dict (same shape as parse mode output).
    """
    mapping = template.item_mapping
    defaults = template.item_defaults

    batch_size = len(entries)
    items: list[FeedItem] = []
    logger.debug("build_feed: building %d items from template '%s'",
                 batch_size, template.feed.title)

    for idx, entry in enumerate(entries, start=1):
        text: str = entry.get("text", "")
        raw_timestamp = entry.get("timestamp", "")
        pub_date = normalize_date(raw_timestamp)

        # Normalize timestamp for strategy use (fallback to raw if normalize fails)
        ts_for_strategy = pub_date or str(raw_timestamp)

        # --- Derive title -------------------------------------------------
        if "title" in entry:
            # Per-entry override takes precedence
            title = entry["title"]
        else:
            title = derive_title(
                text=text,
                strategy=mapping.title_strategy.value,
                max_length=mapping.title_max_length,
                timestamp=ts_for_strategy,
                index=idx,
                title_template=defaults.title_template,
            )

        # --- Derive GUID --------------------------------------------------
        guid = generate_guid(
            text=text,
            timestamp=ts_for_strategy,
            strategy=mapping.guid_strategy.value,
            feed_title=template.feed.title,
            index=idx,
            batch_size=batch_size,
        )

        # --- Derive content / description ---------------------------------
        text_target = mapping.text_target

        if text_target == TextTarget.CONTENT:
            content = text
            description = derive_description(
                text=text,
                strategy=mapping.description_strategy.value,
                max_length=mapping.description_max_length,
            )
        elif text_target == TextTarget.DESCRIPTION:
            content = ""
            description = text
        else:
            # "both"
            content = text
            description = derive_description(
                text=text,
                strategy=mapping.description_strategy.value,
                max_length=mapping.description_max_length,
            )

        # --- Derive link --------------------------------------------------
        if mapping.link_pattern:
            link = generate_link(mapping.link_pattern, guid)
        elif "link" in entry:
            link = entry["link"]
        elif defaults.link:
            link = defaults.link
        else:
            link = ""

        # --- Merge per-entry overrides with defaults ----------------------
        # Precedence: per-entry override > item_defaults > schema default
        author = entry.get("author", defaults.author)
        categories = entry.get("categories", list(defaults.categories))
        thumbnail = entry.get("thumbnail", defaults.thumbnail)
        extensions = entry.get("extensions", dict(defaults.extensions))

        item = FeedItem(
            title=title,
            link=link,
            guid=guid,
            guid_is_permalink=False,
            pub_date=pub_date,
            updated=None,
            author=author,
            description=description,
            content=content,
            thumbnail=thumbnail,
            enclosures=[],
            categories=categories,
            comments_url=None,
            comments_count=None,
            extensions=extensions,
        )
        items.append(item)

    # --- Feed metadata --------------------------------------------------------
    # Compute last_updated as the latest pub_date
    pub_dates = [item.pub_date for item in items if item.pub_date]
    last_updated = max(pub_dates) if pub_dates else None

    feed_meta = FeedMeta(
        title=template.feed.title,
        link=template.feed.link,
        description=template.feed.description,
        language=template.feed.language,
        author=template.feed.author,
        image=template.feed.image,
        last_updated=last_updated,
        generator=GENERATOR,
        categories=list(template.feed.categories),
        ttl=template.feed.ttl,
        extensions={},
    )

    source = SourceInfo(
        type=SourceType.CONSTRUCTED,
        url=None,
        origin=SourceOrigin.TEMPLATE,
    )

    response = FeedResponse(
        status=Status.OK,
        schema_version="1.0",
        source=source,
        feed=feed_meta,
        items=items,
    )

    return response.to_dict()
