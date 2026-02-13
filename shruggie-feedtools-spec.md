# shruggie-feedtools — Technical Specification

**Project:** `shruggie-feedtools`
**Repository:** [shruggietech/shruggie-feedtools](https://github.com/shruggietech/shruggie-feedtools)
**License:** Apache 2.0 ([full text](https://www.apache.org/licenses/LICENSE-2.0))
**Version:** 0.1.0 (MVP)
**Author:** William Thompson / ShruggieTech LLC
**Date:** 2026-02-11
**Status:** DRAFT

---

## 1. Executive Summary

`shruggie-feedtools` is a Python module that normalizes web feed data from diverse sources — RSS, Atom, JSON Feed, WordPress REST API, and other time-sequenced web endpoints — into a single, predictable JSON schema. It also constructs schema-compliant feed output from arbitrary text input using template files. It ships as a CLI tool and a standalone Windows GUI application, distributed as pre-built executables via GitHub Releases. The module is designed from the ground up for eventual integration as a backend for an HTTP API service.

### 1.1 Branding Context

`shruggie-feedtools` lives under the **ShruggieTech LLC** open source umbrella. All ShruggieTech open source tools share the `shruggie-` prefix for namespace consistency. Future closed-source products will have their own distinct brands.

| Surface | Value |
|---------|-------|
| Import name | `shruggie_feedtools` |
| CLI command | `shruggie-feedtools` |
| GitHub repo | `shruggietech/shruggie-feedtools` |
| GUI window title | `Shruggie FeedTools` |
| User-Agent | `shruggie-feedtools/0.1.0` |
| License | Apache 2.0 |

### 1.2 Core Capabilities

The tool has two primary modes of operation:

1. **Parse mode** — Ingest feeds from URLs, files, or raw strings across multiple formats (RSS, Atom, JSON Feed, WordPress REST) and normalize them into a single predictable JSON schema.

2. **Construct mode** — Take raw text content, a timestamp, and a template file, and produce schema-compliant JSON feed output. This enables users to create feeds from arbitrary data sources that don't natively expose a feed format.

Both modes produce output conforming to the same versioned schema (§3), which means parsed feeds and constructed feeds are interchangeable downstream.

### 1.3 How We Differ from macieklamberski/feedsmith (JS)

The JS feedsmith preserves original per-format structure. We take the opposite stance: **normalization is the point.** We handle the information-loss concern through the `extensions` bucket — first-class fields get normalized, everything else gets preserved verbatim under namespace-prefixed keys.

Additionally:
- **Language**: Python (they're JavaScript/TypeScript)
- **Scope**: HTTP fetching, batch processing, CLI, GUI, `.exe`, and template-based construction (they're a parsing library only)
- **JSON-native sources**: WordPress REST auto-detection (they parse strings only)
- **Construction**: They generate feeds from structured objects. We generate feeds from raw text + templates — a different problem entirely.

### 1.4 What We Borrowed from feedsmith (JS)

1. Format-specific parsers alongside universal parser
2. Namespace prefix normalization (arbitrary prefixes → canonical ones via URI)
3. Namespace URI tolerance (HTTPS variants, case, trailing slashes)
4. Case-insensitive element handling
5. Per-format test fixture organization

### 1.5 What Counts as a "Feed"

Any publicly accessible endpoint returning **time-ordered entries** with at minimum a title/identifier and a timestamp:

| Source Category | Examples | How It Arrives |
|----------------|----------|----------------|
| News / Blog RSS | WordPress, Blogger, Ghost, Hugo, Medium, Substack | RSS 2.0, Atom 1.0 |
| Podcast feeds | Apple Podcasts, Spotify-submitted, self-hosted | RSS 2.0 + iTunes namespace |
| Video channel updates | YouTube channels, Vimeo channels | Atom 1.0 |
| Code repository releases | GitHub Releases, GitLab Releases | Atom 1.0 |
| Package registry updates | PyPI, npm, crates.io | RSS 2.0 / Atom |
| Service status pages | Statuspage.io, UptimeRobot | Atom 1.0 / RSS 2.0 |
| Financial / market feeds | SEC EDGAR, Yahoo Finance | RSS 2.0, Atom |
| Government / regulatory | Federal Register, .gov portals | RSS 1.0 (RDF), RSS 2.0, Atom |
| CMS REST APIs | WordPress `/wp-json/wp/v2/posts` | JSON (auto-detected) |
| JSON Feed sites | `jsonfeed.org` spec implementors | JSON Feed 1.0 / 1.1 |
| Reddit / forums | Subreddit `.rss`, Discourse | RSS 2.0 with Media RSS |
| **Custom / constructed** | **Any text source + template** | **Template-based construction** |

### 1.6 Non-Goals (MVP)

- Full feed reader / aggregator
- Feed discovery (auto-detecting feed URLs from arbitrary pages)
- Feed caching, polling, or scheduling
- Database persistence
- User accounts or authentication
- Webhooks or push notifications
- Scraping endpoints without structured feed formats
- Proprietary API integrations requiring auth (Twitter/X, etc.)

---

## 2. Supported Input Formats

### 2.1 XML Feed Formats

| Format | Priority | Notes |
|--------|----------|-------|
| RSS 2.0 | **P0** | Dominant format. WordPress, Blogger, most CMS. |
| Atom 1.0 | **P0** | Google services, GitHub, YouTube, modern feeds. |
| RSS 1.0 (RDF) | **P1** | Government/academic feeds. |
| RSS 0.91/0.92 | **P2** | Legacy. `feedparser` handles transparently. |
| Atom 0.3 | **P2** | Rare. `feedparser` handles transparently. |

### 2.2 JSON-Native Sources

| Source | Priority | Detection Method |
|--------|----------|-----------------|
| WordPress REST API | **P0** | URL pattern + JSON structure sniffing |
| JSON Feed 1.0/1.1 | **P1** | `version` field containing `jsonfeed.org` URL |

### 2.3 Template-Based Construction

| Input | Priority | Description |
|-------|----------|-------------|
| Text + timestamp + template file | **P0** | See §5 for full specification |

### 2.4 Namespace Extensions (Within XML Feeds)

| Namespace | Prefix | Common Sources |
|-----------|--------|----------------|
| Dublin Core | `dc:` | WordPress, most CMS |
| Content Module | `content:` | WordPress, Blogger |
| Media RSS | `media:` | Reddit, YouTube, media sites |
| Slash | `slash:` | WordPress |
| iTunes | `itunes:` | Podcast feeds |
| Syndication | `sy:` | Various CMS |
| YouTube | `yt:` | YouTube Atom feeds |
| GeoRSS | `georss:` | Location-aware feeds |
| Podcast Index | `podcast:` | Modern podcasts |

**Namespace prefix normalization**: Custom prefixes are resolved to canonical ones via URI lookup (e.g., `<custom:creator>` with Dublin Core namespace URI → `dc:creator` in output).

---

## 3. Output Schema

The JSON output schema is the contract. Parse mode and construct mode both produce this exact structure. It must be stable, versioned, and documented.

### 3.1 Top-Level Response Object

```json
{
  "status": "ok",
  "schema_version": "1.0",
  "source": {
    "type": "rss2",
    "url": "https://example.com/feed.xml",
    "origin": "url"
  },
  "feed": { },
  "items": [ ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | `string` | Yes | `"ok"` or `"error"` |
| `message` | `string` | No | Human-readable error (present when `status` is `"error"`) |
| `schema_version` | `string` | Yes | Output schema version. `"1.0"` for MVP. |
| `source.type` | `string` | Yes | `"rss2"`, `"rss1"`, `"rss091"`, `"atom10"`, `"atom03"`, `"json_feed"`, `"wp_rest"`, `"constructed"` |
| `source.url` | `string\|null` | Yes | Original URL if fetched; `null` for files/strings/constructed |
| `source.origin` | `string` | Yes | `"url"`, `"file"`, `"string"`, `"template"` |
| `feed` | `object` | Yes | Feed-level metadata (§3.2) |
| `items` | `array` | Yes | Array of item objects (§3.3) |

### 3.2 Feed Metadata Object

```json
{
  "title": "Hacker News",
  "link": "https://news.ycombinator.com/",
  "description": "Links for the intellectually curious, ranked by readers.",
  "language": "en-us",
  "author": "",
  "image": "https://example.com/logo.png",
  "last_updated": "2026-02-09T12:00:00Z",
  "generator": "WordPress 6.7",
  "categories": ["Technology", "News"],
  "ttl": 60,
  "extensions": {}
}
```

| Field | Type | Default | Source Mapping |
|-------|------|---------|---------------|
| `title` | `string` | `""` | `<title>`, `feed.title`, or template `feed.title` |
| `link` | `string` | `""` | `<link>`, `feed.link[rel=alternate]`, or template |
| `description` | `string` | `""` | `<description>`, `feed.subtitle`, or template |
| `language` | `string` | `""` | `<language>`, `xml:lang`, or template |
| `author` | `string` | `""` | `<managingEditor>`, `feed.author.name`, or template |
| `image` | `string` | `""` | `<image><url>`, `feed.logo`, or template |
| `last_updated` | `string\|null` | `null` | ISO 8601 UTC. Computed as latest `pub_date` in construct mode. |
| `generator` | `string` | `""` | `<generator>`. Always `"shruggie-feedtools/0.1.0"` in construct mode. |
| `categories` | `array[string]` | `[]` | `<category>` elements, or template |
| `ttl` | `int\|null` | `null` | `<ttl>` (minutes), or template |
| `extensions` | `object` | `{}` | Namespace-prefixed overflow bucket (§3.4) |

### 3.3 Item Object

```json
{
  "title": "Article Title",
  "link": "https://example.com/article",
  "guid": "https://example.com/article",
  "guid_is_permalink": true,
  "pub_date": "2026-02-09T08:30:00Z",
  "updated": null,
  "author": "John Doe",
  "description": "Short summary or excerpt...",
  "content": "Full HTML content...",
  "thumbnail": "https://example.com/thumb.jpg",
  "enclosures": [
    {
      "url": "https://example.com/podcast.mp3",
      "type": "audio/mpeg",
      "length": 12345678
    }
  ],
  "categories": ["Tech", "Python"],
  "comments_url": null,
  "comments_count": null,
  "extensions": {}
}
```

| Field | Type | Default | Source |
|-------|------|---------|--------|
| `title` | `string` | `""` | Parsed from feed, or derived from text input in construct mode |
| `link` | `string` | `""` | Parsed, or template `item_defaults.link` pattern |
| `guid` | `string` | `""` | Parsed, or auto-generated in construct mode |
| `guid_is_permalink` | `bool` | `false` | Parsed, or `false` in construct mode |
| `pub_date` | `string\|null` | `null` | ISO 8601 UTC. Parsed, or from timestamp input |
| `updated` | `string\|null` | `null` | Parsed, or `null` in construct mode |
| `author` | `string` | `""` | Parsed, or template `item_defaults.author` |
| `description` | `string` | `""` | Parsed, or derived from text input |
| `content` | `string` | `""` | Parsed, or text input verbatim |
| `thumbnail` | `string` | `""` | Parsed, or template `item_defaults.thumbnail` |
| `enclosures` | `array[object]` | `[]` | Parsed, or `[]` in construct mode |
| `categories` | `array[string]` | `[]` | Parsed, or template `item_defaults.categories` |
| `comments_url` | `string\|null` | `null` | Parsed, or `null` |
| `comments_count` | `int\|null` | `null` | Parsed, or `null` |
| `extensions` | `object` | `{}` | Parsed namespaces, or template `item_defaults.extensions` |

### 3.4 Extensions Object

Namespace-prefixed overflow bucket, keyed by **normalized** prefix:

```json
{
  "extensions": {
    "itunes": {
      "duration": "01:23:45",
      "explicit": "no",
      "image": "https://example.com/podcast-art.jpg"
    },
    "yt": {
      "videoId": "dQw4w9WgXcQ",
      "channelId": "UC..."
    }
  }
}
```

Prefix normalization: even if a feed declares `xmlns:custom="http://purl.org/dc/elements/1.1/"`, the data appears under the `dc` key — never under `custom`.

### 3.5 Date Handling

All dates in output are **ISO 8601 in UTC** (`YYYY-MM-DDTHH:MM:SSZ`).

Accepted input formats:
- RFC 822 / RFC 2822 (`Thu, 09 Feb 2026 12:00:00 GMT`)
- ISO 8601 (`2026-02-09T12:00:00Z`, `2026-02-09T12:00:00+05:00`)
- Loose formats (`February 9, 2026`, `2026-02-09`)
- WordPress REST (`2026-02-09T12:00:00`) — naive datetime, assumed UTC
- Unix epoch (integer or float) — supported in construct mode

Unparseable dates → `null` + warning log. Never crash on a bad date.

---

## 4. Parse Mode — Public API

### 4.1 Universal Parser (Auto-Detect)

```python
from shruggie_feedtools import parse, parse_url, parse_file, parse_string

# From URL (fetches, detects format, parses, normalizes)
result = parse_url("https://news.ycombinator.com/rss")

# From local file
result = parse_file("/path/to/feed.xml")

# From raw content string
result = parse_string(xml_or_json_content, source_url="https://example.com/feed")

# Convenience alias — accepts URL, file path, or raw content (sniffs which)
result = parse("https://news.ycombinator.com/rss")
```

### 4.2 Format-Specific Parsers

```python
from shruggie_feedtools.adapters import (
    parse_rss, parse_atom, parse_rdf, parse_json_feed, parse_wp_rest
)

result = parse_rss(rss_xml_string)
result = parse_atom(atom_xml_string)
result = parse_rdf(rdf_xml_string)
result = parse_json_feed(json_feed_string)
result = parse_wp_rest(wp_json_string, base_url="https://example.com")
```

### 4.3 Batch Operations

```python
from shruggie_feedtools import parse_urls, parse_files

results = parse_urls(["https://a.com/rss", "https://b.com/feed"])
results = parse_files(["/path/to/a.xml", "/path/to/b.xml"])
```

### 4.4 Detection Utility

```python
from shruggie_feedtools.core.detector import detect_feed_type

feed_type = detect_feed_type(content_bytes)
# Returns: "rss2", "atom10", "rss1", "json_feed", "wp_rest", or None
```

---

## 5. Construct Mode — Template-Based Feed Construction

### 5.1 Overview

Construct mode enables creation of schema-compliant feed JSON from raw inputs that aren't feeds at all. The three required inputs are:

1. **Text** — A string of content (the "body" of the item)
2. **Timestamp** — When this entry occurred (any parseable date format or Unix epoch)
3. **Template** — A JSON file defining feed metadata, item defaults, and mapping rules

The output is a fully valid shruggie-feedtools schema object, indistinguishable in structure from parsed feed output. This means constructed feeds can be merged with parsed feeds, stored alongside them, and consumed by the same downstream code.

### 5.2 Template File Format

Templates are JSON files with the extension `.feedtemplate.json`. The format is intentionally close to the output schema so there's minimal cognitive overhead — if you understand the output, you understand the template.

```json
{
  "template_version": "1.0",

  "feed": {
    "title": "Server Incident Log",
    "link": "https://status.example.com",
    "description": "Automated incident reports from monitoring",
    "language": "en-us",
    "author": "ops-bot",
    "image": "",
    "categories": ["infrastructure", "monitoring"],
    "ttl": 15
  },

  "item_mapping": {
    "text_target": "content",
    "title_strategy": "first_line",
    "title_max_length": 120,
    "description_strategy": "truncate",
    "description_max_length": 280,
    "guid_strategy": "sha256"
  },

  "item_defaults": {
    "author": "ops-bot",
    "categories": ["incident"],
    "thumbnail": "",
    "link": "",
    "extensions": {}
  }
}
```

### 5.3 Template Field Reference

#### `template_version` (required)

```json
"template_version": "1.0"
```

Schema version of the template format itself. Always `"1.0"` for MVP. Allows future template format evolution without breaking existing templates.

#### `feed` (required)

Static feed-level metadata. Every field from the output schema's feed object (§3.2) is accepted here. These values are copied directly into the output `feed` object.

The `last_updated` field is **not set in the template** — it is computed automatically as the latest `pub_date` across all items in the constructed output. The `generator` field is always overwritten to `"shruggie-feedtools/0.1.0"` in construct mode.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | `string` | **Yes** | Feed title. The only strictly required feed field. |
| `link` | `string` | No | Feed home URL |
| `description` | `string` | No | Feed description |
| `language` | `string` | No | Language code (e.g., `"en-us"`) |
| `author` | `string` | No | Feed-level author |
| `image` | `string` | No | Feed logo/icon URL |
| `categories` | `array[string]` | No | Feed-level categories |
| `ttl` | `int\|null` | No | Suggested refresh interval (minutes) |

#### `item_mapping` (required)

Controls how the text input and timestamp are transformed into item fields.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `text_target` | `string` | `"content"` | Which item field the raw text is assigned to. One of: `"content"`, `"description"`, `"both"`. When `"both"`, text goes to `content` and a derived version goes to `description`. |
| `title_strategy` | `string` | `"first_line"` | How to derive the item `title` from the text input. See §5.4. |
| `title_max_length` | `int` | `120` | Maximum characters for auto-derived titles. Truncated with `…` if exceeded. |
| `description_strategy` | `string` | `"truncate"` | How to derive `description` when `text_target` is `"content"` or `"both"`. See §5.4. |
| `description_max_length` | `int` | `280` | Max characters for auto-derived descriptions. |
| `guid_strategy` | `string` | `"sha256"` | How to generate item GUIDs. See §5.5. |
| `link_pattern` | `string\|null` | `null` | Optional URL pattern with `{guid}` placeholder. E.g., `"https://example.com/entries/{guid}"`. If set, each item's `link` is generated from this pattern. |

#### `item_defaults` (optional)

Static default values applied to every constructed item. Any field from the item schema (§3.3) is accepted except `title`, `pub_date`, `guid`, `content`, and `description` (which are derived from inputs/mapping rules).

| Field | Type | Notes |
|-------|------|-------|
| `author` | `string` | Default item author |
| `categories` | `array[string]` | Default categories per item |
| `thumbnail` | `string` | Default thumbnail URL |
| `link` | `string` | Default link (overridden by `link_pattern` if set) |
| `extensions` | `object` | Static extension data to inject into every item |

### 5.4 Title and Description Derivation Strategies

#### Title Strategies

| Strategy | Behavior |
|----------|----------|
| `"first_line"` | Extract the first line of the text input (up to first `\n`). Truncate to `title_max_length`. |
| `"truncate"` | Take the first `title_max_length` characters of the full text, breaking at a word boundary. |
| `"timestamp"` | Use the formatted timestamp as the title (e.g., `"2026-02-10 08:30:00 UTC"`). |
| `"template"` | Use a static string from `item_defaults.title_template` with `{timestamp}` and `{index}` placeholders (e.g., `"Entry #{index} — {timestamp}"`). |
| `"none"` | Leave title as `""`. |

#### Description Strategies

| Strategy | Behavior |
|----------|----------|
| `"truncate"` | First `description_max_length` characters of the text, word-boundary break, `…` suffix. |
| `"first_line"` | First line of the text input. |
| `"same"` | Description equals the full text (mirrors `content`). |
| `"none"` | Leave description as `""`. |

### 5.5 GUID Generation Strategies

| Strategy | Output | Deterministic? |
|----------|--------|----------------|
| `"sha256"` | `sha256(text + timestamp)` hex digest | Yes — same input always produces same GUID |
| `"uuid4"` | Random UUID v4 | No — unique each time |
| `"timestamp"` | ISO 8601 timestamp string as GUID | Yes, but not unique if multiple items share a timestamp |
| `"sequential"` | `"{feed_title_slug}-{index}"` (e.g., `"server-incident-log-001"`) | Yes within a batch |

The `"sha256"` default is chosen because it provides content-addressable deduplication: feeding the same text+timestamp through the same template always produces the same GUID, which makes idempotent feed construction possible.

### 5.6 Construct Mode — Python API

```python
from shruggie_feedtools import construct, construct_batch
from shruggie_feedtools.construct import load_template

# Load a template once, reuse for multiple operations
template = load_template("/path/to/my.feedtemplate.json")

# Construct a single-item feed
result = construct(
    text="Server web-03 is experiencing elevated latency on port 443.",
    timestamp="2026-02-10T08:30:00Z",
    template=template
)
# Returns: full schema-compliant dict with one item in items[]

# Construct a multi-item feed from a list of entries
result = construct_batch(
    entries=[
        {"text": "Incident detected on web-03.", "timestamp": "2026-02-10T08:30:00Z"},
        {"text": "Incident escalated to P1.",     "timestamp": "2026-02-10T08:35:00Z"},
        {"text": "Incident resolved.",            "timestamp": "2026-02-10T09:15:00Z"},
    ],
    template=template
)
# Returns: full schema-compliant dict with three items in items[]

# Inline template (dict instead of file)
result = construct(
    text="Quick test entry.",
    timestamp="2026-02-10T12:00:00Z",
    template={
        "template_version": "1.0",
        "feed": {"title": "Test Feed"},
        "item_mapping": {"text_target": "content", "title_strategy": "first_line"},
    }
)
```

### 5.7 Construct Mode — CLI

```bash
# Single item from arguments
shruggie-feedtools construct \
    --template incident.feedtemplate.json \
    --text "Server web-03 is experiencing elevated latency." \
    --timestamp "2026-02-10T08:30:00Z"

# Single item, text from stdin (pipe-friendly)
echo "Server web-03 is down." | shruggie-feedtools construct \
    --template incident.feedtemplate.json \
    --timestamp "2026-02-10T08:30:00Z" \
    --text-stdin

# Batch from a JSONL file (one JSON object per line)
shruggie-feedtools construct \
    --template incident.feedtemplate.json \
    --entries incidents.jsonl

# Batch from stdin JSONL
cat incidents.jsonl | shruggie-feedtools construct \
    --template incident.feedtemplate.json \
    --entries-stdin

# Output to file
shruggie-feedtools construct \
    --template incident.feedtemplate.json \
    --entries incidents.jsonl \
    --output constructed_feed.json \
    --pretty
```

### 5.8 JSONL Entry Format (Batch Input)

For batch construction, entries are provided as JSONL (one JSON object per line):

```jsonl
{"text": "Incident detected on web-03.", "timestamp": "2026-02-10T08:30:00Z"}
{"text": "Incident escalated to P1.", "timestamp": "2026-02-10T08:35:00Z"}
{"text": "Incident resolved. Root cause: expired TLS cert.", "timestamp": "2026-02-10T09:15:00Z"}
```

Each line must have at minimum `text` and `timestamp`. Optional per-entry overrides:

```jsonl
{"text": "Custom titled entry.", "timestamp": "2026-02-10T08:30:00Z", "title": "Override Title", "author": "jdoe", "categories": ["custom"]}
```

Per-entry overrides take precedence over template `item_defaults`, which take precedence over empty-string defaults.

### 5.9 Template Validation

Templates are validated on load via Pydantic. Invalid templates produce clear error messages:

```python
template = load_template("bad_template.json")
# Raises: TemplateValidationError("feed.title is required")
# Raises: TemplateValidationError("item_mapping.guid_strategy must be one of: sha256, uuid4, timestamp, sequential")
```

The CLI validates templates before processing any entries and exits with code `2` on template errors.

### 5.10 Constructed Output Example

Given this template (`changelog.feedtemplate.json`):

```json
{
  "template_version": "1.0",
  "feed": {
    "title": "Project Changelog",
    "link": "https://github.com/shruggietech/project",
    "description": "Development changelog entries",
    "language": "en-us"
  },
  "item_mapping": {
    "text_target": "content",
    "title_strategy": "first_line",
    "title_max_length": 80,
    "description_strategy": "truncate",
    "description_max_length": 200,
    "guid_strategy": "sha256",
    "link_pattern": "https://github.com/shruggietech/project/entries/{guid}"
  },
  "item_defaults": {
    "author": "wthompson",
    "categories": ["changelog", "dev"]
  }
}
```

And this input:

```bash
shruggie-feedtools construct \
    --template changelog.feedtemplate.json \
    --text "Refactored the adapter pipeline\nSplit feedparser_adapter into per-format modules for clarity." \
    --timestamp "2026-02-10T14:00:00Z" \
    --pretty
```

Output:

```json
{
  "status": "ok",
  "schema_version": "1.0",
  "source": {
    "type": "constructed",
    "url": null,
    "origin": "template"
  },
  "feed": {
    "title": "Project Changelog",
    "link": "https://github.com/shruggietech/project",
    "description": "Development changelog entries",
    "language": "en-us",
    "author": "",
    "image": "",
    "last_updated": "2026-02-10T14:00:00Z",
    "generator": "shruggie-feedtools/0.1.0",
    "categories": [],
    "ttl": null,
    "extensions": {}
  },
  "items": [
    {
      "title": "Refactored the adapter pipeline",
      "link": "https://github.com/shruggietech/project/entries/a3f8c9...",
      "guid": "a3f8c9d2e7b1...",
      "guid_is_permalink": false,
      "pub_date": "2026-02-10T14:00:00Z",
      "updated": null,
      "author": "wthompson",
      "description": "Refactored the adapter pipeline Split feedparser_adapter into per-format modules for clarity.",
      "content": "Refactored the adapter pipeline\nSplit feedparser_adapter into per-format modules for clarity.",
      "thumbnail": "",
      "enclosures": [],
      "categories": ["changelog", "dev"],
      "comments_url": null,
      "comments_count": null,
      "extensions": {}
    }
  ]
}
```

---

## 6. Architecture

### 6.1 Package Structure

```
shruggie-feedtools/
├── pyproject.toml
├── README.md
├── LICENSE                         # Apache 2.0
├── .github/
│   └── workflows/
│       └── release.yml             # GitHub Actions release pipeline (§13)
├── scripts/
│   ├── venv-setup.ps1              # Windows: venv check + create
│   ├── venv-setup.sh               # Linux/macOS: venv check + create
│   ├── build.ps1                   # Windows: PyInstaller build
│   ├── build.sh                    # Linux/macOS: PyInstaller build
│   ├── test.ps1                    # Windows: test runner
│   └── test.sh                     # Linux/macOS: test runner
├── src/
│   └── shruggie_feedtools/
│       ├── __init__.py             # Public API: parse, parse_url, construct, etc.
│       ├── __main__.py             # CLI entry (python -m shruggie_feedtools)
│       ├── _version.py             # Single source of truth: __version__ = "0.1.0"
│       ├── core/
│       │   ├── __init__.py
│       │   ├── parser.py           # Parse orchestrator (detect → adapt → normalize)
│       │   ├── normalizer.py       # Adapter output → schema mapping
│       │   ├── schema.py           # Pydantic models for output schema
│       │   ├── dates.py            # Date parsing & normalization
│       │   ├── fetcher.py          # HTTP client (httpx)
│       │   ├── detector.py         # Feed type auto-detection
│       │   └── namespaces.py       # Namespace URI → prefix normalization
│       ├── adapters/
│       │   ├── __init__.py         # Exports: parse_rss, parse_atom, etc.
│       │   ├── feedparser_adapter.py
│       │   ├── wp_rest_adapter.py
│       │   └── json_feed_adapter.py
│       ├── construct/
│       │   ├── __init__.py         # Exports: construct, construct_batch, load_template
│       │   ├── builder.py          # Core construction logic
│       │   ├── template.py         # Template loading, validation, Pydantic models
│       │   ├── strategies.py       # Title, description, GUID derivation strategies
│       │   └── entry.py            # Entry parsing (JSONL, per-entry overrides)
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py             # argparse CLI (parse + construct subcommands)
│       ├── gui/
│       │   ├── __init__.py
│       │   └── app.py              # CustomTkinter GUI
│       └── utils/
│           ├── __init__.py
│           ├── html.py             # HTML utilities (thumbnail extraction)
│           └── logging.py          # Structured logging
├── tests/
│   ├── conftest.py                 # Shared fixtures, helpers
│   ├── fixtures/                   # Test data organized per-format
│   │   ├── rss2/
│   │   │   ├── minimal.xml
│   │   │   ├── wordpress.xml
│   │   │   ├── podcast_itunes.xml
│   │   │   ├── hairy_malformed.xml
│   │   │   ├── financial_sec.xml
│   │   │   └── reddit.xml
│   │   ├── atom10/
│   │   │   ├── github_releases.xml
│   │   │   ├── youtube_channel.xml
│   │   │   └── statuspage.xml
│   │   ├── rss1/
│   │   │   └── rdf_gov.xml
│   │   ├── json_feed/
│   │   │   └── v1_standard.json
│   │   ├── wp_rest/
│   │   │   └── posts_embedded.json
│   │   ├── templates/
│   │   │   ├── minimal.feedtemplate.json
│   │   │   ├── incident_log.feedtemplate.json
│   │   │   ├── changelog.feedtemplate.json
│   │   │   ├── all_strategies.feedtemplate.json
│   │   │   └── invalid_missing_title.feedtemplate.json
│   │   ├── entries/
│   │   │   ├── single_entry.jsonl
│   │   │   ├── batch_entries.jsonl
│   │   │   └── entries_with_overrides.jsonl
│   │   └── edge_cases/
│   │       ├── mixed_case_elements.xml
│   │       ├── custom_namespace_prefixes.xml
│   │       ├── bad_dates.xml
│   │       ├── missing_fields.xml
│   │       └── encoding_utf8_bom.xml
│   ├── snapshots/                  # Golden file expected outputs per fixture
│   │   ├── rss2/
│   │   ├── atom10/
│   │   ├── construct/
│   │   └── ...
│   ├── test_parser.py
│   ├── test_normalizer.py
│   ├── test_schema.py
│   ├── test_dates.py
│   ├── test_detector.py
│   ├── test_namespaces.py
│   ├── test_adapters.py
│   ├── test_fetcher.py
│   ├── test_construct.py
│   ├── test_template.py
│   ├── test_strategies.py
│   └── test_cli.py
└── dist/
    └── release/                    # Pre-built release assets (§13)
```

### 6.2 Data Flow — Parse Mode

```
Input (URL / File / String)
    │
    ▼
┌───────────────────────────┐
│  fetcher.py               │  ← HTTP GET / file read
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  detector.py              │  ← XML vs JSON → specific format
│  (skipped if format-      │
│   specific parser called) │
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  adapter (auto-selected)  │  ← Format-specific parsing → intermediate dict
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  namespaces.py            │  ← Custom prefixes → canonical prefixes
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  normalizer.py            │  ← Intermediate → output schema fields
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  schema.py (Pydantic)     │  ← Validate & serialize
└───────────────────────────┘
    │
    ▼
Output (schema-compliant dict/JSON)
```

### 6.3 Data Flow — Construct Mode

```
Inputs: text + timestamp + template
    │
    ▼
┌───────────────────────────┐
│  template.py              │  ← Load & validate template (Pydantic).
│  (load + validate)        │     Cache if reused across calls.
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  entry.py                 │  ← Parse JSONL entries (batch) or accept
│  (entry parsing)          │     text+timestamp args (single).
│                           │     Apply per-entry overrides.
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  strategies.py            │  ← Derive title (first_line, truncate, etc.)
│  (derivation logic)       │     Derive description (truncate, first_line, etc.)
│                           │     Generate GUID (sha256, uuid4, etc.)
│                           │     Generate link from pattern
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  builder.py               │  ← Assemble feed metadata from template.
│  (assembly)               │     Assemble items from derived fields +
│                           │     item_defaults + per-entry overrides.
│                           │     Compute last_updated. Set generator.
└───────────────────────────┘
    │
    ▼
┌───────────────────────────┐
│  schema.py (Pydantic)     │  ← Same validation as parse mode.
│                           │     Output is structurally identical.
└───────────────────────────┘
    │
    ▼
Output (schema-compliant dict/JSON)
```

### 6.4 Detection Pipeline (Parse Mode)

```
Raw bytes
    │
    ├─ Starts with '{' or '[' ────► JSON path
    │                                  ├─ "version" contains "jsonfeed.org"? → json_feed_adapter
    │                                  ├─ Has "title.rendered" + "_links"?   → wp_rest_adapter
    │                                  └─ Unknown                             → error
    │
    └─ Starts with '<' or BOM ────► XML path
                                       └─ feedparser → inspect result.version
                                            "rss20"  → feedparser_adapter (rss2)
                                            "atom10" → feedparser_adapter (atom10)
                                            "rss10"  → feedparser_adapter (rss1/rdf)
                                            etc.
```

### 6.5 Namespace Normalization

```python
# core/namespaces.py

NAMESPACE_MAP = {
    "http://purl.org/dc/elements/1.1/": "dc",
    "https://purl.org/dc/elements/1.1/": "dc",
    "http://purl.org/dc/terms/": "dcterms",
    "http://purl.org/rss/1.0/modules/content/": "content",
    "http://search.yahoo.com/mrss/": "media",
    "http://www.itunes.com/dtds/podcast-1.0.dtd": "itunes",
    "http://www.w3.org/2005/Atom": "atom",
    "http://purl.org/rss/1.0/modules/syndication/": "sy",
    "http://purl.org/rss/1.0/modules/slash/": "slash",
    "http://www.youtube.com/xml/schemas/2015": "yt",
    "http://www.georss.org/georss": "georss",
    "https://podcastindex.org/namespace/1.0": "podcast",
    # ... additional mappings
}

def normalize_prefix(uri: str, declared_prefix: str) -> str:
    """Map namespace URI to canonical prefix. Falls back to declared prefix if unknown."""
    normalized = uri.rstrip("/").lower()
    for known_uri, canonical in NAMESPACE_MAP.items():
        if normalized == known_uri.rstrip("/").lower():
            return canonical
    return declared_prefix
```

---

## 7. CLI Interface

The CLI uses subcommands to separate parse and construct modes.

### 7.1 Parse Subcommand

```
shruggie-feedtools parse [MODE] [OPTIONS]

Modes (mutually exclusive):
  --url URL                 Parse a single remote feed URL
  --url-list FILE           Parse URLs from a file (one per line)
  --file FILE               Parse a single local file
  --files FILE [FILE ...]   Parse multiple local files
  --dir DIRECTORY           Parse all feed files in a directory
  --stdin                   Read URLs from stdin

Output:
  --output FILE             Write JSON to file (default: stdout)
  --output-dir DIR          For batch: individual .json files
  --pretty                  Pretty-print JSON (default: minified)
  --indent N                Indentation level (default: 2)
  --quiet                   Suppress logs; only emit JSON

Behavior:
  --timeout SECONDS         HTTP timeout (default: 30)
  --user-agent STRING       Custom User-Agent header
  --no-verify-ssl           Disable SSL verification
  --max-items N             Limit items per feed
```

### 7.2 Construct Subcommand

```
shruggie-feedtools construct [OPTIONS]

Required:
  --template FILE           Path to .feedtemplate.json file

Input (one of):
  --text STRING             Text content for a single item
  --text-stdin              Read text from stdin (single item)
  --entries FILE            JSONL file with multiple entries
  --entries-stdin           Read JSONL entries from stdin

Timestamp (required for single-item modes):
  --timestamp STRING        Timestamp for the item (any parseable format)

Output:
  --output FILE             Write JSON to file (default: stdout)
  --pretty                  Pretty-print JSON
  --indent N                Indentation level (default: 2)
  --quiet                   Suppress logs; only emit JSON
```

### 7.3 Global Options

```
shruggie-feedtools --version     Print version and exit
shruggie-feedtools --help        Print help and exit
```

### 7.4 Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All operations succeeded |
| `1` | One or more feeds/entries failed to process |
| `2` | Argument error or template validation error |

### 7.5 Pipe Examples

```bash
# Parse: pipe URLs in, JSON out
echo "https://news.ycombinator.com/rss" | shruggie-feedtools parse --stdin --pretty

# Parse: chain with jq
shruggie-feedtools parse --url https://example.com/feed | jq '.items[].title'

# Construct: single item from piped text
echo "The server rebooted unexpectedly." | \
    shruggie-feedtools construct \
        --template incident.feedtemplate.json \
        --text-stdin \
        --timestamp "2026-02-10T03:00:00Z"

# Construct: batch from JSONL
cat events.jsonl | \
    shruggie-feedtools construct \
        --template changelog.feedtemplate.json \
        --entries-stdin \
        --pretty
```

---

## 8. Adapter Specifications

### 8.1 feedparser Adapter (XML Feeds)

Wraps `feedparser.parse()`. Handles RSS 2.0, 1.0/RDF, 0.9x, Atom 1.0, 0.3.

Responsibilities:
- `feedparser.parse()` on raw content bytes
- Extract `result.version` for `source.type`
- Map `result.feed` → intermediate dict
- Map `result.entries` → intermediate item list
- Namespace prefix normalization on all namespace-prefixed fields
- Handle `bozo` flag — log warning, continue

### 8.2 WordPress REST Adapter

Detection: valid JSON array with `title.rendered`, `content.rendered`, `_links`.

Auto-`_embed`: appends `?_embed` for inline author/category/media.

| Output Field | WP REST Source |
|-------------|---------------|
| `feed.title` | Site name from link relations or base URL |
| `feed.link` | Base URL (strip `/wp-json/...`) |
| `item.title` | `post.title.rendered` (decoded) |
| `item.link` | `post.link` |
| `item.guid` | `post.guid.rendered` |
| `item.pub_date` | `post.date_gmt` + `Z` |
| `item.updated` | `post.modified_gmt` + `Z` |
| `item.author` | `post._embedded.author[0].name` |
| `item.description` | `post.excerpt.rendered` |
| `item.content` | `post.content.rendered` |
| `item.thumbnail` | `post._embedded["wp:featuredmedia"][0].source_url` |
| `item.categories` | `post._embedded["wp:term"]` flattened |

Pagination: MVP processes first page. `X-WP-Total`/`X-WP-TotalPages` stored in `feed.extensions.wp`.

### 8.3 JSON Feed Adapter

Detection: JSON object with `version` containing `jsonfeed.org`.

| Output Field | JSON Feed Source |
|-------------|-----------------|
| `feed.title` | `title` |
| `feed.link` | `home_page_url` |
| `feed.description` | `description` |
| `feed.image` | `icon` or `favicon` |
| `feed.author` | `authors[0].name` (v1.1) or `author.name` (v1.0) |
| `item.title` | `items[].title` |
| `item.link` | `items[].url` |
| `item.guid` | `items[].id` |
| `item.pub_date` | `items[].date_published` |
| `item.updated` | `items[].date_modified` |
| `item.content` | `items[].content_html` or `items[].content_text` |
| `item.description` | `items[].summary` or truncated content |
| `item.thumbnail` | `items[].image` or `items[].banner_image` |
| `item.enclosures` | `items[].attachments[]` |
| `item.categories` | `items[].tags[]` |

---

## 9. Error Handling

### 9.1 Principles

- Never crash on bad feed data. Degrade gracefully.
- Errors in response dict (`"status": "error"`), not exceptions.
- Separate network, parse, and template errors.
- Log liberally at DEBUG.

### 9.2 Error Categories

| Category | Status | Behavior |
|----------|--------|----------|
| Network error (timeout, DNS, HTTP 4xx/5xx) | `"error"` | No parsing attempted. |
| Unparseable content (not XML, not JSON, empty) | `"error"` | Diagnostic message. |
| Partially malformed feed | `"ok"` | Parse what's possible. Defaults for missing fields. |
| Unrecognized JSON structure | `"error"` | "Does not match any known feed format." |
| Template validation failure | `"error"` | Specific field-level message. |
| Unparseable entry in JSONL | Per-item | Skip entry, log warning, continue batch. |

---

## 10. Dependencies

### 10.1 Core (Runtime)

| Package | Version | Purpose |
|---------|---------|---------|
| `feedparser` | `>=6.0` | XML feed parsing |
| `httpx` | `>=0.27` | HTTP client (async-capable) |
| `pydantic` | `>=2.0` | Schema validation & serialization |
| `python-dateutil` | `>=2.9` | Robust date parsing |

### 10.2 GUI

| Package | Version | Purpose |
|---------|---------|---------|
| `customtkinter` | `>=5.2` | Modern tkinter wrapper |

### 10.3 Build / Dev

| Package | Purpose |
|---------|---------|
| `pyinstaller` | `.exe` bundling |
| `pytest` | Testing |
| `pytest-cov` | Coverage |
| `ruff` | Linting + formatting |

---

## 11. HTTP Fetching

| Setting | Default |
|---------|---------|
| Timeout (connect) | 10s |
| Timeout (read) | 30s |
| Max redirects | 5 |
| Max response size | 10 MB |
| User-Agent | `shruggie-feedtools/0.1.0` |
| Retry count | 2 (exponential backoff) |
| Accept header | RSS/Atom/JSON content types |

Captures `Content-Type`, final URL, `ETag`/`Last-Modified` for future conditional fetching.

---

## 12. GUI Specification

### 12.1 Overview

The GUI is a standalone desktop application built with CustomTkinter. It mirrors the CLI's two-mode architecture (Parse / Construct) and serves as a visual frontend to the same library code. It is shipped as a separate release artifact alongside the CLI executable (see §13).

### 12.2 Layout

The window uses a two-panel layout: a narrow left sidebar for mode selection and a main working area on the right.

```
┌──────────────────────────────────────────────────────────────┐
│  Shruggie FeedTools                                    [—][×]│
├────────────┬─────────────────────────────────────────────────┤
│            │  ┌─────────────────────────────────────────────┐│
│  ┌──────┐  │  │  Input Method: (•) URL  ( ) File  ( ) Batch││
│  │ Parse│  │  ├─────────────────────────────────────────────┤│
│  └──────┘  │  │  URL: [____________________________________]││
│            │  │                                             ││
│  ┌──────┐  │  │  Options:                                   ││
│  │Const-│  │  │  [✓] Pretty print    Max items: [___]       ││
│  │ruct  │  │  │  [ ] Skip SSL verify                        ││
│  └──────┘  │  │                                             ││
│            │  │                      ┌─────────────────────┐││
│            │  │                      │    ▶ Parse Feed      │││
│            │  │                      └─────────────────────┘││
│            │  ├─────────────────────────────────────────────┤│
│            │  │  Output                          [Copy][Save]│
│            │  │  ┌─────────────────────────────────────────┐││
│            │  │  │{                                        │││
│            │  │  │  "status": "ok",                        │││
│            │  │  │  "schema_version": "1.0",               │││
│            │  │  │  ...                                    │││
│            │  │  └─────────────────────────────────────────┘││
│            │  └─────────────────────────────────────────────┘│
└────────────┴─────────────────────────────────────────────────┘
```

### 12.3 Mode: Parse

The Parse view has three input methods selectable via radio buttons at the top of the working area.

**URL input** — Single text field for a feed URL. The primary parse workflow.

**File input** — A file picker (Browse button) for selecting a local `.xml` or `.json` file. After selecting, the file path displays in a read-only field.

**Batch input** — A text area for entering multiple URLs (one per line) with a "Load from File" button to populate from a `.txt` file. The text area is editable so users can manually add/remove/reorder URLs.

All three input methods share a common options bar (pretty print toggle, max items spinner, SSL verification toggle) and the "Parse Feed" / "Parse All" action button. Results appear in the output panel below.

### 12.4 Mode: Construct

The Construct view presents three input fields stacked vertically:

**Template** — A file picker for selecting a `.feedtemplate.json` file. After selection, the template's `feed.title` is shown as confirmation that it loaded and validated.

**Text** — A multiline text area for the item content. Supports free-form text input.

**Timestamp** — A single-line text field. Accepts any format the date parser understands. Defaults to the current UTC time (pre-filled, editable).

An action button labeled "Construct Feed" triggers the operation. Results appear in the same output panel used by Parse mode.

### 12.5 Output Panel

The output panel is shared across both modes and occupies the lower portion of the working area. It is a scrollable, read-only, monospaced text area displaying the JSON output. Two buttons in the panel header: "Copy" (copies to clipboard) and "Save" (opens a save-as dialog defaulting to `.json`).

When an error occurs, the output panel displays the error response JSON (with `"status": "error"`) using the same rendering — no separate error dialog. This keeps the interface predictable and ensures error responses are copy/saveable just like successful output.

### 12.6 Appearance

Dark mode by default (CustomTkinter dark theme). Typography: JetBrains Mono for the output panel, Inter for all UI labels and controls, Space Grotesk for the window title. Minimum window size: 900×600. Resizable, with the output panel expanding to fill available vertical space.

### 12.7 Threading

All parse and construct operations run in a background thread to keep the UI responsive. The action button is disabled and shows a spinner/progress indicator while an operation is in progress. The output panel is cleared at the start of each operation and populated when the operation completes.

---

## 13. Release Pipeline

### 13.1 Release Artifacts

Every release publishes two artifacts:

| Artifact | Filename | Contents |
|----------|----------|----------|
| CLI executable | `shruggie-feedtools-cli-{version}-win-x64.exe` | PyInstaller single-file `.exe`. CLI only. No GUI deps. ~20–35 MB. |
| GUI executable | `shruggie-feedtools-gui-{version}-win-x64.exe` | PyInstaller single-file `.exe`. Full GUI + CLI. Includes CustomTkinter. ~40–65 MB. |

The CLI and GUI executables target Windows 10/11 x64.

> **Windows users:** After downloading a `.exe` from GitHub Releases, you may need to right-click → **Properties** → check **"Unblock"** → **OK** before Windows will let you run it.

### 13.2 GitHub Actions Workflow

The release workflow lives at `.github/workflows/release.yml`. It is triggered when a tag matching `v*` is pushed (e.g., `v0.1.0`).

The workflow supports two scenarios: pre-built assets pushed alongside the tag, or assets built from source in CI. The `dist/release/` directory is the handoff point.

#### Workflow Logic

```yaml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  release:
    runs-on: windows-latest
    permissions:
      contents: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check for pre-built assets
        id: check_assets
        shell: pwsh
        run: |
          $cliExists = Test-Path "dist/release/shruggie-feedtools-cli-*.exe"
          $guiExists = Test-Path "dist/release/shruggie-feedtools-gui-*.exe"
          if ($cliExists -and $guiExists) {
            echo "prebuilt=true" >> $env:GITHUB_OUTPUT
            Write-Host "Pre-built assets found in dist/release/. Skipping build."
          } else {
            echo "prebuilt=false" >> $env:GITHUB_OUTPUT
            Write-Host "No pre-built assets found. Will build from source."
          }

      - name: Set up Python 3.12
        if: steps.check_assets.outputs.prebuilt == 'false'
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Build release assets
        if: steps.check_assets.outputs.prebuilt == 'false'
        shell: pwsh
        run: |
          ./scripts/venv-setup.ps1
          ./scripts/build.ps1 -Release

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/release/*
          generate_release_notes: true
```

#### How the Pre-Built Bypass Works

If a developer builds the executables locally (via `./scripts/build.ps1 -Release`) and commits them to `dist/release/` before pushing the tag, the workflow detects the existing files and skips the entire build step. This avoids redundant CI compute and ensures the exact binaries the developer tested are what gets released.

If `dist/release/` is empty or missing the expected `.exe` files when the tag is pushed, the workflow builds everything from source.

The `.gitignore` should **not** ignore `dist/release/`. That directory is intentionally committable. The rest of `dist/` (build intermediates, `__pycache__`, etc.) should be gitignored.

```gitignore
# .gitignore (relevant excerpt)
dist/*
!dist/release/
.venv/
*.egg-info/
__pycache__/
build/
```

### 13.3 Version Tagging

Version is maintained in `src/shruggie_feedtools/_version.py` as the single source of truth. The release process is:

1. Update `_version.py` to the new version (e.g., `"0.2.0"`).
2. Commit.
3. Tag: `git tag v0.2.0`.
4. Push: `git push origin main --tags`.

---

## 14. Development Scripts

All scripts live in the `scripts/` directory. Each operation has a PowerShell (`.ps1`) and Bash (`.sh`) variant that mirror each other in function. Every script includes embedded help text and follows best practices for its platform.

**Critical rule**: No script ever runs Python outside the virtual environment. Every script that needs Python calls the venv-setup script first to ensure the environment exists, then activates it before proceeding.

### 14.1 `venv-setup.ps1` / `venv-setup.sh` — Virtual Environment Setup

These scripts are the foundation. Other scripts call them before doing anything that touches Python.

**Parameters:**

| Parameter | PS1 | Bash | Default | Description |
|-----------|-----|------|---------|-------------|
| Help | `-Help` | `--help` | — | Show usage and exit |
| PythonCmd | `-PythonCmd <string>` | `--python <string>` | `python` (ps1) / `python3.12` then `python3` (sh) | Python interpreter to use for venv creation |
| Force | `-Force` | `--force` | `false` | Delete and recreate the venv even if it exists |

**Logic:**

1. Locate the project root by walking up from the script's own directory until `pyproject.toml` is found.
2. Check if `.venv/` exists in the project root.
3. If `.venv/` exists and `-Force` was not specified: verify the Python version inside the venv is >=3.12. If valid, print "Virtual environment OK" and exit 0. If the version is wrong, print a warning and recreate.
4. If `.venv/` does not exist (or `-Force` was specified): run `<PythonCmd> -m venv .venv`. Activate the venv. Run `pip install --upgrade pip`. Run `pip install -e ".[dev,gui]"` (editable install with dev and GUI extras). Print summary of installed packages and exit 0.
5. If `<PythonCmd>` is not found or is below 3.12: print a clear error message ("Python >=3.12 is required. Found: <version>. Install from https://python.org") and exit 1.

**PowerShell specifics:**

```powershell
<#
.SYNOPSIS
    Sets up the Python virtual environment for shruggie-feedtools development.
.DESCRIPTION
    Checks for an existing .venv directory, validates the Python version,
    and creates/recreates the virtual environment as needed. Installs all
    development and GUI dependencies via editable install.
.PARAMETER PythonCmd
    Python interpreter command to use for venv creation. Default: "python"
.PARAMETER Force
    Force recreation of the virtual environment even if it already exists.
.EXAMPLE
    ./scripts/venv-setup.ps1
    ./scripts/venv-setup.ps1 -PythonCmd "py -3.12" -Force
#>
[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Python interpreter command")]
    [string]$PythonCmd = "python",

    [Parameter(HelpMessage = "Force recreation of virtual environment")]
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Activation: .venv\Scripts\Activate.ps1
```

**Bash specifics:**

```bash
#!/usr/bin/env bash
set -euo pipefail

# usage() function prints help text, called on --help or bad args
# Activation: source .venv/bin/activate
# Default PythonCmd: searches for python3.12 first, then python3, then python
```

### 14.2 `build.ps1` / `build.sh` — Build Release Executables

Compiles the CLI and GUI executables using PyInstaller.

**Parameters:**

| Parameter | PS1 | Bash | Default | Description |
|-----------|-----|------|---------|-------------|
| Help | `-Help` | `--help` | — | Show usage and exit |
| Target | `-Target <string>` | `--target <string>` | `all` | What to build: `cli`, `gui`, or `all` |
| Release | `-Release` | `--release` | `false` | Copy final artifacts to `dist/release/` with versioned filenames |
| Clean | `-Clean` | `--clean` | `false` | Delete `build/` and `dist/` before building |

**Logic:**

1. Call the venv-setup script to ensure the environment is ready. If it fails, exit immediately.
2. Activate the venv.
3. Read the version from `src/shruggie_feedtools/_version.py` (regex extraction of `__version__`).
4. If `-Clean` was specified: delete `build/` and `dist/` directories (preserving `dist/release/` unless `-Clean` is combined with `-Release`).
5. Build targets using PyInstaller:
   - **CLI target**: `pyinstaller --onefile --name shruggie-feedtools-cli --console src/shruggie_feedtools/__main__.py`
   - **GUI target**: `pyinstaller --onefile --name shruggie-feedtools-gui --windowed --add-data "src/shruggie_feedtools/gui:shruggie_feedtools/gui" src/shruggie_feedtools/gui/app.py`
6. If `-Release` was specified: create `dist/release/` if it doesn't exist. Copy and rename the built executables to versioned filenames (e.g., `shruggie-feedtools-cli-0.1.0-win-x64.exe`). Print the full path and file size of each artifact.
7. Print build summary (targets built, output locations, total time elapsed).

**PowerShell specifics:**

```powershell
<#
.SYNOPSIS
    Builds shruggie-feedtools release executables using PyInstaller.
.DESCRIPTION
    Compiles CLI and/or GUI executables. Optionally copies versioned
    artifacts to dist/release/ for GitHub release publishing.
.PARAMETER Target
    Build target: "cli", "gui", or "all". Default: "all"
.PARAMETER Release
    Copy final artifacts to dist/release/ with versioned filenames.
.PARAMETER Clean
    Delete build/ and dist/ directories before building.
.EXAMPLE
    ./scripts/build.ps1
    ./scripts/build.ps1 -Target cli -Release
    ./scripts/build.ps1 -Clean -Release
#>
[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Build target: cli, gui, or all")]
    [ValidateSet("cli", "gui", "all")]
    [string]$Target = "all",

    [Parameter(HelpMessage = "Copy artifacts to dist/release/ with versioned filenames")]
    [switch]$Release,

    [Parameter(HelpMessage = "Clean build directories before building")]
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
```

### 14.3 `test.ps1` / `test.sh` — Test Runner

Runs the full test suite with colored, per-test verbosity and a summary report.

**Parameters:**

| Parameter | PS1 | Bash | Default | Description |
|-----------|-----|------|---------|-------------|
| Help | `-Help` | `--help` | — | Show usage and exit |
| Silent | `-Silent` | `--silent` | `false` | Suppress all output. Exit code only. For CI use. |
| Coverage | `-Coverage` | `--coverage` | `false` | Generate coverage report |
| Filter | `-Filter <string>` | `--filter <string>` | — | pytest `-k` expression to run subset of tests |
| FailFast | `-FailFast` | `--fail-fast` | `false` | Stop on first failure |

**Logic:**

1. Call the venv-setup script. If it fails, exit immediately.
2. Activate the venv.
3. If `-Silent`: run `pytest --tb=no --no-header -q` and exit with pytest's exit code. No other output.
4. Otherwise: print a header banner with project name, Python version, and timestamp.
5. Run pytest with `--tb=short -v` (verbose, per-test lines). If `-Coverage`: add `--cov=shruggie_feedtools --cov-report=term-missing`. If `-Filter`: add `-k "<filter>"`. If `-FailFast`: add `-x`.
6. Parse pytest's output to produce a colored summary:
   - Each test line: green `✓ PASS` or red `✗ FAIL` prefix, followed by the test name.
   - Section headers (test files) printed in bold/white as encountered.
   - At the end, a summary block:

```
═══════════════════════════════════════════
  RESULTS: 47 passed, 2 failed, 1 skipped
═══════════════════════════════════════════

  FAILED:
    ✗ test_dates.py::test_parse_ambiguous_timezone
    ✗ test_cli.py::test_construct_missing_timestamp

  Duration: 3.4s
```

7. Green banner if all passed, red banner if any failed. Exit with pytest's exit code.

**Color implementation**: PowerShell uses `Write-Host -ForegroundColor`. Bash uses ANSI escape codes (`\033[32m` green, `\033[31m` red, `\033[1m` bold, `\033[0m` reset), with automatic detection of terminal color support via `tput colors` or `$TERM` — colors are disabled if output is not a terminal (i.e., when piped).

**PowerShell specifics:**

```powershell
<#
.SYNOPSIS
    Runs the shruggie-feedtools test suite with colored output.
.DESCRIPTION
    Executes pytest with per-test verbosity, colored pass/fail indicators,
    and a summary report. Supports silent mode for CI pipelines.
.PARAMETER Silent
    Suppress all output. Only exit code is emitted. Use in CI/CD pipelines.
.PARAMETER Coverage
    Generate a coverage report alongside test results.
.PARAMETER Filter
    pytest -k expression to run a subset of tests.
.PARAMETER FailFast
    Stop on first test failure.
.EXAMPLE
    ./scripts/test.ps1
    ./scripts/test.ps1 -Coverage -FailFast
    ./scripts/test.ps1 -Silent
    ./scripts/test.ps1 -Filter "test_dates"
#>
[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Suppress output, exit code only")]
    [switch]$Silent,

    [Parameter(HelpMessage = "Generate coverage report")]
    [switch]$Coverage,

    [Parameter(HelpMessage = "pytest -k filter expression")]
    [string]$Filter,

    [Parameter(HelpMessage = "Stop on first failure")]
    [switch]$FailFast
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
```

---

## 15. Configuration Object

```python
@dataclass
class ParserConfig:
    # HTTP
    timeout_connect: float = 10.0
    timeout_read: float = 30.0
    max_response_bytes: int = 10 * 1024 * 1024
    user_agent: str = "shruggie-feedtools/0.1.0"
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
```

---

## 16. API-Readiness Design

1. `parse_string()` is the atomic parse operation.
2. `construct()` is the atomic construct operation.
3. `httpx` for async compatibility with future FastAPI.
4. Pydantic models = API response schema.
5. No global state. Stateless. Thread-safe.
6. `ParserConfig` dataclass passed explicitly.

---

## 17. Testing

### 17.1 Test Framework and Conventions

Framework: `pytest` with `pytest-cov` for coverage. Target: 90%+ line coverage on non-GUI code. Tests live in `tests/` and follow the naming convention `test_<module>.py`. Each test function is named `test_<what_it_verifies>` with a docstring explaining the expected behavior.

Snapshot testing uses golden files in `tests/snapshots/`. Running `pytest --update-snapshots` regenerates them. Snapshots are committed to the repo — diffs in snapshot files during code review are how schema changes get caught.

### 17.2 Fixture Data

Parse mode fixtures:

| Fixture File | Source Type | Why It's Included |
|-------------|-------------|-------------------|
| `rss2/minimal.xml` | RSS 2.0 | Minimum valid RSS. Tests default handling. |
| `rss2/wordpress.xml` | RSS 2.0 | Real WordPress export. dc:creator, content:encoded, excerpt, categories, featured images. |
| `rss2/podcast_itunes.xml` | RSS 2.0 + iTunes | iTunes namespace fields: duration, explicit, image, author, episode type. |
| `rss2/hairy_malformed.xml` | RSS 2.0 | Missing closing tags, bad dates, mixed encodings, empty elements. Tests graceful degradation. |
| `rss2/financial_sec.xml` | RSS 2.0 | SEC EDGAR filing feed. Unusual structure, no descriptions, date edge cases. |
| `rss2/reddit.xml` | RSS 2.0 + Media RSS | media:thumbnail, media:content, HTML entities in titles. |
| `atom10/github_releases.xml` | Atom 1.0 | GitHub releases feed. link[rel=alternate], content type=html, updated dates. |
| `atom10/youtube_channel.xml` | Atom 1.0 + YouTube | yt:videoId, yt:channelId, media:group, media:thumbnail. |
| `atom10/statuspage.xml` | Atom 1.0 | Statuspage.io incident feed. Multiple updates per entry. |
| `rss1/rdf_gov.xml` | RSS 1.0 (RDF) | Government .gov feed. RDF structure, dc: namespace throughout. |
| `json_feed/v1_standard.json` | JSON Feed 1.1 | Standard JSON Feed with authors array, tags, attachments, content_html. |
| `wp_rest/posts_embedded.json` | WordPress REST | `_embedded` author, featured media, wp:term categories. |
| `edge_cases/mixed_case_elements.xml` | RSS 2.0 | `<Title>`, `<TITLE>`, `<title>` in same feed. |
| `edge_cases/custom_namespace_prefixes.xml` | RSS 2.0 | Non-standard prefixes for dc, content, itunes namespaces. |
| `edge_cases/bad_dates.xml` | RSS 2.0 | 15+ date formats including malformed, ambiguous timezones, epoch, empty. |
| `edge_cases/missing_fields.xml` | RSS 2.0 | Feed with zero optional fields. Tests every default value. |
| `edge_cases/encoding_utf8_bom.xml` | RSS 2.0 | UTF-8 BOM, HTML entities, Unicode in titles/content. |

Construct mode fixtures:

| Fixture File | Purpose |
|-------------|---------|
| `templates/minimal.feedtemplate.json` | Only `template_version`, `feed.title`, and `item_mapping`. Tests that all omitted fields receive correct defaults. |
| `templates/incident_log.feedtemplate.json` | Full template with all fields populated. Ops/monitoring use case. |
| `templates/changelog.feedtemplate.json` | Uses `link_pattern` with `{guid}` placeholder. Dev changelog use case. |
| `templates/all_strategies.feedtemplate.json` | Not a realistic template — exists purely to exercise every strategy combination in tests. |
| `templates/invalid_missing_title.feedtemplate.json` | Missing `feed.title`. Must trigger `TemplateValidationError`. |
| `entries/single_entry.jsonl` | One-line JSONL with text + timestamp. |
| `entries/batch_entries.jsonl` | 10 entries with varying timestamps. |
| `entries/entries_with_overrides.jsonl` | Entries with per-entry title, author, and category overrides. |

### 17.3 Test Specifications

Each test file below lists its test functions and what each function verifies.

#### `test_detector.py` — Format Detection

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_detect_rss2_standard` | `rss2/minimal.xml` bytes | Returns `"rss2"` |
| `test_detect_atom10_standard` | `atom10/github_releases.xml` bytes | Returns `"atom10"` |
| `test_detect_rss1_rdf` | `rss1/rdf_gov.xml` bytes | Returns `"rss1"` |
| `test_detect_json_feed` | `json_feed/v1_standard.json` bytes | Returns `"json_feed"` |
| `test_detect_wp_rest` | `wp_rest/posts_embedded.json` bytes | Returns `"wp_rest"` |
| `test_detect_xml_with_bom` | `encoding_utf8_bom.xml` bytes | Returns correct type despite BOM prefix |
| `test_detect_empty_bytes` | `b""` | Returns `None` |
| `test_detect_html_page` | `<html>...</html>` bytes | Returns `None` (not a feed) |
| `test_detect_plain_text` | `"Hello world"` bytes | Returns `None` |
| `test_detect_json_non_feed` | `{"name": "not a feed"}` bytes | Returns `None` |

#### `test_dates.py` — Date Parsing and Normalization

| Test Function | Input | Expected Output |
|--------------|-------|-----------------|
| `test_parse_rfc2822` | `"Thu, 09 Feb 2026 12:00:00 GMT"` | `"2026-02-09T12:00:00Z"` |
| `test_parse_rfc2822_with_offset` | `"Thu, 09 Feb 2026 07:00:00 -0500"` | `"2026-02-09T12:00:00Z"` |
| `test_parse_iso8601_utc` | `"2026-02-09T12:00:00Z"` | `"2026-02-09T12:00:00Z"` |
| `test_parse_iso8601_offset` | `"2026-02-09T12:00:00+05:00"` | `"2026-02-09T07:00:00Z"` |
| `test_parse_iso8601_no_tz` | `"2026-02-09T12:00:00"` | `"2026-02-09T12:00:00Z"` (assumed UTC) |
| `test_parse_loose_date_only` | `"February 9, 2026"` | `"2026-02-09T00:00:00Z"` |
| `test_parse_loose_ymd` | `"2026-02-09"` | `"2026-02-09T00:00:00Z"` |
| `test_parse_unix_epoch_int` | `1770595200` | `"2026-02-09T12:00:00Z"` |
| `test_parse_unix_epoch_float` | `1770595200.5` | `"2026-02-09T12:00:00Z"` (truncated to seconds) |
| `test_parse_garbage_returns_none` | `"not a date at all"` | `None` |
| `test_parse_empty_returns_none` | `""` | `None` |
| `test_parse_partial_date` | `"Feb 2026"` | `"2026-02-01T00:00:00Z"` (best-effort first of month) |
| `test_all_outputs_are_utc` | Various inputs with offsets | All outputs end in `Z`, no offset strings |

#### `test_namespaces.py` — Namespace Prefix Normalization

| Test Function | Input (URI, declared) | Expected Canonical Prefix |
|--------------|----------------------|--------------------------|
| `test_dc_http` | `("http://purl.org/dc/elements/1.1/", "x")` | `"dc"` |
| `test_dc_https` | `("https://purl.org/dc/elements/1.1/", "x")` | `"dc"` |
| `test_dc_trailing_slash` | `("http://purl.org/dc/elements/1.1", "x")` | `"dc"` |
| `test_dc_uppercase_scheme` | `("HTTP://purl.org/dc/elements/1.1/", "x")` | `"dc"` |
| `test_itunes_standard` | `("http://www.itunes.com/dtds/podcast-1.0.dtd", "itunes")` | `"itunes"` |
| `test_itunes_custom_prefix` | `("http://www.itunes.com/dtds/podcast-1.0.dtd", "podcast")` | `"itunes"` |
| `test_media_rss` | `("http://search.yahoo.com/mrss/", "media")` | `"media"` |
| `test_unknown_uri_uses_declared` | `("http://example.com/custom/ns", "myns")` | `"myns"` |
| `test_youtube_namespace` | `("http://www.youtube.com/xml/schemas/2015", "yt")` | `"yt"` |
| `test_all_known_uris_resolve` | All entries in `NAMESPACE_MAP` | Each resolves to its canonical prefix |

#### `test_adapters.py` — Format-Specific Parsing

Tests each adapter in isolation. Adapters receive raw content and return intermediate dicts (not yet normalized to the final schema — that's the normalizer's job). These tests verify that adapters correctly extract raw values from their respective formats.

**feedparser adapter (RSS 2.0):**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_rss2_minimal_extracts_title` | `rss2/minimal.xml` | `feed.title` is non-empty string |
| `test_rss2_minimal_extracts_items` | `rss2/minimal.xml` | `items` is a non-empty list |
| `test_rss2_wordpress_dc_creator` | `rss2/wordpress.xml` | Items contain `dc:creator` values |
| `test_rss2_wordpress_content_encoded` | `rss2/wordpress.xml` | Items contain `content:encoded` HTML body |
| `test_rss2_wordpress_categories` | `rss2/wordpress.xml` | Items have `categories` arrays with at least one entry |
| `test_rss2_podcast_itunes_fields` | `rss2/podcast_itunes.xml` | Items contain `itunes:duration`, `itunes:explicit`, `itunes:image` |
| `test_rss2_podcast_enclosure` | `rss2/podcast_itunes.xml` | At least one item has an enclosure with `url`, `type`, `length` |
| `test_rss2_malformed_does_not_crash` | `rss2/hairy_malformed.xml` | Returns a result (not an exception). May have fewer items. |
| `test_rss2_malformed_bozo_flag` | `rss2/hairy_malformed.xml` | `feedparser` bozo flag is `True`; adapter logs a warning but still returns data |
| `test_rss2_reddit_media_thumbnail` | `rss2/reddit.xml` | Items contain `media:thumbnail` URLs |
| `test_rss2_sec_minimal_descriptions` | `rss2/financial_sec.xml` | Items parse successfully even with missing/empty descriptions |

**feedparser adapter (Atom 1.0):**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_atom10_github_link_alternate` | `atom10/github_releases.xml` | Item links use `rel="alternate"` href |
| `test_atom10_github_updated_dates` | `atom10/github_releases.xml` | Items have `updated` fields (Atom uses `updated` not `pubDate`) |
| `test_atom10_github_content_html` | `atom10/github_releases.xml` | Items contain HTML content bodies |
| `test_atom10_youtube_yt_videoid` | `atom10/youtube_channel.xml` | Items contain `yt:videoId` values |
| `test_atom10_youtube_media_group` | `atom10/youtube_channel.xml` | Items contain `media:group` with `media:thumbnail` |
| `test_atom10_statuspage_multiple_updates` | `atom10/statuspage.xml` | Entries with multiple `<updated>` values are handled (latest wins) |

**feedparser adapter (RSS 1.0 / RDF):**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_rss1_rdf_parses_items` | `rss1/rdf_gov.xml` | Returns non-empty items list |
| `test_rss1_rdf_dc_namespace` | `rss1/rdf_gov.xml` | Items contain `dc:` prefixed fields throughout |
| `test_rss1_source_type` | `rss1/rdf_gov.xml` | Source type reports as `"rss1"` |

**WordPress REST adapter:**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_wp_rest_extracts_title` | `wp_rest/posts_embedded.json` | `item.title` extracted from `title.rendered` with HTML entities decoded |
| `test_wp_rest_extracts_content` | `wp_rest/posts_embedded.json` | `item.content` extracted from `content.rendered` |
| `test_wp_rest_extracts_excerpt` | `wp_rest/posts_embedded.json` | `item.description` extracted from `excerpt.rendered` |
| `test_wp_rest_embedded_author` | `wp_rest/posts_embedded.json` | `item.author` extracted from `_embedded.author[0].name` |
| `test_wp_rest_embedded_featured_media` | `wp_rest/posts_embedded.json` | `item.thumbnail` extracted from `_embedded["wp:featuredmedia"][0].source_url` |
| `test_wp_rest_embedded_categories` | `wp_rest/posts_embedded.json` | `item.categories` flattened from `_embedded["wp:term"]` |
| `test_wp_rest_guid` | `wp_rest/posts_embedded.json` | `item.guid` extracted from `guid.rendered` |
| `test_wp_rest_dates_gmt` | `wp_rest/posts_embedded.json` | `item.pub_date` from `date_gmt`, `item.updated` from `modified_gmt`, both with `Z` suffix |
| `test_wp_rest_base_url_extraction` | `wp_rest/posts_embedded.json` with `base_url` | `feed.link` strips `/wp-json/...` path |

**JSON Feed adapter:**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_json_feed_extracts_title` | `json_feed/v1_standard.json` | `feed.title` matches source `title` |
| `test_json_feed_home_page_url` | `json_feed/v1_standard.json` | `feed.link` from `home_page_url` |
| `test_json_feed_authors_array` | `json_feed/v1_standard.json` | `feed.author` from `authors[0].name` (v1.1 array format) |
| `test_json_feed_item_content_html` | `json_feed/v1_standard.json` | `item.content` from `content_html` |
| `test_json_feed_item_tags` | `json_feed/v1_standard.json` | `item.categories` from `tags[]` |
| `test_json_feed_item_attachments` | `json_feed/v1_standard.json` | `item.enclosures` mapped from `attachments[]` with `url`, `mime_type`, `size_in_bytes` |
| `test_json_feed_item_dates` | `json_feed/v1_standard.json` | `item.pub_date` from `date_published`, `item.updated` from `date_modified` |
| `test_json_feed_item_image` | `json_feed/v1_standard.json` | `item.thumbnail` from `image` or `banner_image` |
| `test_json_feed_item_summary` | `json_feed/v1_standard.json` | `item.description` from `summary` field |

#### `test_normalizer.py` — Schema Mapping and Field Normalization

Tests the normalizer module, which takes the intermediate dict output from any adapter and maps it into the final output schema fields. Covers fallback chains, default values, date normalization, thumbnail extraction, and extension bucketing.

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_title_passthrough` | Intermediate dict with `title: "Hello"` | Output item `title` is `"Hello"` |
| `test_title_missing_defaults_empty` | Intermediate dict with no `title` key | Output item `title` is `""` |
| `test_description_from_summary` | Intermediate dict with `summary` but no `description` | Output `description` populated from `summary` |
| `test_description_fallback_to_content_truncated` | Intermediate dict with `content` only (no summary/description) | Output `description` is truncated content |
| `test_content_from_content_encoded` | Intermediate dict with `content:encoded` | Output `content` populated from `content:encoded` value |
| `test_content_prefers_full_over_summary` | Intermediate dict with both `content` and `summary` | Output `content` uses the longer/full value, `description` uses the shorter |
| `test_author_from_dc_creator` | Intermediate dict with `dc:creator` but no `author` | Output `author` populated from `dc:creator` |
| `test_author_from_atom_author_name` | Intermediate dict with `author.name` (Atom style) | Output `author` is the name string |
| `test_guid_passthrough` | Intermediate dict with `guid` | Output `guid` matches input |
| `test_guid_missing_falls_back_to_link` | Intermediate dict with `link` but no `guid` | Output `guid` equals the `link` value |
| `test_guid_is_permalink_true` | Intermediate dict with `guid_is_permalink: true` | Output `guid_is_permalink` is `True` |
| `test_guid_is_permalink_default_false` | Intermediate dict with no permalink info | Output `guid_is_permalink` is `False` |
| `test_pub_date_normalized_to_utc` | Intermediate dict with RFC 2822 date | Output `pub_date` is ISO 8601 UTC string |
| `test_pub_date_missing_is_null` | Intermediate dict with no date | Output `pub_date` is `None` |
| `test_updated_separate_from_pub_date` | Intermediate dict with both `published` and `updated` | Output has distinct `pub_date` and `updated` values |
| `test_thumbnail_from_media_thumbnail` | Intermediate dict with `media:thumbnail` URL | Output `thumbnail` matches the URL |
| `test_thumbnail_from_media_content_image` | Intermediate dict with `media:content` of type `image/*` | Output `thumbnail` extracted |
| `test_thumbnail_from_enclosure_image` | Intermediate dict with enclosure of type `image/jpeg` | Output `thumbnail` from enclosure URL |
| `test_thumbnail_extraction_disabled` | Config with `thumbnail_extraction=False` | Output `thumbnail` is `""` regardless of available sources |
| `test_enclosures_mapped` | Intermediate dict with enclosure data | Output `enclosures` list with `url`, `type`, `length` per item |
| `test_enclosures_empty_when_none` | Intermediate dict with no enclosures | Output `enclosures` is `[]` |
| `test_categories_from_tags` | Intermediate dict with `tags` list | Output `categories` is list of strings |
| `test_categories_deduplication` | Intermediate dict with duplicate tag values | Output `categories` contains no duplicates |
| `test_extensions_bucket_namespaced` | Intermediate dict with `itunes:duration`, `yt:videoId` | Output `extensions` has `{"itunes": {"duration": ...}, "yt": {"videoId": ...}}` |
| `test_extensions_uses_normalized_prefix` | Intermediate dict with custom prefix resolved to canonical | Extension keys use canonical prefix, not original declared prefix |
| `test_extensions_disabled` | Config with `include_extensions=False` | Output `extensions` is `{}` regardless of source data |
| `test_feed_language_passthrough` | Intermediate feed dict with `language: "en-us"` | Output `feed.language` is `"en-us"` |
| `test_feed_generator_passthrough` | Intermediate feed dict with `generator` | Output `feed.generator` preserves the value |
| `test_feed_ttl_integer` | Intermediate feed dict with `ttl: "60"` (string) | Output `feed.ttl` is `60` (integer) |
| `test_feed_ttl_missing_is_null` | Intermediate feed dict with no `ttl` | Output `feed.ttl` is `None` |
| `test_feed_image_from_logo` | Intermediate feed dict with `logo` URL (Atom) | Output `feed.image` matches the URL |
| `test_feed_last_updated_computed` | Intermediate feed dict with no `updated`, items with `pub_date` values | Output `feed.last_updated` is the latest `pub_date` across all items |

#### `test_schema.py` — Pydantic Model Validation

Tests the Pydantic models that enforce the output schema contract. These models are the last gate before output — they guarantee structural correctness regardless of which adapter or mode produced the data.

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_valid_response_roundtrips` | Fully populated response dict | Pydantic model accepts it; `.model_dump()` matches input structure |
| `test_minimal_response_roundtrips` | Response with only required fields, all optionals at defaults | Model accepts; defaults are correct types |
| `test_status_enum_ok` | `status: "ok"` | Accepted |
| `test_status_enum_error` | `status: "error"` | Accepted |
| `test_status_enum_invalid` | `status: "maybe"` | Pydantic `ValidationError` |
| `test_schema_version_required` | Response dict missing `schema_version` | `ValidationError` |
| `test_source_type_valid_values` | Each of `"rss2"`, `"rss1"`, `"atom10"`, `"json_feed"`, `"wp_rest"`, `"constructed"` | All accepted |
| `test_source_origin_valid_values` | Each of `"url"`, `"file"`, `"string"`, `"template"` | All accepted |
| `test_source_url_nullable` | `source.url: null` | Accepted (valid for file/string/template origins) |
| `test_feed_title_is_string` | `feed.title: 123` (integer) | `ValidationError` — must be string |
| `test_feed_categories_is_string_array` | `feed.categories: ["a", "b"]` | Accepted |
| `test_feed_categories_rejects_non_strings` | `feed.categories: [1, 2]` | `ValidationError` |
| `test_feed_ttl_nullable_int` | `feed.ttl: null` then `feed.ttl: 60` | Both accepted |
| `test_feed_ttl_rejects_string` | `feed.ttl: "sixty"` | `ValidationError` |
| `test_feed_extensions_is_dict` | `feed.extensions: {"dc": {"creator": "X"}}` | Accepted |
| `test_item_defaults_applied` | Item dict with no optional fields | Model fills defaults: `title=""`, `guid=""`, `categories=[]`, etc. |
| `test_item_pub_date_nullable` | `pub_date: null` | Accepted |
| `test_item_pub_date_accepts_iso_string` | `pub_date: "2026-02-09T12:00:00Z"` | Accepted |
| `test_item_enclosure_structure` | `enclosures: [{"url": "...", "type": "audio/mpeg", "length": 123}]` | Accepted |
| `test_item_enclosure_missing_fields` | `enclosures: [{"url": "..."}]` (no type/length) | Accepted with defaults or `None` for optional enclosure fields |
| `test_item_guid_is_permalink_bool` | `guid_is_permalink: "yes"` (string) | `ValidationError` — must be bool |
| `test_item_comments_count_nullable_int` | `comments_count: null` then `comments_count: 5` | Both accepted |
| `test_response_serialization_json` | Valid response model instance | `.model_dump_json()` produces valid JSON string |
| `test_response_serialization_excludes_none` | Response with `None` optional fields | Serialized output either includes `null` or excludes key per configuration |
| `test_error_response_includes_message` | Response with `status: "error"`, `message: "Timeout"` | Model accepts; `message` field present in output |

#### `test_parser.py` — End-to-End Parse Pipeline

Integration tests that run the full pipeline: raw content → detection → adapter → namespace normalization → normalizer → Pydantic validation → output dict. Each test uses a fixture file and verifies the final output structure, not intermediate states.

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_parse_rss2_minimal_full_pipeline` | `rss2/minimal.xml` via `parse_string()` | `status: "ok"`, `source.type: "rss2"`, `feed.title` non-empty, `items` non-empty, all items have `pub_date` or `None` |
| `test_parse_rss2_wordpress_full_pipeline` | `rss2/wordpress.xml` via `parse_string()` | Items have `author` (from dc:creator), `content` (from content:encoded), `categories`, `thumbnail` |
| `test_parse_rss2_podcast_full_pipeline` | `rss2/podcast_itunes.xml` via `parse_string()` | Items have enclosures with audio MIME types; `extensions.itunes` contains `duration`, `explicit` |
| `test_parse_atom10_github_full_pipeline` | `atom10/github_releases.xml` via `parse_string()` | `source.type: "atom10"`, items have `link`, `content`, `updated` dates |
| `test_parse_atom10_youtube_full_pipeline` | `atom10/youtube_channel.xml` via `parse_string()` | Items have `thumbnail`, `extensions.yt.videoId` |
| `test_parse_rss1_rdf_full_pipeline` | `rss1/rdf_gov.xml` via `parse_string()` | `source.type: "rss1"`, items parse with dc: fields normalized |
| `test_parse_json_feed_full_pipeline` | `json_feed/v1_standard.json` via `parse_string()` | `source.type: "json_feed"`, feed and items fully populated |
| `test_parse_wp_rest_full_pipeline` | `wp_rest/posts_embedded.json` via `parse_string()` | `source.type: "wp_rest"`, items have `author`, `thumbnail`, `categories` from embedded data |
| `test_parse_malformed_degrades_gracefully` | `rss2/hairy_malformed.xml` via `parse_string()` | `status: "ok"`, returns partial items; missing fields get defaults; no exception raised |
| `test_parse_empty_string_returns_error` | `""` via `parse_string()` | `status: "error"`, `message` present |
| `test_parse_html_page_returns_error` | `<html>...</html>` via `parse_string()` | `status: "error"`, message indicates unrecognized format |
| `test_parse_unknown_json_returns_error` | `{"random": "object"}` via `parse_string()` | `status: "error"`, message indicates no known feed format |
| `test_parse_file_from_path` | Local fixture file path via `parse_file()` | Same result as `parse_string()` with same content; `source.origin: "file"` |
| `test_parse_source_origin_string` | Content via `parse_string()` | `source.origin: "string"` |
| `test_parse_source_url_preserved` | Content via `parse_string(source_url="https://x.com/feed")` | `source.url: "https://x.com/feed"` |
| `test_parse_max_items_config` | `rss2/wordpress.xml` with `ParserConfig(max_items=3)` | Output `items` has at most 3 entries |
| `test_parse_rss_direct_skips_detection` | `rss2/minimal.xml` via `parse_rss()` | Same output as auto-detect pipeline; detection step is skipped |
| `test_parse_atom_direct_skips_detection` | `atom10/github_releases.xml` via `parse_atom()` | Same output as auto-detect pipeline |
| `test_parse_output_validates_against_schema` | Any fixture via `parse_string()` | Output passes Pydantic model validation with zero errors |
| `test_parse_all_dates_are_utc_iso` | `rss2/wordpress.xml` via `parse_string()` | Every non-null `pub_date` and `updated` across all items ends in `Z` |
| `test_parse_namespace_normalization_applied` | `edge_cases/custom_namespace_prefixes.xml` via `parse_string()` | Extensions use canonical prefixes (`dc`, `itunes`, `content`) not the custom prefixes declared in the XML |
| `test_parse_mixed_case_elements` | `edge_cases/mixed_case_elements.xml` via `parse_string()` | Parses successfully; `<Title>`, `<TITLE>`, `<title>` all resolve to `title` field |
| `test_parse_bad_dates_survive` | `edge_cases/bad_dates.xml` via `parse_string()` | `status: "ok"`, unparseable dates become `null`, parseable dates are correct |
| `test_parse_missing_fields_all_defaults` | `edge_cases/missing_fields.xml` via `parse_string()` | Every optional field is its documented default value |
| `test_parse_encoding_utf8_bom` | `edge_cases/encoding_utf8_bom.xml` via `parse_string()` | Parses successfully; Unicode characters preserved in titles/content |

#### `test_fetcher.py` — HTTP Fetching

Tests the HTTP client wrapper. Uses `httpx`'s built-in mock transport or `pytest-httpx` to simulate network conditions without real HTTP requests.

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_fetch_returns_bytes` | Mock 200 response with XML body | Returns raw bytes of the response body |
| `test_fetch_captures_content_type` | Mock response with `Content-Type: application/rss+xml` | Returned metadata includes `content_type: "application/rss+xml"` |
| `test_fetch_captures_final_url` | Mock 301 redirect from URL A → URL B | Returned metadata includes `final_url` matching URL B |
| `test_fetch_captures_etag` | Mock response with `ETag: "abc123"` header | Returned metadata includes `etag: "abc123"` |
| `test_fetch_captures_last_modified` | Mock response with `Last-Modified` header | Returned metadata includes `last_modified` value |
| `test_fetch_timeout_connect` | Mock transport that hangs on connect | Raises or returns error within `timeout_connect` seconds |
| `test_fetch_timeout_read` | Mock transport that hangs on read | Raises or returns error within `timeout_read` seconds |
| `test_fetch_http_404_returns_error` | Mock 404 response | Returns error result with HTTP status code in message |
| `test_fetch_http_500_returns_error` | Mock 500 response | Returns error result |
| `test_fetch_dns_failure_returns_error` | Mock DNS resolution failure | Returns error result with network error message |
| `test_fetch_max_response_size` | Mock response body exceeding 10 MB | Fetch truncates or rejects; does not consume unbounded memory |
| `test_fetch_redirect_limit` | Mock chain of 6+ redirects | Returns error after `max_redirects` (default 5) |
| `test_fetch_retry_on_transient_error` | Mock: first request 503, second request 200 | Returns successful result after retry |
| `test_fetch_retry_exhaustion` | Mock: all requests return 503 | Returns error after `retries` attempts (default 2) |
| `test_fetch_user_agent_header` | Mock transport that captures request headers | Request contains `User-Agent: shruggie-feedtools/0.1.0` |
| `test_fetch_custom_user_agent` | `ParserConfig(user_agent="custom/1.0")` | Request contains `User-Agent: custom/1.0` |
| `test_fetch_accept_header` | Mock transport that captures request headers | Request contains `Accept` header listing RSS/Atom/JSON content types |
| `test_fetch_ssl_verification_default` | Default config | SSL verification is enabled |
| `test_fetch_ssl_verification_disabled` | `ParserConfig(verify_ssl=False)` | SSL verification is disabled in the request |

#### `test_construct.py` — Feed Construction

Integration tests for construct mode. Tests the full pipeline: template + text + timestamp → builder → Pydantic validation → output. Uses template fixtures from `tests/fixtures/templates/`.

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_construct_single_item` | Text string + timestamp + minimal template | `status: "ok"`, `source.type: "constructed"`, `source.origin: "template"`, `items` has exactly 1 entry |
| `test_construct_item_content_from_text` | Text `"Hello world"`, `text_target: "content"` | `items[0].content` is `"Hello world"` |
| `test_construct_item_content_to_description` | Text, `text_target: "description"` | `items[0].description` is the text, `items[0].content` is `""` |
| `test_construct_item_content_to_both` | Text, `text_target: "both"` | `items[0].content` is the text, `items[0].description` is derived from text |
| `test_construct_pub_date_from_timestamp` | Timestamp `"2026-02-10T08:30:00Z"` | `items[0].pub_date` is `"2026-02-10T08:30:00Z"` |
| `test_construct_pub_date_normalizes_offset` | Timestamp `"2026-02-10T03:30:00-05:00"` | `items[0].pub_date` is `"2026-02-10T08:30:00Z"` |
| `test_construct_pub_date_from_epoch` | Timestamp `1770595200` | `items[0].pub_date` is valid ISO 8601 UTC string |
| `test_construct_feed_metadata_from_template` | Incident log template with all feed fields | Output `feed.title`, `feed.link`, `feed.description`, `feed.language`, `feed.author` match template values |
| `test_construct_feed_generator_forced` | Any template | Output `feed.generator` is `"shruggie-feedtools/0.1.0"` regardless of template content |
| `test_construct_feed_last_updated_computed` | Batch of 3 entries with different timestamps | `feed.last_updated` equals the latest `pub_date` across all items |
| `test_construct_item_defaults_applied` | Template with `item_defaults.author: "bot"`, `item_defaults.categories: ["ops"]` | `items[0].author` is `"bot"`, `items[0].categories` is `["ops"]` |
| `test_construct_item_defaults_overridden_by_entry` | Batch entry with `author: "jdoe"`, template default `author: "bot"` | Item uses `"jdoe"` not `"bot"` |
| `test_construct_link_pattern` | Template with `link_pattern: "https://x.com/{guid}"` | `items[0].link` is `"https://x.com/<generated_guid>"` |
| `test_construct_source_url_null` | Any construct call | `source.url` is `null` |
| `test_construct_batch_multiple_items` | 3 entries via `construct_batch()` | `items` has exactly 3 entries, each with correct `pub_date` |
| `test_construct_batch_ordering` | 3 entries with timestamps out of chronological order | Items appear in the order provided (no automatic sorting) |
| `test_construct_batch_from_jsonl` | `entries/batch_entries.jsonl` fixture | All 10 entries parsed and present in output |
| `test_construct_batch_entry_overrides` | `entries/entries_with_overrides.jsonl` fixture | Per-entry `title`, `author`, `categories` override template defaults |
| `test_construct_batch_bad_entry_skipped` | JSONL with one malformed line among valid entries | Valid entries succeed; bad entry is skipped; warning logged |
| `test_construct_inline_template_dict` | Template passed as Python dict instead of file path | Output is identical to file-based template with same content |
| `test_construct_output_validates_against_schema` | Any construct call | Output passes Pydantic model validation with zero errors |
| `test_construct_empty_text` | Text `""` + valid timestamp + minimal template | `status: "ok"`, item has `content: ""`, `title` derived per strategy (may be `""`) |
| `test_construct_guid_deterministic_sha256` | Same text + same timestamp, called twice | Both calls produce the same GUID |
| `test_construct_guid_different_inputs` | Different text, same timestamp | GUIDs differ |

#### `test_template.py` — Template Loading and Validation

Tests the template loading, Pydantic validation, and default application logic. Exercises both valid templates and intentional validation failures.

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_load_minimal_template` | `templates/minimal.feedtemplate.json` | Loads successfully; `template_version` is `"1.0"`, `feed.title` is set |
| `test_load_full_template` | `templates/incident_log.feedtemplate.json` | All fields populated, no defaults needed |
| `test_load_template_defaults_item_mapping` | Minimal template with `item_mapping` containing only `text_target` | Defaults applied: `title_strategy: "first_line"`, `title_max_length: 120`, `description_strategy: "truncate"`, `description_max_length: 280`, `guid_strategy: "sha256"`, `link_pattern: null` |
| `test_load_template_defaults_item_defaults` | Minimal template with no `item_defaults` section | Defaults applied: `author: ""`, `categories: []`, `thumbnail: ""`, `link: ""`, `extensions: {}` |
| `test_load_template_defaults_feed_optional_fields` | Template with only `feed.title` | Defaults: `link: ""`, `description: ""`, `language: ""`, `author: ""`, `image: ""`, `categories: []`, `ttl: null` |
| `test_load_missing_template_version` | Template JSON without `template_version` | `TemplateValidationError` mentioning `template_version` |
| `test_load_missing_feed_title` | `templates/invalid_missing_title.feedtemplate.json` | `TemplateValidationError` mentioning `feed.title` |
| `test_load_missing_item_mapping` | Template JSON without `item_mapping` section | `TemplateValidationError` mentioning `item_mapping` |
| `test_load_invalid_text_target` | `item_mapping.text_target: "title"` (not in allowed set) | `TemplateValidationError` listing valid values: `content`, `description`, `both` |
| `test_load_invalid_title_strategy` | `item_mapping.title_strategy: "random"` | `TemplateValidationError` listing valid values: `first_line`, `truncate`, `timestamp`, `template`, `none` |
| `test_load_invalid_description_strategy` | `item_mapping.description_strategy: "ai_summary"` | `TemplateValidationError` listing valid values: `truncate`, `first_line`, `same`, `none` |
| `test_load_invalid_guid_strategy` | `item_mapping.guid_strategy: "md5"` | `TemplateValidationError` listing valid values: `sha256`, `uuid4`, `timestamp`, `sequential` |
| `test_load_title_max_length_must_be_positive` | `item_mapping.title_max_length: 0` | `TemplateValidationError` |
| `test_load_description_max_length_must_be_positive` | `item_mapping.description_max_length: -1` | `TemplateValidationError` |
| `test_load_template_from_dict` | Valid template as Python dict (not a file path) | Loads and validates identically to file-based loading |
| `test_load_nonexistent_file` | Path to a file that does not exist | `FileNotFoundError` or equivalent with clear message |
| `test_load_invalid_json` | File containing `{broken json` | Error with message indicating JSON parse failure |
| `test_load_template_caching` | Same file path loaded twice via `load_template()` | Second call returns without re-reading disk (if caching implemented) or is functionally identical |
| `test_template_version_unsupported` | `template_version: "2.0"` | `TemplateValidationError` indicating unsupported version |

#### `test_strategies.py` — Title, Description, and GUID Derivation

Tests each derivation strategy function in isolation. These are pure functions: input text/timestamp/config in, derived string out.

**Title strategies:**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_title_first_line_basic` | Text `"First line\nSecond line"` | `"First line"` |
| `test_title_first_line_no_newline` | Text `"Only one line"` | `"Only one line"` |
| `test_title_first_line_truncated` | Text with first line of 200 chars, `title_max_length: 120` | 120 chars ending with `…` |
| `test_title_first_line_empty_text` | Text `""` | `""` |
| `test_title_first_line_leading_newline` | Text `"\nActual first line"` | `""` (first line is empty) |
| `test_title_truncate_basic` | Text `"A long paragraph of text..."` (150 chars), `title_max_length: 80` | 80 chars or fewer, broken at word boundary, ending with `…` |
| `test_title_truncate_short_text` | Text `"Short"`, `title_max_length: 120` | `"Short"` (no truncation needed, no `…`) |
| `test_title_truncate_word_boundary` | Text `"Hello world goodbye"`, `title_max_length: 12` | `"Hello world…"` (breaks at word boundary, not mid-word) |
| `test_title_timestamp_format` | Timestamp `"2026-02-10T08:30:00Z"` | `"2026-02-10 08:30:00 UTC"` |
| `test_title_template_with_placeholders` | Template string `"Entry #{index} — {timestamp}"`, index=5 | `"Entry #5 — 2026-02-10 08:30:00 UTC"` |
| `test_title_template_missing_placeholder` | Template string `"Static title"` | `"Static title"` (no substitution needed) |
| `test_title_none_strategy` | Any text | `""` |

**Description strategies:**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_desc_truncate_basic` | Text of 500 chars, `description_max_length: 280` | 280 chars or fewer, word boundary, ending with `…` |
| `test_desc_truncate_short_text` | Text of 100 chars, `description_max_length: 280` | Full text, no `…` |
| `test_desc_truncate_word_boundary` | Text `"one two three four five"`, `description_max_length: 15` | `"one two three…"` |
| `test_desc_first_line` | Text `"Summary line\nDetail paragraph..."` | `"Summary line"` |
| `test_desc_same_mirrors_content` | Text `"Full content here"` | `"Full content here"` (identical to input) |
| `test_desc_none_strategy` | Any text | `""` |

**GUID strategies:**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_guid_sha256_deterministic` | Text `"hello"` + timestamp `"2026-02-10T08:30:00Z"`, called twice | Both calls return the same hex string |
| `test_guid_sha256_different_text` | Two calls with different text, same timestamp | Different hex strings |
| `test_guid_sha256_different_timestamp` | Two calls with same text, different timestamps | Different hex strings |
| `test_guid_sha256_format` | Any valid input | 64-character lowercase hex string |
| `test_guid_uuid4_format` | Any input | Valid UUID v4 format (`8-4-4-4-12` hex with version nibble `4`) |
| `test_guid_uuid4_not_deterministic` | Same input called twice | Two different UUIDs |
| `test_guid_timestamp_format` | Timestamp `"2026-02-10T08:30:00Z"` | `"2026-02-10T08:30:00Z"` (ISO string used as GUID) |
| `test_guid_sequential_format` | Feed title `"Server Incident Log"`, index 3 | `"server-incident-log-003"` |
| `test_guid_sequential_slug_generation` | Feed title `"My Feed — Special (Chars!)"` | Slug contains only lowercase alphanumerics and hyphens |
| `test_guid_sequential_zero_padded` | Index 1, batch size < 1000 | `"...-001"` (3-digit zero-padded) |

#### `test_cli.py` — CLI Interface

Tests the CLI by invoking `shruggie-feedtools` as a subprocess (or via the argparse entry point in-process). Verifies argument parsing, subcommand routing, output formatting, exit codes, and pipe behavior.

**Parse subcommand:**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_cli_parse_url_stdout` | `shruggie-feedtools parse --url <mock_url>` | Stdout is valid JSON with `status: "ok"`. Exit code `0`. |
| `test_cli_parse_file` | `shruggie-feedtools parse --file rss2/minimal.xml` | Stdout is valid JSON. `source.origin: "file"`. Exit code `0`. |
| `test_cli_parse_stdin` | Echo URL, pipe to `shruggie-feedtools parse --stdin` | Stdout is valid JSON. Exit code `0`. |
| `test_cli_parse_url_list` | `shruggie-feedtools parse --url-list urls.txt` (file with 2 URLs) | Stdout contains two JSON results (one per feed). Exit code `0`. |
| `test_cli_parse_output_file` | `shruggie-feedtools parse --file fixture.xml --output out.json` | `out.json` created with valid JSON. Stdout is empty. Exit code `0`. |
| `test_cli_parse_pretty` | `shruggie-feedtools parse --file fixture.xml --pretty` | Stdout JSON is indented (contains newlines and spaces). Exit code `0`. |
| `test_cli_parse_indent_custom` | `shruggie-feedtools parse --file fixture.xml --pretty --indent 4` | JSON indentation is 4 spaces. |
| `test_cli_parse_quiet` | `shruggie-feedtools parse --file fixture.xml --quiet` | Stderr is empty (no log output). Stdout is JSON only. |
| `test_cli_parse_max_items` | `shruggie-feedtools parse --file wordpress.xml --max-items 2` | Output `items` array has at most 2 entries. |
| `test_cli_parse_no_verify_ssl` | `shruggie-feedtools parse --url <url> --no-verify-ssl` | Does not fail on self-signed cert (verified via mock). |
| `test_cli_parse_timeout` | `shruggie-feedtools parse --url <url> --timeout 5` | Timeout applies to fetch (verified via mock). |
| `test_cli_parse_nonexistent_file` | `shruggie-feedtools parse --file does_not_exist.xml` | Stderr contains error message. Exit code `2`. |
| `test_cli_parse_no_input_specified` | `shruggie-feedtools parse` (no --url, --file, etc.) | Stderr contains usage help. Exit code `2`. |

**Construct subcommand:**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_cli_construct_text_arg` | `shruggie-feedtools construct --template t.json --text "Hello" --timestamp "2026-02-10T12:00:00Z"` | Stdout is valid JSON. `source.type: "constructed"`. Exit code `0`. |
| `test_cli_construct_text_stdin` | Echo text, pipe to `shruggie-feedtools construct --template t.json --text-stdin --timestamp "..."` | Stdout is valid JSON with item content from stdin. Exit code `0`. |
| `test_cli_construct_entries_file` | `shruggie-feedtools construct --template t.json --entries batch.jsonl` | Output `items` count matches JSONL line count. Exit code `0`. |
| `test_cli_construct_entries_stdin` | Cat JSONL, pipe to `shruggie-feedtools construct --template t.json --entries-stdin` | Output `items` count matches JSONL line count. Exit code `0`. |
| `test_cli_construct_output_file` | `--output out.json` | File created. Stdout empty. Exit code `0`. |
| `test_cli_construct_pretty` | `--pretty` | Output JSON is indented. |
| `test_cli_construct_missing_template` | `shruggie-feedtools construct --text "X" --timestamp "..."` (no --template) | Stderr error. Exit code `2`. |
| `test_cli_construct_invalid_template` | `--template invalid_missing_title.feedtemplate.json` | Stderr contains `TemplateValidationError` message. Exit code `2`. |
| `test_cli_construct_missing_timestamp` | `shruggie-feedtools construct --template t.json --text "X"` (no --timestamp) | Stderr error about missing timestamp. Exit code `2`. |
| `test_cli_construct_nonexistent_template` | `--template no_such_file.json` | Stderr error. Exit code `2`. |
| `test_cli_construct_bad_jsonl_entry` | JSONL file with one malformed line | Partial success: valid entries in output, warning for bad entry. Exit code `1`. |

**Global options and edge cases:**

| Test Function | Input | Expected Result |
|--------------|-------|-----------------|
| `test_cli_version` | `shruggie-feedtools --version` | Stdout contains version string matching `_version.py`. Exit code `0`. |
| `test_cli_help` | `shruggie-feedtools --help` | Stdout contains usage text with `parse` and `construct` subcommands. Exit code `0`. |
| `test_cli_parse_help` | `shruggie-feedtools parse --help` | Stdout contains parse-specific options. Exit code `0`. |
| `test_cli_construct_help` | `shruggie-feedtools construct --help` | Stdout contains construct-specific options. Exit code `0`. |
| `test_cli_unknown_subcommand` | `shruggie-feedtools frobnicate` | Stderr error. Exit code `2`. |
| `test_cli_pipe_json_to_jq` | `shruggie-feedtools parse --file fixture.xml` piped through `jq '.items[0].title'` | jq receives valid JSON and extracts field successfully |

### 17.4 Snapshot Tests

Snapshot testing is the primary mechanism for catching unintended changes to the output schema. A snapshot test runs a fixture through the full pipeline and compares the resulting JSON byte-for-byte against a committed golden file. If the output differs, the test fails — forcing the developer to either fix the regression or deliberately regenerate the snapshot and commit the diff.

#### How It Works

1. Each snapshot test calls `parse_string()` or `construct()` with a specific fixture.
2. The output dict is serialized to JSON with `pretty_print=True`, `indent=2`, and keys sorted alphabetically for deterministic ordering.
3. The serialized JSON is compared against the corresponding golden file in `tests/snapshots/`.
4. If the golden file does not exist, the test fails with a message indicating the snapshot needs to be created.
5. If the golden file exists and the output matches, the test passes silently.
6. If the golden file exists and the output differs, the test fails and prints a unified diff showing exactly which fields changed.

#### Regeneration

Running `pytest --update-snapshots` overwrites all golden files with current output. This flag should only be used intentionally — never as a way to silence failures without understanding why the output changed.

The workflow for a deliberate schema change:

1. Make the code change.
2. Run `pytest` — snapshot tests fail, showing the diff.
3. Review the diff to confirm it reflects the intended change and nothing else.
4. Run `pytest --update-snapshots` to regenerate.
5. Commit the updated golden files alongside the code change. The snapshot diffs in the pull request are how reviewers verify schema changes.

#### Snapshot Implementation

Snapshots are implemented as a pytest fixture (in `conftest.py`) rather than a third-party plugin, keeping the dependency footprint minimal:

```python
# tests/conftest.py (relevant excerpt)

import json
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"

@pytest.fixture
def assert_snapshot(request):
    """Compare output against a golden file. Create/update with --update-snapshots."""
    update = request.config.getoption("--update-snapshots", default=False)

    def _assert(output: dict, name: str, subfolder: str = ""):
        snapshot_path = SNAPSHOT_DIR / subfolder / f"{name}.json"
        serialized = json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

        if update:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(serialized, encoding="utf-8")
            return

        if not snapshot_path.exists():
            pytest.fail(f"Snapshot not found: {snapshot_path}\nRun pytest --update-snapshots to create it.")

        expected = snapshot_path.read_text(encoding="utf-8")
        if serialized != expected:
            # Show unified diff for clear failure output
            import difflib
            diff = difflib.unified_diff(
                expected.splitlines(keepends=True),
                serialized.splitlines(keepends=True),
                fromfile=f"snapshot/{name}.json",
                tofile="actual output",
            )
            pytest.fail(f"Snapshot mismatch:\n{''.join(diff)}")

    return _assert
```

The `--update-snapshots` flag is registered via `conftest.py`:

```python
def pytest_addoption(parser):
    parser.addoption("--update-snapshots", action="store_true", default=False,
                     help="Regenerate snapshot golden files from current output")
```

#### Snapshot Coverage

Every parse fixture and every construct template fixture has a corresponding snapshot. The naming convention mirrors the fixture directory structure:

| Snapshot File | Source Fixture | Pipeline |
|--------------|---------------|----------|
| `snapshots/rss2/minimal.json` | `fixtures/rss2/minimal.xml` | `parse_string()` |
| `snapshots/rss2/wordpress.json` | `fixtures/rss2/wordpress.xml` | `parse_string()` |
| `snapshots/rss2/podcast_itunes.json` | `fixtures/rss2/podcast_itunes.xml` | `parse_string()` |
| `snapshots/rss2/hairy_malformed.json` | `fixtures/rss2/hairy_malformed.xml` | `parse_string()` |
| `snapshots/rss2/financial_sec.json` | `fixtures/rss2/financial_sec.xml` | `parse_string()` |
| `snapshots/rss2/reddit.json` | `fixtures/rss2/reddit.xml` | `parse_string()` |
| `snapshots/atom10/github_releases.json` | `fixtures/atom10/github_releases.xml` | `parse_string()` |
| `snapshots/atom10/youtube_channel.json` | `fixtures/atom10/youtube_channel.xml` | `parse_string()` |
| `snapshots/atom10/statuspage.json` | `fixtures/atom10/statuspage.xml` | `parse_string()` |
| `snapshots/rss1/rdf_gov.json` | `fixtures/rss1/rdf_gov.xml` | `parse_string()` |
| `snapshots/json_feed/v1_standard.json` | `fixtures/json_feed/v1_standard.json` | `parse_string()` |
| `snapshots/wp_rest/posts_embedded.json` | `fixtures/wp_rest/posts_embedded.json` | `parse_string()` |
| `snapshots/edge_cases/mixed_case_elements.json` | `fixtures/edge_cases/mixed_case_elements.xml` | `parse_string()` |
| `snapshots/edge_cases/custom_namespace_prefixes.json` | `fixtures/edge_cases/custom_namespace_prefixes.xml` | `parse_string()` |
| `snapshots/edge_cases/bad_dates.json` | `fixtures/edge_cases/bad_dates.xml` | `parse_string()` |
| `snapshots/edge_cases/missing_fields.json` | `fixtures/edge_cases/missing_fields.xml` | `parse_string()` |
| `snapshots/edge_cases/encoding_utf8_bom.json` | `fixtures/edge_cases/encoding_utf8_bom.xml` | `parse_string()` |
| `snapshots/construct/minimal_single.json` | `templates/minimal.feedtemplate.json` + single entry | `construct()` |
| `snapshots/construct/incident_log_batch.json` | `templates/incident_log.feedtemplate.json` + `entries/batch_entries.jsonl` | `construct_batch()` |
| `snapshots/construct/changelog_with_link_pattern.json` | `templates/changelog.feedtemplate.json` + single entry | `construct()` |
| `snapshots/construct/entry_overrides.json` | `templates/incident_log.feedtemplate.json` + `entries/entries_with_overrides.jsonl` | `construct_batch()` |

Total: 21 snapshot golden files covering all parse fixtures and the primary construct scenarios.

#### What Snapshot Diffs Catch

Snapshots are intentionally comprehensive — the full output JSON, not a subset of fields. This means they catch:

- Field additions, removals, or renames in the output schema
- Changes to default values
- Date normalization regressions (e.g., a timezone offset appearing where `Z` was expected)
- Namespace prefix normalization regressions
- Thumbnail extraction logic changes
- Extension bucketing changes
- Ordering changes in arrays (categories, enclosures)
- Whitespace or encoding changes in content passthrough

The tradeoff is that snapshots are brittle by design. Any code change that touches the output will likely break at least one snapshot. This is the point — it forces every output-affecting change to be visible in code review via the snapshot diff.

---

## 18. Security

### 18.1 XML Processing

XML entity expansion (XXE) is the primary attack surface for a feed parser. The `feedparser` library disables external entity resolution by default, which neutralizes the classic XXE attack vectors: local file disclosure via `file://` entities, SSRF via `http://` entities, and denial-of-service via recursive entity expansion ("billion laughs").

shruggie-feedtools does not use any other XML parser. All XML processing goes through `feedparser`. If a future adapter needs raw XML parsing (e.g., for OPML), it must use `defusedxml` or equivalent — never `xml.etree.ElementTree` or `lxml` without explicit entity restrictions.

### 18.2 HTML Content Passthrough

Feed content fields (`content`, `description`) frequently contain raw HTML. shruggie-feedtools passes this HTML through without sanitization. This is a deliberate design decision: the tool normalizes feed structure, not content safety. Sanitization is a downstream responsibility.

This must be documented clearly in the README and API docs: **consumers rendering HTML from feed output must sanitize it before display.** Failure to do so exposes consumers to stored XSS from malicious feed content.

### 18.3 HTTP Request Security

| Concern | Mitigation |
|---------|-----------|
| SSRF (Server-Side Request Forgery) | Not applicable for CLI/GUI (user controls URLs directly). Future API service must validate and restrict target URLs — private IP ranges (`10.x`, `172.16.x`, `192.168.x`, `127.x`, `::1`), cloud metadata endpoints (`169.254.169.254`), and non-HTTP schemes must be rejected. |
| TLS verification | Enabled by default. `--no-verify-ssl` is available but logged as a warning. |
| Redirect following | Capped at 5 redirects (configurable). Prevents infinite redirect loops. |
| Response size | Capped at 10 MB (configurable). Prevents memory exhaustion from oversized responses. |
| Timeouts | Connect: 10s, read: 30s (configurable). Prevents hanging on unresponsive hosts. |
| User-Agent disclosure | Default `shruggie-feedtools/0.1.0`. Customizable. Does not leak system info. |

### 18.4 Template Safety

Templates are JSON data files, not executable code. The template engine:

- Does no string interpolation beyond `{guid}`, `{timestamp}`, and `{index}` in `link_pattern` and `title_template` fields — these are replaced by the builder, not evaluated.
- Performs no `eval()`, `exec()`, or dynamic import.
- Validates all template fields via Pydantic with strict type checking before any processing occurs.
- Rejects unknown fields (Pydantic `extra = "forbid"` on template models) to prevent accidental data injection.

### 18.5 Dependency Pinning

Runtime dependencies (`feedparser`, `httpx`, `pydantic`, `python-dateutil`) are specified with minimum version floors (`>=`) in `pyproject.toml` for flexibility. For reproducible builds, a `requirements-lock.txt` is maintained with exact pinned versions and hashes, regenerated on each dependency update.

### 18.6 Secrets and Credentials

shruggie-feedtools does not handle authentication, API keys, or credentials in any form. It fetches only publicly accessible URLs. If a future version adds authenticated source support, credentials must never appear in output JSON, log output, or error messages.

---

## 19. Performance Targets

MVP performance targets. These are verified manually during development and will be formalized into benchmarks post-MVP.

### 19.1 Parse Mode

| Operation | Target | Notes |
|-----------|--------|-------|
| Parse single local XML file (100 items) | < 200ms | Dominated by `feedparser` parse time. |
| Parse single local XML file (1000 items) | < 1.5s | Linear scaling with item count. |
| Parse single local JSON file (100 items) | < 100ms | JSON parsing is faster than XML. |
| Parse single remote URL (including fetch) | < 5s | Network-bound. Timeout defaults enforce this ceiling. |
| Batch parse 50 local files sequentially | < 10s | ~200ms per file. |
| Detection + routing (no parsing) | < 10ms | Byte sniffing and format identification only. |
| Namespace normalization pass | < 5ms | Dictionary lookup per prefixed field. |

### 19.2 Construct Mode

| Operation | Target | Notes |
|-----------|--------|-------|
| Construct single item from template | < 50ms | Template load + strategy derivation + Pydantic validation. |
| Construct batch of 100 items from JSONL | < 500ms | Template loaded once, reused per item. |
| Construct batch of 1000 items from JSONL | < 2s | Linear scaling. |
| Template load + validation | < 20ms | Pydantic model instantiation from JSON file. |

### 19.3 GUI

| Metric | Target |
|--------|--------|
| Time from click to output displayed | < 6s for remote URL, < 1s for local file |
| UI thread blocking | Never. All parse/construct operations run in background threads. |
| Output panel render (10,000 lines JSON) | < 500ms to populate the text widget. |

### 19.4 Executable Size

| Artifact | Target |
|----------|--------|
| CLI `.exe` (PyInstaller, Windows x64) | 20–35 MB |
| GUI `.exe` (PyInstaller, Windows x64) | 40–65 MB |

### 19.5 Memory

No explicit memory ceiling for MVP, but the design avoids unbounded growth:

- Response body size capped at `max_response_bytes` (default 10 MB).
- Items are processed as a list in memory — not streamed. For typical feeds (10–200 items), this is negligible. Feeds with thousands of items may consume tens of MB, which is acceptable for a CLI/GUI tool.
- Construct mode batch processing loads all JSONL entries into memory before building. For extremely large batches (100k+ entries), a streaming mode would be needed — deferred to post-MVP.

---

## 20. Future Roadmap

Items are grouped by theme rather than strict priority. Nothing here is committed — this is a direction map, not a promise.

### 20.1 Near-Term (Post-MVP)

**FastAPI HTTP service** — `/v1/parse` and `/v1/construct` endpoints wrapping the existing library functions. The architecture is already designed for this: stateless functions, Pydantic models as response schemas, `httpx` for async compatibility. The service would be the primary integration point for other ShruggieTech tools.

**OPML import** — Parse OPML subscription lists (`.opml` files) as batch input to parse mode. An OPML file contains a list of feed URLs; the tool would extract those URLs and run them through the parse pipeline. This is a natural extension of the existing `--url-list` batch mode.

**Caching layer** — Store `ETag` and `Last-Modified` headers from fetched feeds. On subsequent fetches, send conditional requests (`If-None-Match`, `If-Modified-Since`). If the server returns `304 Not Modified`, return the cached result without re-parsing. Cache backend: SQLite for the CLI/GUI, optional Redis for the API service.

**Async batch processing** — Use `asyncio` + `httpx.AsyncClient` for concurrent fetching in batch mode. Currently batch operations fetch sequentially. Async would dramatically improve throughput for large URL lists.

### 20.2 Medium-Term

**Feed generation (reverse direction)** — Produce RSS 2.0, Atom 1.0, or JSON Feed output from the shruggie-feedtools schema. This would make the tool bidirectional: parse any format in, generate any format out. The JS feedsmith project supports this and it proved useful for their users.

**Feed discovery** — Given an arbitrary webpage URL, detect feed URLs from `<link rel="alternate" type="application/rss+xml">` and similar tags. Useful as a "find the feed for this site" utility.

**`fastfeedparser` swap** — Drop-in replacement for `feedparser` with better performance. Evaluate when the library matures. The adapter layer isolates this swap — only `feedparser_adapter.py` would change.

**Additional JSON adapters** — Ghost Content API, Discourse API, Mastodon API, Bluesky AT Protocol feeds. Each would get its own adapter module following the existing pattern.

**JSON Schema export** — Auto-generate a standalone JSON Schema document from the Pydantic models. Useful for consumers who want to validate shruggie-feedtools output without importing the Python package.

### 20.3 Long-Term

**Plugin system** — Allow third-party adapters registered via entry points. A developer could write a custom adapter for a proprietary feed format, package it as a pip-installable plugin, and shruggie-feedtools would discover and use it at runtime.

**Template library** — A curated, version-controlled collection of `.feedtemplate.json` files for common use cases: incident logs, changelogs, bookmark feeds, reading notes, sensor data, social media archives. Distributed as a companion package or included in the main repo under `templates/`.

**Template inheritance** — A template extending a base template with overrides. For example, a team-specific incident log template that inherits from a base incident template but overrides the `feed.title` and `item_defaults.author`.

**Streaming construct mode** — For very large batches (100k+ entries), process JSONL entries as a stream rather than loading all into memory. Emit output incrementally.

---

## Appendix A: Platform and Tooling

### A.1 Runtime Requirements

| Requirement | Value |
|-------------|-------|
| Python version | `>=3.12` |
| Primary target OS | Windows 10/11 x64 (`.exe` artifacts) |
| Module compatibility | Windows, macOS, Linux — anywhere Python >=3.12 runs |

### A.2 Project Metadata (`pyproject.toml`)

| Field | Value |
|-------|-------|
| Build system | `hatchling` |
| Package name | `shruggie-feedtools` |
| Import name | `shruggie_feedtools` |
| License | `Apache-2.0` |
| License file | `LICENSE` (full Apache 2.0 text, obtained from https://www.apache.org/licenses/LICENSE-2.0.txt) |
| Python requires | `>=3.12` |
| CLI entry point | `shruggie-feedtools = "shruggie_feedtools.cli.main:main"` |
| Module entry point | `python -m shruggie_feedtools` (via `__main__.py`) |

### A.3 Extras

The `pyproject.toml` defines optional dependency groups:

```toml
[project.optional-dependencies]
gui = ["customtkinter>=5.2"]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.4",
    "pyinstaller>=6.0",
]
```

Install combinations:

| Command | What it installs |
|---------|-----------------|
| `pip install -e ".[dev,gui]"` | Editable install with all dependencies (used by `venv-setup` scripts during development) |

> **Note:** This project is not published to PyPI. End users should download pre-built executables from [GitHub Releases](https://github.com/shruggietech/shruggie-feedtools/releases). The `pip install -e` command above is for contributors setting up a local development environment only.

### A.4 Code Style and Linting

`ruff` handles both linting and formatting. Configuration in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]

[tool.ruff.format]
quote-style = "double"
```

Rule sets: pycodestyle errors/warnings (`E`, `W`), pyflakes (`F`), isort-compatible import sorting (`I`), pyupgrade for Python 3.12+ idioms (`UP`), bugbear (`B`), simplify (`SIM`), and Ruff-specific rules (`RUF`).

No separate `black`, `isort`, or `flake8` — `ruff` replaces all three.

### A.5 Typography (GUI)

| Usage | Font | Fallback |
|-------|------|----------|
| Output panel (JSON) | JetBrains Mono | Consolas, monospace |
| UI labels and controls | Inter | Segoe UI, system sans-serif |
| Window title bar | Space Grotesk | Inter, system sans-serif |

Fonts are not bundled. The GUI uses system-installed fonts with fallback chains. CustomTkinter handles font configuration via `CTkFont`.

### A.6 Version Management

The version string lives in exactly one place:

```
src/shruggie_feedtools/_version.py
```

```python
__version__ = "0.1.0"
```

All other version references read from this file:

- `pyproject.toml` uses `dynamic = ["version"]` with `[tool.hatch.version] path = "src/shruggie_feedtools/_version.py"`
- The CLI `--version` flag reads `__version__` at runtime
- The build scripts extract it via regex for naming release artifacts
- The `User-Agent` header interpolates it at runtime

---

## Appendix B: Template Quick Reference

### B.1 Minimal Valid Template

The smallest template that passes validation. Every omitted field receives its documented default.

```json
{
  "template_version": "1.0",
  "feed": {
    "title": "My Feed"
  },
  "item_mapping": {
    "text_target": "content",
    "title_strategy": "first_line",
    "guid_strategy": "sha256"
  }
}
```

### B.2 All Fields with Defaults

Every field shown, set to its default value. Copy this as a starting point and change what you need.

```json
{
  "template_version": "1.0",

  "feed": {
    "title": "",
    "link": "",
    "description": "",
    "language": "",
    "author": "",
    "image": "",
    "categories": [],
    "ttl": null
  },

  "item_mapping": {
    "text_target": "content",
    "title_strategy": "first_line",
    "title_max_length": 120,
    "description_strategy": "truncate",
    "description_max_length": 280,
    "guid_strategy": "sha256",
    "link_pattern": null
  },

  "item_defaults": {
    "author": "",
    "categories": [],
    "thumbnail": "",
    "link": "",
    "extensions": {}
  }
}
```

### B.3 Strategy Quick Reference

**`item_mapping.text_target`** — Where the raw text input goes:

| Value | `content` field | `description` field |
|-------|----------------|-------------------|
| `"content"` | Full text | Derived via `description_strategy` |
| `"description"` | `""` | Full text |
| `"both"` | Full text | Derived via `description_strategy` |

**`item_mapping.title_strategy`** — How the item title is derived:

| Value | Behavior |
|-------|----------|
| `"first_line"` | First line of text, up to `title_max_length` |
| `"truncate"` | First `title_max_length` chars, word boundary |
| `"timestamp"` | Formatted timestamp as title |
| `"template"` | `item_defaults.title_template` with `{timestamp}` and `{index}` |
| `"none"` | Empty string |

**`item_mapping.description_strategy`** — How the description is derived:

| Value | Behavior |
|-------|----------|
| `"truncate"` | First `description_max_length` chars, word boundary |
| `"first_line"` | First line of text |
| `"same"` | Full text (mirrors content) |
| `"none"` | Empty string |

**`item_mapping.guid_strategy`** — How GUIDs are generated:

| Value | Format | Deterministic |
|-------|--------|---------------|
| `"sha256"` | 64-char hex digest of `text + timestamp` | Yes |
| `"uuid4"` | Random UUID v4 | No |
| `"timestamp"` | ISO 8601 string | Yes (not unique across same-timestamp items) |
| `"sequential"` | `{feed-title-slug}-{zero-padded-index}` | Yes (within a batch) |

### B.4 Precedence Order

When a field could come from multiple sources, the first available value wins:

1. **Per-entry override** (JSONL field) — highest priority
2. **Template `item_defaults`**
3. **Derived value** (from strategy)
4. **Schema default** (`""`, `[]`, `null`, `false`) — lowest priority

Fields that are always derived and never overridable from `item_defaults`: `pub_date` (from timestamp input), `guid` (from strategy), `content`/`description` (from text input + strategy).

---

## Appendix C: Construct Mode Use Cases

Practical examples showing how construct mode maps to real-world scenarios. Each includes the template design rationale and a representative CLI invocation.

### C.1 Server Incident Log

A monitoring script detects anomalies and pipes alert text into shruggie-feedtools to build a structured incident feed. Downstream systems (dashboards, Slack bots, PagerDuty integrations) consume the JSON output.

**Template design**: `timestamp` title strategy so each entry is titled by when it happened. `sha256` GUIDs for idempotent deduplication — if the same alert fires twice for the same event, the GUID collision signals a duplicate. Short `description_max_length` for Slack-friendly previews.

```json
{
  "template_version": "1.0",
  "feed": {
    "title": "web-03 Incident Feed",
    "link": "https://status.example.com",
    "description": "Automated alerts from web-03 monitoring",
    "language": "en-us"
  },
  "item_mapping": {
    "text_target": "content",
    "title_strategy": "timestamp",
    "description_strategy": "truncate",
    "description_max_length": 140,
    "guid_strategy": "sha256"
  },
  "item_defaults": {
    "author": "monitoring-agent",
    "categories": ["incident", "web-03"]
  }
}
```

```bash
echo "Elevated latency on port 443. p99 > 2s for 5 consecutive minutes." | \
    shruggie-feedtools construct \
        --template web03-incidents.feedtemplate.json \
        --text-stdin \
        --timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### C.2 Development Changelog

A git post-commit hook extracts the commit message and pipes it through construct mode. The resulting feed is appended to a growing JSONL file, which is periodically batch-constructed into a full changelog feed.

**Template design**: `first_line` title strategy (commit subject line becomes the title, commit body becomes the content). `link_pattern` with `{guid}` generates a permalink per entry. `sha256` GUID ensures the same commit message + timestamp always produces the same entry.

```json
{
  "template_version": "1.0",
  "feed": {
    "title": "shruggie-feedtools Changelog",
    "link": "https://github.com/shruggietech/shruggie-feedtools",
    "description": "Development changelog"
  },
  "item_mapping": {
    "text_target": "both",
    "title_strategy": "first_line",
    "title_max_length": 80,
    "description_strategy": "truncate",
    "description_max_length": 200,
    "guid_strategy": "sha256",
    "link_pattern": "https://github.com/shruggietech/shruggie-feedtools/commits/{guid}"
  },
  "item_defaults": {
    "author": "wthompson",
    "categories": ["changelog"]
  }
}
```

```bash
# Single entry from commit hook
shruggie-feedtools construct \
    --template changelog.feedtemplate.json \
    --text "$(git log -1 --format=%B)" \
    --timestamp "$(git log -1 --format=%cI)"

# Batch from accumulated JSONL
shruggie-feedtools construct \
    --template changelog.feedtemplate.json \
    --entries changelog-entries.jsonl \
    --output changelog.json --pretty
```

### C.3 Bookmark Feed

A browser bookmarklet or extension saves the current page URL and title as a JSONL entry. Periodically, the entries are batch-constructed into a feed of saved links.

**Template design**: `text_target: "description"` because the text is a short annotation, not a full article body. `truncate` title strategy for when the annotation is used as the title. `uuid4` GUIDs because the same URL bookmarked twice should produce two distinct entries (intentional re-saves).

```json
{
  "template_version": "1.0",
  "feed": {
    "title": "Saved Links",
    "link": "https://bookmarks.example.com",
    "description": "Bookmarked pages"
  },
  "item_mapping": {
    "text_target": "description",
    "title_strategy": "first_line",
    "title_max_length": 100,
    "description_strategy": "same",
    "guid_strategy": "uuid4"
  },
  "item_defaults": {
    "author": "wthompson",
    "categories": ["bookmark"]
  }
}
```

Entry JSONL (note per-entry `link` overrides):

```jsonl
{"text": "Excellent writeup on feed normalization", "timestamp": "2026-02-10T09:00:00Z", "link": "https://example.com/feed-normalization"}
{"text": "Useful Pydantic v2 migration guide", "timestamp": "2026-02-10T14:30:00Z", "link": "https://docs.pydantic.dev/latest/migration/"}
```

### C.4 Sensor Data Log

An IoT device or data pipeline emits periodic readings. Each reading is a single text line (e.g., `"temperature=72.4F humidity=45%"`) with a timestamp. The feed provides a structured, queryable log.

**Template design**: `timestamp` title strategy since sensor readings don't have natural titles. `sequential` GUIDs for simple monotonic ordering. `none` description strategy — the reading is short enough that `content` alone suffices.

```json
{
  "template_version": "1.0",
  "feed": {
    "title": "Garage Sensor Readings",
    "description": "Temperature and humidity from garage sensor array",
    "language": "en-us"
  },
  "item_mapping": {
    "text_target": "content",
    "title_strategy": "timestamp",
    "description_strategy": "none",
    "guid_strategy": "sequential"
  },
  "item_defaults": {
    "author": "sensor-array-01",
    "categories": ["sensor", "garage"]
  }
}
```

```bash
# Continuous pipeline: sensor emits JSONL to stdout, construct reads from stdin
sensor-reader --format jsonl | \
    shruggie-feedtools construct \
        --template garage-sensor.feedtemplate.json \
        --entries-stdin \
        --output readings.json
```

### C.5 Social Media Archive

An export script pulls posts from a social platform API and converts them to JSONL. Construct mode produces a portable, platform-independent archive feed.

**Template design**: `truncate` title strategy since social posts don't have separate titles. `sha256` GUIDs so re-running the export with the same data produces identical output (idempotent archiving). Per-entry overrides carry the original post URL as `link`.

```json
{
  "template_version": "1.0",
  "feed": {
    "title": "Social Archive — @wthompson",
    "link": "https://archive.example.com/wthompson",
    "description": "Archived posts"
  },
  "item_mapping": {
    "text_target": "both",
    "title_strategy": "truncate",
    "title_max_length": 80,
    "description_strategy": "truncate",
    "description_max_length": 280,
    "guid_strategy": "sha256"
  },
  "item_defaults": {
    "author": "wthompson",
    "categories": ["archive"]
  }
}
```

```bash
python export-posts.py --format jsonl | \
    shruggie-feedtools construct \
        --template social-archive.feedtemplate.json \
        --entries-stdin \
        --output archive.json --pretty
```
