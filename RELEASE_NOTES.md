# Release Notes — shruggie-feedtools v0.1.4

**Release Date:** 2026-02-13
**Status:** Patch release (Alpha)

---

## Overview

Critical parsing and usability release fixing three persistent issues: JSON Feed and WordPress REST API detection failures across both CLI and GUI, unreliable GUI favicon display, and inadequate CLI help text. Adds content-type and BOM-aware feed detection, a comprehensive CLI help overhaul, and 15 new tests (317 total passing).

---

## Bug Fixes

### JSON Feed / WP REST Detection Failures

- **Fixed: JSON Parse operations failing with "Response does not match any known feed format"** — The feed type detector now accepts an optional `content_type` parameter used as a fallback when byte-level sniffing is inconclusive. `parse_url()` passes the HTTP `Content-Type` header through to the detector, and `parse_file()` uses file extension (`.json`) as a detection hint.
- **Fixed: BOM-encoded feeds rejected** — Added BOM detection and re-encoding for UTF-8, UTF-16 LE/BE, and UTF-32 LE/BE byte order marks. Content is normalized to UTF-8 before detection and parsing.
- **Improved: Diagnostic error messages** — All error responses now include diagnostic context (`first_byte`, `content_type`, `filename`) to aid troubleshooting.

### GUI Favicon Not Applying

- **Fixed: Favicon still not appearing after previous attempts** — Comprehensive timing overhaul:
  - Icon now applied at four staggered delays (100ms, 500ms, 1200ms, and `after_idle`) to reliably override CustomTkinter's aggressive default-icon behavior
  - Added `parents[2]` as a candidate base directory for editable-install layouts
  - Reduced per-call re-apply delay from 300ms to 200ms
  - Logs all searched paths when no favicon is found for easier debugging
- **Fixed: PyInstaller build missing favicon** — Added `('brand', 'brand')` to the GUI `.spec` file's `datas` list so `favicon.ico` and `favicon.png` are bundled in the executable. Added `icon='brand/favicon.ico'` to the `EXE()` call so the `.exe` itself displays the correct icon in Windows Explorer and the taskbar.

### CLI Help Text Overhaul

- **Fixed: Terse, incomplete CLI help** — Complete rebuild of the argument parser:
  - All parsers now use `RawDescriptionHelpFormatter` for proper multi-line rendering
  - Arguments organized into logical groups: **input modes**, **output options**, **behavior options** (parse); **template**, **input modes**, **timestamp**, **output options** (construct)
  - Descriptive metavars added: `URL`, `FILE`, `DIRECTORY`, `SECONDS`, `STRING`, `N`, `DIR`
  - Rich multi-line descriptions listing all supported feed formats
  - Practical usage examples in epilogs for all subcommands
  - Exit code documentation (0 = success, 1 = partial failure, 2 = argument/template error)

---

## New Tests

| Area | Tests Added | Description |
|---|---|---|
| `test_detector.py` | 7 | Content-type fallback hints, UTF-8/16 BOM handling, backward compatibility |
| `test_parser.py` | 3 | JSON Feed via `parse_url()` (mocked), `parse_file()` pipeline |
| `test_cli.py` | 5 | JSON Feed CLI file/URL parsing, enriched help text assertions |
| **Total** | **15 new** | **317 total tests passing** |

---

## Release Artifacts

| Artifact | Description |
|---|---|
| `shruggie-feedtools-cli-0.1.4-win-x64.exe` | Standalone Windows CLI executable |
| `shruggie-feedtools-gui-0.1.4-win-x64.exe` | Standalone Windows GUI executable |
| `shruggie_feedtools-0.1.4.tar.gz` | Source distribution |
| `shruggie_feedtools-0.1.4-py3-none-any.whl` | Python wheel |

---

## Upgrade Notes

- Drop-in replacement for v0.1.3 — no schema changes, no API changes
- JSON Feed and WP REST parsing that previously failed should now succeed out of the box
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
- No CI test gate prior to release — tests are run locally (317/317 passing)

---

## License

Apache License 2.0
