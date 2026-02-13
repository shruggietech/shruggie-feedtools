# shruggie-feedtools

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

Python module that normalizes web feed data from diverse sources — RSS, Atom, JSON Feed, WordPress REST API, and other time-sequenced web endpoints — into a single, predictable JSON schema. It also constructs schema-compliant feed output from arbitrary text input using template files. Ships as a CLI tool and a standalone Windows GUI application, distributed as pre-built executables via GitHub Releases.

---

## Core Capabilities

### Parse Mode

Ingest feeds from URLs, files, or raw strings across multiple formats (RSS 2.0, RSS 1.0, Atom 1.0, JSON Feed, WordPress REST) and normalize them into a single predictable JSON schema. Every parsed feed produces the same output structure regardless of the source format.

### Construct Mode

Take raw text content, a timestamp, and a template file, and produce schema-compliant JSON feed output. This enables users to create feeds from arbitrary data sources that don't natively expose a feed format. Parsed feeds and constructed feeds are interchangeable downstream.

---

## Installation

### Download (recommended)

Grab the latest `.exe` from the [GitHub Releases](https://github.com/shruggietech/shruggie-feedtools/releases) page:

| Artifact | Description |
|----------|-------------|
| `shruggie-feedtools-cli-{version}-win-x64.exe` | Standalone CLI executable (Windows x64) |
| `shruggie-feedtools-gui-{version}-win-x64.exe` | Standalone GUI executable (Windows x64, includes CLI) |

> **Windows users:** After downloading, you may need to right-click the `.exe` → **Properties** → check **"Unblock"** → **OK** before Windows will let you run it. This is normal for executables downloaded from the internet.

Place the `.exe` anywhere on your system and run it directly — no Python installation required.

### Development setup (contributors only)

```bash
git clone https://github.com/shruggietech/shruggie-feedtools.git
cd shruggie-feedtools
```

**Windows (PowerShell):**

```powershell
./scripts/venv-setup.ps1
```

**Linux/macOS:**

```bash
./scripts/venv-setup.sh
```

This creates a `.venv`, installs all dependencies, and sets up the project for local development.

---

## Quick Start

### Parse a URL

```bash
shruggie-feedtools parse --url https://example.com/feed.xml --pretty
```

### Parse a local file

```bash
shruggie-feedtools parse --file path/to/feed.xml --pretty
```

### Construct a single item

```bash
shruggie-feedtools construct \
  --template my.feedtemplate.json \
  --text "Server restarted after kernel update." \
  --timestamp "2026-02-11T12:00:00Z" \
  --pretty
```

### Construct a batch from JSONL

```bash
shruggie-feedtools construct \
  --template my.feedtemplate.json \
  --entries entries.jsonl \
  --pretty
```

### Python API

```python
from shruggie_feedtools import parse_url, parse_file, construct, construct_batch

# Parse a remote feed
result = parse_url("https://example.com/feed.xml")

# Parse a local file
result = parse_file("path/to/feed.xml")

# Construct a single-item feed
result = construct(
    text="Server restarted after kernel update.",
    timestamp="2026-02-11T12:00:00Z",
    template="my.feedtemplate.json",
)

# Construct a batch feed from a JSONL file
result = construct_batch(
    entries="entries.jsonl",
    template="my.feedtemplate.json",
)
```

---

## CLI Reference

### `shruggie-feedtools parse`

Parse web feeds and normalize them to JSON.

| Flag | Description |
|------|-------------|
| `--url URL` | Parse a single remote feed URL |
| `--url-list FILE` | Parse URLs from a file (one per line) |
| `--file FILE` | Parse a single local file |
| `--files FILE [FILE ...]` | Parse multiple local files |
| `--dir DIR` | Parse all feed files in a directory |
| `--stdin` | Read URLs from stdin |
| `--output FILE` | Write JSON to file (default: stdout) |
| `--output-dir DIR` | Write individual `.json` files to directory (batch) |
| `--pretty` | Pretty-print JSON output |
| `--indent N` | Indentation level (default: 2) |
| `--quiet` | Suppress logs; only emit JSON |
| `--timeout SECONDS` | HTTP timeout in seconds (default: 30) |
| `--user-agent STRING` | Custom User-Agent header |
| `--no-verify-ssl` | Disable SSL certificate verification |
| `--max-items N` | Limit number of items per feed |

### `shruggie-feedtools construct`

Construct schema-compliant feeds from text content and templates.

| Flag | Description |
|------|-------------|
| `--template FILE` | Path to `.feedtemplate.json` file (**required**) |
| `--text STRING` | Text content for a single item |
| `--text-stdin` | Read text from stdin (single item) |
| `--entries FILE` | JSONL file with multiple entries |
| `--entries-stdin` | Read JSONL entries from stdin |
| `--timestamp STRING` | Timestamp for the item (required for single-item modes) |
| `--output FILE` | Write JSON to file (default: stdout) |
| `--pretty` | Pretty-print JSON output |
| `--indent N` | Indentation level (default: 2) |
| `--quiet` | Suppress logs; only emit JSON |

### Global options

| Flag | Description |
|------|-------------|
| `--version` | Show version and exit |
| `-h`, `--help` | Show help and exit |

---

## Python API Reference

### Parse functions

```python
parse(input_value: str, config=None) -> dict
```
Convenience parser — accepts a URL, file path, or raw content string. Automatically routes to the appropriate parser.

```python
parse_url(url: str, config=None) -> dict
```
Fetch and parse a feed from a URL.

```python
parse_file(path: str | Path, config=None) -> dict
```
Parse a feed from a local file.

```python
parse_string(content: str | bytes, source_url=None, config=None) -> dict
```
Parse feed content from a string or bytes.

```python
parse_urls(urls: list[str], config=None) -> list[dict]
```
Parse multiple feeds from URLs. Returns a list of response dicts.

```python
parse_files(paths: list[str | Path], config=None) -> list[dict]
```
Parse multiple feeds from local files.

### Construct functions

```python
construct(text: str, timestamp: str, template) -> dict
```
Construct a single-item feed from text, a timestamp, and a template. Template can be a file path, dict, or pre-loaded `FeedTemplate`.

```python
construct_batch(entries, template) -> dict
```
Construct a multi-item feed from entries and a template. Entries can be a list of dicts or a path to a JSONL file.

---

## Supported Formats

| Source Category | Examples | Format |
|----------------|----------|--------|
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

---

## Template Quick Reference

### Minimal valid template

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

### Strategy summary

| Strategy field | Options |
|---------------|---------|
| `text_target` | `content`, `description`, `both` |
| `title_strategy` | `first_line`, `truncate`, `timestamp`, `template`, `none` |
| `description_strategy` | `truncate`, `first_line`, `same`, `none` |
| `guid_strategy` | `sha256`, `uuid4`, `timestamp`, `sequential` |

---

## Development

### Clone and set up

```bash
git clone https://github.com/shruggietech/shruggie-feedtools.git
cd shruggie-feedtools
```

### Virtual environment setup

**Windows (PowerShell):**

```powershell
./scripts/venv-setup.ps1
```

**Linux/macOS:**

```bash
./scripts/venv-setup.sh
```

### Running tests

```bash
pytest tests/ -v
```

### Building executables

**Windows (PowerShell):**

```powershell
./scripts/build.ps1 -Release
```

This produces CLI and GUI `.exe` files in `dist/release/`.

---

## License

[Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) — see [LICENSE](LICENSE) for full text.

---

## Specification

For full technical details, see [shruggie-feedtools-spec.md](shruggie-feedtools-spec.md).
