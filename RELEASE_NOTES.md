# Release Notes — shruggie-feedtools v0.1.5

**Release Date:** 2026-02-13
**Status:** Patch release (Alpha)

---

## Overview

Targeted reliability release resolving two persistent issues from v0.1.4: WordPress REST API index URLs failing to parse, and GUI favicons not surviving CustomTkinter's startup icon overrides. Also fixes a stale hardcoded user-agent string and eliminates recurring snapshot maintenance caused by version bumps.

---

## Bug Fixes

### WordPress REST API Index URL Auto-Discovery

- **Fixed: "Parse" failing for WP REST root URLs** — Entering URLs like `https://example.com/wp-json/wp/v2` or `https://example.com/wp-json/` previously returned "Response does not match any known feed format" because those endpoints return API index/discovery JSON, not post data. The detector now recognizes these responses as `wp_rest_index` and the parser auto-discovers the correct `/posts?_embed` endpoint, transparently re-fetching and parsing the actual posts.
- **Supports two WP REST index patterns:**
  - Namespace index (`/wp-json/wp/v2`) — identified by `namespace` + `routes` keys
  - Site root (`/wp-json/`) — identified by `namespaces` array containing `wp/*` entries
- **New helper:** `derive_wp_rest_posts_url()` maps index URLs to their posts endpoint

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
| `test_detector.py` | 3 | WP REST namespace index, site root, and negative case |
| `test_detector.py` | 6 | `derive_wp_rest_posts_url()` URL derivation (namespace, root, subdir, negative) |
| **Total** | **9 new** | **326 total tests passing** |

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

- Drop-in replacement for v0.1.4 — no schema changes, no API changes
- Download the latest `.exe` from [GitHub Releases](https://github.com/shruggietech/shruggie-feedtools/releases) — no pip install required
- WP REST API root/index URLs that previously failed will now auto-discover and parse posts
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
