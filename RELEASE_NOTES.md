# Release Notes — shruggie-feedtools v0.1.3

**Release Date:** 2026-02-13
**Status:** Patch release (Alpha)

---

## Overview

UI polish release addressing eight GUI issues: file picker usability, copy feedback, per-tab output persistence, Settings layout, font sizing, text contrast, active tab indicator, and favicon reliability. Also includes test maintenance fixes.

---

## Bug Fixes

### GUI: File Picker Filter

- **Fixed: Template browser too restrictive** — The Construct template file picker now defaults to showing all `*.json` files instead of only `*.feedtemplate.json`. Feed template and all-files filters remain as secondary options.

### GUI: Copy Button Feedback

- **Fixed: No indication on copy** — Pressing the "Copy" button now flashes green with "Copied!" text for 1.5 seconds, then reverts to its default appearance.

### GUI: Separate Output States

- **Fixed: Shared output between Parse and Construct** — Parse and Construct tabs now maintain independent output contents. Switching tabs saves the current output and restores the previous output for the target tab.

### GUI: Settings Full Page

- **Fixed: Settings overlaid on output panel** — The Settings tab now hides the output panel entirely via `grid_remove()`, presenting a clean full-page layout. Output content is preserved and restored when returning to Parse or Construct.

### GUI: Construct Text Input Font

- **Fixed: Construct text area font too small** — The Construct text input now uses a dedicated fixed-size 12pt font, independent of the output font size control in Settings.

### GUI: Settings Text Contrast

- **Fixed: Settings description text hard to read** — All description labels on the Settings page now use adaptive `text_color=("gray30", "gray70")` instead of hardcoded `"gray"`, providing proper contrast in both light and dark modes.

### GUI: Active Tab Indicator

- **Fixed: No visual indicator for active tab** — The active sidebar button is now highlighted with a darker blue fill (`#144870` dark / `#1a5c9e` light), matching the hover color. Inactive buttons use the default color.

### GUI: Favicon Display

- **Fixed: Favicon still not appearing** — Comprehensive favicon overhaul:
  - Deferred `_apply_icon()` to `self.after(200, ...)` so it runs after CustomTkinter completes its own window initialization
  - Re-applies `iconbitmap()` after a 300ms delay to override CTk's default icon
  - Added PNG fallback icon (`brand/favicon.png`) for `wm_iconphoto()` via `tk.PhotoImage` — works without Pillow
  - Added `Pillow>=10.0` to the `[gui]` optional dependency group
  - Added `PIL` to PyInstaller `hiddenimports` and `favicon.png` to bundled data

---

## Test Maintenance

- **Snapshot version strings updated** — Updated 4 construct snapshot files from `shruggie-feedtools/0.1.1` to `shruggie-feedtools/0.1.2` (carried forward to 0.1.3 dynamically)
- **Dynamic version assertion** — `test_construct_feed_generator_forced` now imports `__version__` dynamically instead of hardcoding a version string, preventing future breakage on version bumps
- **307 tests passing**

---

## Release Artifacts

| Artifact | Description |
|---|---|
| `shruggie-feedtools-cli-0.1.3-win-x64.exe` | Standalone Windows CLI executable |
| `shruggie-feedtools-gui-0.1.3-win-x64.exe` | Standalone Windows GUI executable |
| `shruggie_feedtools-0.1.3.tar.gz` | Source distribution |
| `shruggie_feedtools-0.1.3-py3-none-any.whl` | Python wheel |

---

## Upgrade Notes

- Drop-in replacement for v0.1.2 — no schema changes, no API changes
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
- `Pillow >= 10.0` (for robust favicon display; included in `[gui]` extras)

---

## Known Limitations

- PyPI publishing is not yet configured; install from source or use the standalone executables
- GUI executable is Windows-only in this release
- No CI test gate prior to release — tests are run locally (307/307 passing)

---

## License

Apache License 2.0
