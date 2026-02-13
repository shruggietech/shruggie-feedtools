# Release Notes — shruggie-feedtools v0.1.6

**Release Date:** 2026-02-13
**Status:** Patch release (Alpha)

---

## Overview

Cleanup release that removes non-functional JSON Feed and WordPress REST API input adapters after multiple failed implementation attempts. The codebase is now streamlined to XML-based feed parsing only (RSS 2.0, RSS 1.0/RDF, Atom 1.0, RSS 0.9x, Atom 0.3). JSON output remains the sole output format — unchanged.

---

## Breaking Changes

### Removed: JSON Feed and WordPress REST API Input Support

- **Removed all JSON Feed (input) and WordPress REST API (input) adapters, detection logic, fixtures, and tests** — These features were persistently non-functional after multiple implementation attempts and have been fully excised from the codebase.
- **Output format is unchanged** — All output is still JSON. Only the *input* JSON Feed and WP REST adapters have been removed.
- Files removed: `json_feed_adapter.py`, `wp_rest_adapter.py`, and associated fixture/snapshot directories
- Enum values `"json_feed"` and `"wp_rest"` removed from `source.type`
- Detection logic removed: `_detect_json_type()`, `derive_wp_rest_posts_url()`, JSON-path routing in detector
- Parser routing for JSON Feed and WP REST removed from `_route_to_adapter()`
- Dead code removed: JSON Feed attachments mapping in `_normalize_enclosures()`
- CLI help text and examples updated to reflect XML-only input support
- Documentation updated throughout: README, spec, plan, and release notes

### Supported Input Formats (as of v0.1.6)

| Format | Example Sources |
|---|---|
| RSS 2.0 | Most blogs, podcasts, news sites |
| RSS 1.0 / RDF | Older syndication feeds |
| RSS 0.91 / 0.92 | Legacy feeds |
| Atom 1.0 | GitHub releases, YouTube, status pages |
| Atom 0.3 | Older Atom feeds |

---

## Test Results

- **276 tests passing** (down from 278 in v0.1.5 — net removal of 46 tests from deleted adapters, offset by prior additions)
- All remaining XML-based adapter, detector, parser, normalizer, schema, CLI, construct, and template tests pass

---

## Release Artifacts

| Artifact | Description |
|---|---|
| `shruggie-feedtools-cli-0.1.6-win-x64.exe` | Standalone Windows CLI executable |
| `shruggie-feedtools-gui-0.1.6-win-x64.exe` | Standalone Windows GUI executable |

Download from [GitHub Releases](https://github.com/shruggietech/shruggie-feedtools/releases).

> **Windows users:** After downloading, you may need to right-click the `.exe` → **Properties** → check **"Unblock"** → **OK** before Windows will let you run it.

---

## Upgrade Notes

- JSON Feed and WP REST API input URLs will no longer parse — these features have been removed
- No schema changes to existing output fields; no API changes for XML-based feed parsing
- Drop-in replacement for v0.1.5 for all XML-based feed workflows
- Download the latest `.exe` from [GitHub Releases](https://github.com/shruggietech/shruggie-feedtools/releases) — no pip install required
- HTTP requests now correctly identify as `shruggie-feedtools/0.1.6`

---

## Requirements

- Windows 10/11 x64 (for standalone executables — no Python needed)
- Python 3.12 or later (for development/contributor use only)

### Runtime Dependencies

- `feedparser >= 6.0`
- `httpx >= 0.27`
- `pydantic >= 2.0`
- `python-dateutil >= 2.9`

### Optional (development only)

- `customtkinter >= 5.2` (for GUI)
- `pygments >= 2.17` (for GUI syntax highlighting)
- `Pillow >= 10.0` (for robust favicon display)

---

## Known Limitations

- GUI executable is Windows-only in this release
- No CI test gate prior to release — tests are run locally (276/276 passing)

---

## License

Apache License 2.0
