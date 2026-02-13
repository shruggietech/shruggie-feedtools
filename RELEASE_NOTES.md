# Release Notes — shruggie-feedtools v0.1.2

**Release Date:** 2026-02-13
**Status:** Patch release (Alpha)

---

## Overview

Enhancement release adding a Settings panel, debug logging across the entire codebase, theme management, output font-size control, and icon/taskbar fixes.

---

## New Features

### GUI: Settings Tab

- **Application Theme** — New "Settings" tab in the left sidebar with a segmented button to switch between Auto (Default), Light, and Dark themes. Theme changes are applied immediately to the output editor (background, foreground, syntax highlighting, gutter, scrollbars).
- **Debug Logging Toggle** — Enable/disable file-based debug logging from within the GUI. When active, detailed DEBUG-level messages are written to a `.log` file next to the executable. The log file path is displayed in the Settings panel.
- **Output Font Size** — Numeric spinbox (up/down arrows + typed entry) to adjust the output viewer font size between 8–32 pt. Out-of-range values are gracefully clamped to the nearest limit; a debug log message is emitted when clamping occurs.

### GUI: Theming & Scrollbars

- **Dynamic scrollbar recoloring** — Replaced `tk.Scrollbar` with `ctk.CTkScrollbar` so scrollbars automatically adapt to the current light/dark color scheme.
- **Full editor theme palette** — Dark and light color dictionaries for editor background/foreground, gutter, cursor, selection, and all JSON syntax-highlight token colors.

### CLI: Debug Logging

- **`--debug` flag** — Added to both `parse` and `construct` subcommands. When active, writes DEBUG-level logs to `<executable_basename>.log` in the same directory as the executable/script.

### Debug Logging Infrastructure

- Comprehensive debug logging added to **all core modules, adapters, and construct modules**:
  - `core/parser.py` — parse_string, parse_file, parse_url, adapter routing
  - `core/fetcher.py` — HTTP request details, response status, retries
  - `core/detector.py` — feed type detection paths and results
  - `core/normalizer.py` — feed and item normalization entry points
  - `core/dates.py` — epoch value handling
  - `adapters/feedparser_adapter.py` — version detection, entry count
  - `adapters/json_feed_adapter.py` — feed title, item count
  - `adapters/wp_rest_adapter.py` — post count, base URL
  - `construct/builder.py` — batch size, template title
  - `construct/template.py` — template loading source
  - `construct/entry.py` — JSONL line count

## Bug Fixes

- **Fixed: Favicon not appearing in title bar/taskbar** — Corrected path resolution (`parents[2]` → `parents[3]`) in `_apply_icon()` to properly locate `brand/favicon.ico` from the nested `gui/` package.
- **Fixed: Windows taskbar showing Python icon** — Added `SetCurrentProcessExplicitAppUserModelID` via ctypes before window creation, plus `wm_iconphoto` via PIL/Pillow for robust taskbar icon display.
- **Fixed: Pylance lint errors** — Suppressed false-positive "possibly unbound" warnings for optional PIL imports that are already guarded by a runtime `_HAS_PIL` check.

## PyInstaller Spec Updates

- Both GUI and CLI `.spec` files now include `brand/favicon.ico` in `datas` for frozen builds.
- Both `.spec` files set `icon='brand/favicon.ico'` on the EXE for proper Windows executable icon.

---

## Test Results

- **307 tests passing** (unchanged from v0.1.1 — all existing tests continue to pass)

---

## Release Artifacts

| Artifact | Description |
|---|---|
| `shruggie-feedtools-cli-0.1.2-win-x64.exe` | Standalone Windows CLI executable |
| `shruggie-feedtools-gui-0.1.2-win-x64.exe` | Standalone Windows GUI executable |
| `shruggie_feedtools-0.1.2.tar.gz` | Source distribution |
| `shruggie_feedtools-0.1.2-py3-none-any.whl` | Python wheel |

---

## Upgrade Notes

- Drop-in replacement for v0.1.1 — no schema changes, no API changes
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
