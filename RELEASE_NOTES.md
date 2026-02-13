# Release Notes — shruggie-feedtools v0.1.5

**Release Date:** 2026-02-13
**Status:** Patch release (Alpha)

---

## Overview

Targeted reliability release resolving two persistent issues from v0.1.4: GUI favicons not surviving CustomTkinter's startup icon overrides, and a stale hardcoded user-agent string. Also eliminates recurring snapshot maintenance caused by version bumps and removes non-functional JSON Feed and WP REST input support.

---

## Bug Fixes

### Removed: JSON Feed and WordPress REST API Input Support

- **Removed all JSON Feed (input) and WordPress REST API (input) adapters, detection logic, fixtures, and tests** — These features were persistently non-functional after multiple implementation attempts. Input parsing now supports XML-based feeds only (RSS 2.0, RSS 1.0/RDF, Atom 1.0, RSS 0.9x, Atom 0.3).
- **Output format is unchanged** — All output is still JSON. Only the *input* JSON Feed and WP REST adapters have been removed.
- Files removed: `json_feed_adapter.py`, `wp_rest_adapter.py`, `tests/fixtures/json_feed/`, `tests/fixtures/wp_rest/`, `tests/snapshots/json_feed/`, `tests/snapshots/wp_rest/`
- Enum values `"json_feed"` and `"wp_rest"` removed from `source.type`

### GUI Favicon — Win32 API Override

- **Fixed: Favicons still not appearing after 3+ prior attempts** — Replaced the unreliable multi-timer race (4 staggered `after()` calls) with a definitive approach:
  - On Windows, uses Win32 API (`LoadImageW` + `SendMessageW` with `WM_SETICON`) via ctypes to set both ICON_SMALL (16×16) and ICON_BIG (32×32) at the OS/window-manager level, completely bypassing tkinter
  - After applying, monkey-patches `iconbitmap` to a no-op so CustomTkinter can never override the icon again
  - Falls back to standard tkinter `iconbitmap` + `wm_iconphoto` on non-Windows platforms

### Hardcoded User-Agent Fixed

- **Fixed: HTTP User-Agent reporting `shruggie-feedtools/0.1.1` regardless of actual version** — `ParserConfig.user_agent` now uses a `field(default_factory=...)` that reads `__version__` at runtime instead of a hardcoded string. The user-agent will always match the installed version going forward.

---

## Test Infrastructure

### Version-Resilient Snapshots

- **Fixed: Snapshot tests breaking on every version bump** — The `assert_snapshot` fixture in `conftest.py` now normalizes `shruggie-feedtools/X.Y.Z` to a stable placeholder before comparing, so construct snapshots no longer fail when `_version.py` is bumped. Supports semver and pre-release suffixes.

### New Tests

| Area | Tests Added | Description |
|---|---|---|
| `test_detector.py` | 3 | Content-type fallback, BOM handling, XML detection |
| **Total** | **3 new** | **Tests passing** |

---

## Release Artifacts

| Artifact | Description |
|---|---|
| `shruggie-feedtools-cli-0.1.5-win-x64.exe` | Standalone Windows CLI executable |
| `shruggie-feedtools-gui-0.1.5-win-x64.exe` | Standalone Windows GUI executable |

Download from [GitHub Releases](https://github.com/shruggietech/shruggie-feedtools/releases).

> **Windows users:** After downloading, you may need to right-click the `.exe` → **Properties** → check **"Unblock"** → **OK** before Windows will let you run it.

---

## Upgrade Notes

- Drop-in replacement for v0.1.4 — no schema changes to existing output fields, no API changes for XML-based feed parsing
- Download the latest `.exe` from [GitHub Releases](https://github.com/shruggietech/shruggie-feedtools/releases) — no pip install required
- JSON Feed and WP REST API input URLs will no longer parse (these features have been removed)
- GUI favicon should now persist reliably on Windows
- HTTP requests now correctly identify as `shruggie-feedtools/0.1.5`

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
- No CI test gate prior to release — tests are run locally (317/317 passing)

---

## License

Apache License 2.0
