# Release Notes — shruggie-feedtools v0.1.1

**Release Date:** 2026-02-13
**Status:** Patch release (Alpha)

---

## Overview

Bug-fix and enhancement release addressing critical issues found in v0.1.0.

---

## Bug Fixes

- **Fixed: Construct mode completely non-functional in GUI** — Switching from Parse to Construct left stale widget references that silently crashed the action handler and permanently locked the busy state. Mode switching now properly cleans up all widget attributes, and `_set_busy` / `_find_action_buttons` guard against dead widgets via `winfo_exists()`.
- **Fixed: Thread-safety violation in Parse GUI flow** — Parse input values are now captured on the main thread before dispatching to the background worker, preventing potential tkinter cross-thread access errors.
- **Fixed: JSON feed detection too strict** — WordPress REST responses without `_links` (stripped by CDN/caching layers) and JSON Feed documents with bare version strings (`"1.0"` / `"1.1"` instead of full jsonfeed.org URL) are now correctly identified. Unrecognized JSON payloads now emit diagnostic `logger.debug()` output.

## Enhancements

### GUI Output Panel

- **Syntax highlighting** — JSON output is color-coded (keys, strings, numbers, booleans, punctuation) using a VS Code dark+ inspired palette via Pygments
- **Line numbers** — Synchronized gutter with line numbers along the left side
- **Editable output** — Output text can be manually edited; highlighting re-applies automatically with debounce
- **Clear button** — Dedicated button to clear the output area; output also auto-clears before each Parse or Construct action
- **Minify/Pretty toggle** — Independent toggle button to reformat current output between indented and single-line minified JSON

### GUI Branding

- **Window icon** — Application title bar and Windows taskbar now display the shruggie-feedtools favicon (works in both dev and PyInstaller-bundled contexts)

## Dependency Changes

- Added `pygments >= 2.17` to `[gui]` optional dependencies

## Test Results

- **307 tests passing** (up from 301 in v0.1.0 — 7 new detector tests added)

---

## Release Artifacts

| Artifact | Description |
|---|---|
| `shruggie-feedtools-cli-0.1.1-win-x64.exe` | Standalone Windows CLI executable |
| `shruggie-feedtools-gui-0.1.1-win-x64.exe` | Standalone Windows GUI executable |
| `shruggie_feedtools-0.1.1.tar.gz` | Source distribution |
| `shruggie_feedtools-0.1.1-py3-none-any.whl` | Python wheel |

---

## Upgrade Notes

- Drop-in replacement for v0.1.0 — no schema changes, no API changes
- GUI users: download the new `.exe` and replace the old one
- pip users: `pip install --upgrade shruggie-feedtools[gui]`

---

## Requirements

- Python 3.12 or later (for library/CLI usage via pip)
- Windows 10/11 x64 (for standalone executables)

### Runtime Dependencies

- `feedparser >= 6.0`
- `httpx >= 0.27`
- `pydantic >= 2.0`
- `python-dateutil >= 2.9`

### Optional

- `customtkinter >= 5.2` (for GUI: `pip install shruggie-feedtools[gui]`)
- `pygments >= 2.17` (for GUI syntax highlighting; included in `[gui]` extras)

---

## Known Limitations

- PyPI publishing is not yet configured; install from source or use the standalone executables
- GUI executable is Windows-only in this release
- No CI test gate prior to release — tests are run locally (307/307 passing)

---

## License

Apache License 2.0
