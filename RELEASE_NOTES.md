# Release Notes — shruggie-feedtools v0.1.0

**Release Date:** 2026-02-11
**Status:** Initial public release (Alpha)

---

## Overview

First release of **shruggie-feedtools** — a Python module and CLI tool that normalizes web feed data from diverse sources into a single, predictable JSON schema. It also constructs schema-compliant feed output from arbitrary text input using template files.

---

## Features

### Parse Mode

- **Multi-format ingestion** — RSS 2.0, RSS 1.0/RDF, Atom 1.0, JSON Feed 1.0/1.1, and WordPress REST API
- **Unified JSON output** — Every source format normalizes to the same schema, making downstream processing format-agnostic
- **Flexible input** — Parse from URLs, local files, raw strings, or stdin
- **Batch processing** — Parse multiple URLs or files in a single invocation
- **Namespace normalization** — Dublin Core, iTunes, Media RSS, YouTube, Slash, and Content namespaces mapped to consistent prefixes
- **Date normalization** — RFC 822, RFC 2822, ISO 8601, loose formats, and Unix epoch timestamps all normalize to ISO 8601 UTC
- **Graceful degradation** — Malformed feeds produce partial results with error metadata instead of crashing

### Construct Mode

- **Template-based feed creation** — Define feed structure via `.feedtemplate.json` files
- **Text derivation strategies** — Title and description derived via `first_line`, `truncate`, `timestamp`, `template`, `same`, or `none`
- **GUID generation** — `sha256`, `uuid4`, `timestamp`, or `sequential` strategies
- **Link pattern support** — Generate item links from GUID values using patterns
- **Batch construction** — Build multi-item feeds from JSONL input with per-entry overrides
- **Schema parity** — Constructed output is structurally identical to parsed output

### CLI

- `shruggie-feedtools parse` — All parse input modes with `--pretty`, `--output`, `--max-items`, `--quiet`, and SSL/timeout options
- `shruggie-feedtools construct` — Template-driven construction with `--text`, `--text-stdin`, `--entries`, and `--entries-stdin` input modes
- `--version` and `--help` for all commands and subcommands
- Exit codes: `0` success, `1` partial failure, `2` argument/template error
- Pipe-friendly: JSON to stdout by default

### GUI

- **Standalone Windows application** — Two-panel layout with Parse and Construct modes
- **Dark mode** — CustomTkinter-based interface
- **Threaded operations** — Non-blocking parse/construct with progress indication
- **Output panel** — Scrollable monospaced JSON display with Copy and Save buttons

### Python API

```python
from shruggie_feedtools import (
    parse, parse_url, parse_file, parse_string,
    parse_urls, parse_files,
    construct, construct_batch,
)
```

---

## Release Artifacts

| Artifact | Description |
|---|---|
| `shruggie-feedtools-cli-0.1.0-win-x64.exe` | Standalone Windows CLI executable |
| `shruggie-feedtools-gui-0.1.0-win-x64.exe` | Standalone Windows GUI executable |
| `shruggie_feedtools-0.1.0.tar.gz` | Source distribution |
| `shruggie_feedtools-0.1.0-py3-none-any.whl` | Python wheel |

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

---

## Known Limitations

- PyPI publishing is not yet configured; install from source or use the standalone executables
- GUI executable is Windows-only in this release
- No CI test gate prior to release — tests are run locally (301/301 passing)

---

## License

Apache License 2.0
