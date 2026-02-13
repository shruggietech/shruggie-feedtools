# shruggie-feedtools — Implementation Plan

**Project:** `shruggie-feedtools`
**Spec:** [shruggie-feedtools-spec.md](shruggie-feedtools-spec.md)
**Date:** 2026-02-11
**Scope:** Full MVP (v0.1.0) implementation from empty repo to release-ready codebase

---

## Plan Overview

This plan is structured as five sequential sprints designed for AI-first execution. Each sprint runs in an isolated context window and produces a fully functional, testable layer that subsequent sprints build upon.

**Sprint dependency chain:**

```
Sprint 1  →  Sprint 2  →  Sprint 3  →  Sprint 4  →  Sprint 5
Foundation    Parse        Construct     CLI +         GUI +
+ Schema      Pipeline     Pipeline      Scripts       Release
```

Every sprint ends with passing tests for all code produced in that sprint. No sprint assumes the existence of code that hasn't been built yet, with one deliberate exception noted in Sprint 3 (reuse of `schema.py` and `dates.py` from Sprint 1).

---

## Sprint 1 — Project Scaffolding and Core Foundation

### Spec References

- [§1.1 Branding Context](shruggie-feedtools-spec.md#11-branding-context) — Package/import/CLI naming conventions
- [§3 Output Schema](shruggie-feedtools-spec.md#3-output-schema) — Full schema contract (§3.1–§3.5)
- [§3.5 Date Handling](shruggie-feedtools-spec.md#35-date-handling) — Date formats and normalization rules
- [§6.1 Package Structure](shruggie-feedtools-spec.md#61-package-structure) — Directory layout
- [§6.5 Namespace Normalization](shruggie-feedtools-spec.md#65-namespace-normalization) — `NAMESPACE_MAP` and `normalize_prefix()`
- [§10 Dependencies](shruggie-feedtools-spec.md#10-dependencies) — Runtime and dev dependency versions
- [§15 Configuration Object](shruggie-feedtools-spec.md#15-configuration-object) — `ParserConfig` dataclass
- [§17.1 Test Framework and Conventions](shruggie-feedtools-spec.md#171-test-framework-and-conventions) — pytest setup, snapshot infrastructure
- [§17.3 test_schema.py](shruggie-feedtools-spec.md#173-test-specifications) — Pydantic model validation tests
- [§17.3 test_dates.py](shruggie-feedtools-spec.md#173-test-specifications) — Date parsing tests
- [§17.3 test_namespaces.py](shruggie-feedtools-spec.md#173-test-specifications) — Namespace normalization tests
- [Appendix A](shruggie-feedtools-spec.md#appendix-a-platform-and-tooling) — pyproject.toml, version management, ruff config, extras

### Goals

This sprint creates the entire project skeleton and implements the foundational modules that every other module depends on. Nothing in this sprint depends on external HTTP calls, feed parsing, or CLI/GUI layers.

### Deliverables

**Project scaffolding:**

- Complete directory tree as defined in §6.1 — all `__init__.py` files, all subdirectories, even if modules are stubs
- `pyproject.toml` with hatchling build system, all dependency groups (`core`, `gui`, `dev`), ruff config, CLI entry point, dynamic versioning
- `LICENSE` — full Apache 2.0 text
- `.gitignore` — Python ignores, `dist/*` with `!dist/release/` exemption, `.venv/`, `build/`, `__pycache__/`, `*.egg-info/`
- `src/shruggie_feedtools/_version.py` — `__version__ = "0.1.0"`
- `src/shruggie_feedtools/__init__.py` — placeholder public API with version import

**Core modules (fully implemented):**

- `src/shruggie_feedtools/core/schema.py` — All Pydantic models: `FeedResponse`, `FeedMeta`, `FeedItem`, `Enclosure`, `SourceInfo`. Enums for `status`, `source.type`, `source.origin`. `extra = "forbid"` where appropriate. Serialization methods.
- `src/shruggie_feedtools/core/dates.py` — `normalize_date(value) -> str | None` function handling RFC 822, RFC 2822, ISO 8601 (with/without offset), loose formats, naive datetime (assume UTC), Unix epoch int/float. Returns ISO 8601 UTC string (`...Z`) or `None`. Never raises on bad input.
- `src/shruggie_feedtools/core/namespaces.py` — `NAMESPACE_MAP` dict (all URIs from spec §6.5), `normalize_prefix(uri, declared_prefix) -> str` function with URI tolerance (HTTPS variants, case, trailing slashes).
- `src/shruggie_feedtools/core/config.py` — `ParserConfig` dataclass exactly as specified in §15.
- `src/shruggie_feedtools/utils/logging.py` — Structured logging setup using stdlib `logging`. Configurable level. Named logger `shruggie_feedtools`.
- `src/shruggie_feedtools/utils/html.py` — Stub with function signatures for thumbnail extraction (implemented in Sprint 2 when normalizer needs it).

**Test infrastructure:**

- `tests/conftest.py` — Snapshot fixture (`assert_snapshot`), `--update-snapshots` CLI option registration, shared helpers, fixture path resolution
- `tests/test_schema.py` — All tests from §17.3 `test_schema.py` table (roundtrip, validation errors, default application, serialization)
- `tests/test_dates.py` — All tests from §17.3 `test_dates.py` table (RFC 2822, ISO 8601, loose, epoch, garbage, empty, partial, UTC enforcement)
- `tests/test_namespaces.py` — All tests from §17.3 `test_namespaces.py` table (DC HTTP/HTTPS/trailing-slash/uppercase, iTunes, Media RSS, unknown fallback, YouTube, exhaustive map check)

### Verification

```bash
# From project root after running ./scripts/venv-setup.ps1 (or .sh)
pytest tests/test_schema.py tests/test_dates.py tests/test_namespaces.py -v
```

All tests pass. No imports from `adapters/`, `construct/`, `cli/`, or `gui/` are used.

---

## Sprint 2 — Parse Pipeline (Detection, Adapters, Normalizer, Fetcher, Orchestrator)

### Spec References

- [§2 Supported Input Formats](shruggie-feedtools-spec.md#2-supported-input-formats) — All format priorities and detection methods
- [§2.4 Namespace Extensions](shruggie-feedtools-spec.md#24-namespace-extensions-within-xml-feeds) — Supported namespace prefixes
- [§4 Parse Mode — Public API](shruggie-feedtools-spec.md#4-parse-mode--public-api) — `parse`, `parse_url`, `parse_file`, `parse_string`, `parse_urls`, `parse_files`, format-specific parsers, `detect_feed_type`
- [§6.2 Data Flow — Parse Mode](shruggie-feedtools-spec.md#62-data-flow--parse-mode) — Fetch → Detect → Adapt → Namespace → Normalize → Schema
- [§6.4 Detection Pipeline](shruggie-feedtools-spec.md#64-detection-pipeline-parse-mode) — XML vs JSON routing, format sniffing
- [§8 Adapter Specifications](shruggie-feedtools-spec.md#8-adapter-specifications) — feedparser adapter (§8.1)
- [§9 Error Handling](shruggie-feedtools-spec.md#9-error-handling) — Graceful degradation, error categories
- [§11 HTTP Fetching](shruggie-feedtools-spec.md#11-http-fetching) — Timeout, retry, redirect, response size, headers
- [§17.2 Fixture Data](shruggie-feedtools-spec.md#172-fixture-data) — All parse fixture files and their purposes
- [§17.3 test_detector.py](shruggie-feedtools-spec.md#173-test-specifications) — Format detection tests
- [§17.3 test_adapters.py](shruggie-feedtools-spec.md#173-test-specifications) — Per-adapter tests (RSS 2.0, Atom 1.0, RSS 1.0)
- [§17.3 test_normalizer.py](shruggie-feedtools-spec.md#173-test-specifications) — Schema mapping and field normalization tests
- [§17.3 test_fetcher.py](shruggie-feedtools-spec.md#173-test-specifications) — HTTP client tests
- [§17.3 test_parser.py](shruggie-feedtools-spec.md#173-test-specifications) — End-to-end parse pipeline integration tests
- [§17.4 Snapshot Tests](shruggie-feedtools-spec.md#174-snapshot-tests) — Parse fixture snapshots
- [§18.1 XML Processing](shruggie-feedtools-spec.md#181-xml-processing) — XXE safety via feedparser
- [§18.2 HTML Content Passthrough](shruggie-feedtools-spec.md#182-html-content-passthrough) — No sanitization by design
- [§18.3 HTTP Request Security](shruggie-feedtools-spec.md#183-http-request-security) — TLS, redirects, response size, timeouts

### Prerequisites (from Sprint 1)

- `core/schema.py` — Pydantic models for validation and serialization
- `core/dates.py` — Date normalization
- `core/namespaces.py` — Namespace prefix resolution
- `core/config.py` — `ParserConfig`
- `utils/logging.py` — Logger
- `tests/conftest.py` — Snapshot fixture

### Goals

This sprint implements the entire parse pipeline from HTTP fetch through to validated schema output. It also creates all parse-mode test fixture data files (the realistic XML/JSON samples that every parse test depends on) and writes both unit and integration tests. The public API for parse mode is wired up in `__init__.py` at the end.

### Deliverables

**Fixture data files (all under `tests/fixtures/`):**

Create realistic, representative test data for every format. These files must be self-consistent — valid enough for their respective parsers while exercising the edge cases described in §17.2.

- `rss2/minimal.xml` — Minimum valid RSS 2.0 with channel title, link, description, and 2–3 items
- `rss2/wordpress.xml` — WordPress-style export with `dc:creator`, `content:encoded`, excerpt, categories, `slash:comments`
- `rss2/podcast_itunes.xml` — RSS 2.0 with `itunes:` namespace fields (duration, explicit, image, author) and audio enclosures
- `rss2/hairy_malformed.xml` — Intentionally broken: missing closing tags, bad dates, mixed encodings, empty elements
- `rss2/financial_sec.xml` — SEC EDGAR-style: unusual structure, minimal descriptions, date edge cases
- `rss2/reddit.xml` — Media RSS: `media:thumbnail`, `media:content`, HTML entities in titles
- `atom10/github_releases.xml` — GitHub releases: `link[rel=alternate]`, `content type="html"`, `updated` dates
- `atom10/youtube_channel.xml` — YouTube: `yt:videoId`, `yt:channelId`, `media:group`, `media:thumbnail`
- `atom10/statuspage.xml` — Statuspage.io: multiple `<updated>` elements per entry
- `rss1/rdf_gov.xml` — Government RDF: full `dc:` namespace usage
- `edge_cases/mixed_case_elements.xml` — `<Title>`, `<TITLE>`, `<title>` in same feed
- `edge_cases/custom_namespace_prefixes.xml` — Non-standard prefix declarations resolving to known URIs
- `edge_cases/bad_dates.xml` — 15+ date format variants including malformed, empty, ambiguous timezone, epoch
- `edge_cases/missing_fields.xml` — Feed with zero optional fields
- `edge_cases/encoding_utf8_bom.xml` — UTF-8 BOM, HTML entities, Unicode content

**Core parse modules:**

- `core/detector.py` — `detect_feed_type(content: bytes) -> str | None` per §6.4 detection pipeline. XML path (feedparser version sniffing). Returns format string or `None`.
- `core/fetcher.py` — `fetch(url, config) -> FetchResult` using `httpx`. Captures `Content-Type`, final URL, ETag, Last-Modified. Handles timeouts, retries with exponential backoff, redirect limits, response size cap, custom User-Agent, SSL toggle. Returns structured result (not raw exception).
- `core/normalizer.py` — `normalize_feed(intermediate, config) -> dict` and `normalize_item(intermediate, config) -> dict`. Maps adapter intermediate dicts → output schema fields. Implements fallback chains (description from summary or truncated content, author from `dc:creator`, guid from link, thumbnail from `media:thumbnail`/`media:content`/enclosure). Categories deduplication. Extension bucketing by normalized prefix.
- `utils/html.py` — `extract_thumbnail(html_content) -> str` for pulling thumbnail URLs from HTML img tags in content fields.

**Adapters:**

- `adapters/__init__.py` — Exports: `parse_rss`, `parse_atom`, `parse_rdf`
- `adapters/feedparser_adapter.py` — Wraps `feedparser.parse()`. Handles RSS 2.0, Atom 1.0, RSS 1.0/RDF. Extracts `result.version` → `source.type`. Maps `result.feed` and `result.entries` → intermediate dicts. Namespace prefix normalization on all prefixed fields. Handles `bozo` flag (warn, continue).

**Parse orchestrator:**

- `core/parser.py` — `parse_string(content, source_url, config)`, `parse_file(path, config)`, `parse_url(url, config)`, `parse_urls(urls, config)`, `parse_files(paths, config)`, `parse(input, config)` convenience function. Chains: fetch → detect → adapt → normalize → validate. Error wrapping per §9.

**Public API update:**

- `__init__.py` — Export `parse`, `parse_url`, `parse_file`, `parse_string`, `parse_urls`, `parse_files` from `core.parser`

**Tests:**

- `tests/test_detector.py` — All 10 tests from §17.3 detector table
- `tests/test_adapters.py` — All adapter tests from §17.3 (RSS 2.0: 10 tests, Atom 1.0: 6 tests, RSS 1.0: 3 tests)
- `tests/test_normalizer.py` — All 30 tests from §17.3 normalizer table
- `tests/test_fetcher.py` — All 18 tests from §17.3 fetcher table (using `httpx` mock transport or `pytest-httpx`)
- `tests/test_parser.py` — All 22 integration tests from §17.3 parser table
- `tests/snapshots/` — Generate all 15 parse-mode golden files (§17.4 snapshot coverage table, parse entries)

### Verification

```bash
pytest tests/test_detector.py tests/test_adapters.py tests/test_normalizer.py \
       tests/test_fetcher.py tests/test_parser.py -v --update-snapshots
# Then re-run without --update-snapshots to confirm snapshots match:
pytest tests/ -v
```

All parse-mode tests pass. Snapshot golden files are generated and committed. The `parse_string()` function works end-to-end for all fixture formats.

---

## Sprint 3 — Construct Pipeline (Templates, Strategies, Builder)

### Spec References

- [§5 Construct Mode — Template-Based Feed Construction](shruggie-feedtools-spec.md#5-construct-mode--template-based-feed-construction) — Full construct mode spec (§5.1–§5.10)
- [§5.2 Template File Format](shruggie-feedtools-spec.md#52-template-file-format) — `.feedtemplate.json` structure
- [§5.3 Template Field Reference](shruggie-feedtools-spec.md#53-template-field-reference) — `template_version`, `feed`, `item_mapping`, `item_defaults`
- [§5.4 Title and Description Derivation Strategies](shruggie-feedtools-spec.md#54-title-and-description-derivation-strategies) — `first_line`, `truncate`, `timestamp`, `template`, `none`, `same`
- [§5.5 GUID Generation Strategies](shruggie-feedtools-spec.md#55-guid-generation-strategies) — `sha256`, `uuid4`, `timestamp`, `sequential`
- [§5.6 Construct Mode — Python API](shruggie-feedtools-spec.md#56-construct-mode--python-api) — `construct()`, `construct_batch()`, `load_template()`
- [§5.8 JSONL Entry Format](shruggie-feedtools-spec.md#58-jsonl-entry-format-batch-input) — Batch input format with per-entry overrides
- [§5.9 Template Validation](shruggie-feedtools-spec.md#59-template-validation) — Pydantic validation, `TemplateValidationError`
- [§5.10 Constructed Output Example](shruggie-feedtools-spec.md#510-constructed-output-example) — Expected output walkthrough
- [§6.3 Data Flow — Construct Mode](shruggie-feedtools-spec.md#63-data-flow--construct-mode) — Template → Entry → Strategies → Builder → Schema
- [§17.2 Fixture Data](shruggie-feedtools-spec.md#172-fixture-data) — Construct fixture files (templates + entries)
- [§17.3 test_construct.py](shruggie-feedtools-spec.md#173-test-specifications) — Construct integration tests
- [§17.3 test_template.py](shruggie-feedtools-spec.md#173-test-specifications) — Template loading and validation tests
- [§17.3 test_strategies.py](shruggie-feedtools-spec.md#173-test-specifications) — Strategy function unit tests
- [§17.4 Snapshot Tests](shruggie-feedtools-spec.md#174-snapshot-tests) — Construct fixture snapshots
- [§18.4 Template Safety](shruggie-feedtools-spec.md#184-template-safety) — No eval, strict Pydantic, `extra = "forbid"`
- [Appendix B Template Quick Reference](shruggie-feedtools-spec.md#appendix-b-template-quick-reference) — Minimal template, defaults, strategy tables, precedence order
- [Appendix C Construct Mode Use Cases](shruggie-feedtools-spec.md#appendix-c-construct-mode-use-cases) — Practical template examples

### Prerequisites (from Sprints 1–2)

- `core/schema.py` — Pydantic models (construct output uses the same schema as parse output)
- `core/dates.py` — Timestamp normalization (construct timestamps go through the same pipeline)
- `tests/conftest.py` — Snapshot fixture

### Goals

This sprint implements the entire construct pipeline: template loading/validation, text derivation strategies, GUID generation, JSONL entry parsing, feed assembly, and schema validation. Construct mode output is structurally identical to parse mode output — same Pydantic models, same JSON shape.

### Deliverables

**Construct fixture data files:**

- `tests/fixtures/templates/minimal.feedtemplate.json` — Only required fields; tests default handling
- `tests/fixtures/templates/incident_log.feedtemplate.json` — Full template, all fields populated
- `tests/fixtures/templates/changelog.feedtemplate.json` — Uses `link_pattern` with `{guid}`
- `tests/fixtures/templates/all_strategies.feedtemplate.json` — Exercises every strategy combination
- `tests/fixtures/templates/invalid_missing_title.feedtemplate.json` — Missing `feed.title`, must fail validation
- `tests/fixtures/entries/single_entry.jsonl` — One-line JSONL
- `tests/fixtures/entries/batch_entries.jsonl` — 10 entries with varying timestamps
- `tests/fixtures/entries/entries_with_overrides.jsonl` — Per-entry title, author, category overrides

**Construct modules:**

- `construct/__init__.py` — Exports: `construct`, `construct_batch`, `load_template`
- `construct/template.py` — Pydantic models for template validation: `FeedTemplate`, `FeedSection`, `ItemMapping`, `ItemDefaults`. `load_template(path_or_dict)` function. `TemplateValidationError` custom exception. `extra = "forbid"` on all models. Strategy field enums with allowed value sets. Positive integer validators on max_length fields. Template version check (only `"1.0"`).
- `construct/strategies.py` — Pure functions for each derivation strategy:
  - Title: `derive_title(text, strategy, max_length, timestamp, index, title_template) -> str`
  - Description: `derive_description(text, strategy, max_length) -> str`
  - GUID: `generate_guid(text, timestamp, strategy, feed_title, index, batch_size) -> str`
  - Link: `generate_link(pattern, guid) -> str`
  - Word-boundary truncation helper with `…` suffix
  - Slug generation for sequential GUIDs
- `construct/entry.py` — `parse_entries(jsonl_path_or_lines) -> list[dict]`. Parses JSONL with per-entry override support. Validates `text` and `timestamp` are present per line. Skips malformed lines with warning.
- `construct/builder.py` — `build_feed(entries, template) -> dict`. Assembles feed metadata from template. Applies strategy derivations per item. Merges `item_defaults` → per-entry overrides → derived values per precedence order (§B.4). Computes `feed.last_updated` as latest `pub_date`. Forces `feed.generator` to `"shruggie-feedtools/0.1.0"`. Sets `source.type = "constructed"`, `source.origin = "template"`, `source.url = None`. Validates output through Pydantic schema.

**Public API additions in `__init__.py`:**

- Export `construct`, `construct_batch` from `construct` package
- `construct(text, timestamp, template) -> dict` — single-item convenience
- `construct_batch(entries, template) -> dict` — multi-item

**Tests:**

- `tests/test_template.py` — All 17 tests from §17.3 template table (minimal load, full load, all default paths, 7 validation error cases, dict loading, nonexistent file, invalid JSON, caching, unsupported version)
- `tests/test_strategies.py` — All 28 tests from §17.3 strategies table (12 title, 6 description, 10 GUID)
- `tests/test_construct.py` — All 22 tests from §17.3 construct table (single item, text targets, timestamps, feed metadata, defaults, overrides, link pattern, batch, JSONL, inline template, empty text, deterministic GUID)
- `tests/snapshots/construct/` — Generate all 4 construct-mode golden files (minimal_single, incident_log_batch, changelog_with_link_pattern, entry_overrides)

### Verification

```bash
pytest tests/test_template.py tests/test_strategies.py tests/test_construct.py -v --update-snapshots
# Then full suite to confirm no regressions:
pytest tests/ -v
```

All construct tests pass. Both `construct()` and `construct_batch()` produce schema-identical output to `parse_string()`. Snapshot golden files generated.

---

## Sprint 4 — CLI Interface and Development Scripts

### Spec References

- [§7 CLI Interface](shruggie-feedtools-spec.md#7-cli-interface) — Full CLI spec (§7.1–§7.5)
- [§7.1 Parse Subcommand](shruggie-feedtools-spec.md#71-parse-subcommand) — All parse flags and modes
- [§7.2 Construct Subcommand](shruggie-feedtools-spec.md#72-construct-subcommand) — All construct flags and modes
- [§7.3 Global Options](shruggie-feedtools-spec.md#73-global-options) — `--version`, `--help`
- [§7.4 Exit Codes](shruggie-feedtools-spec.md#74-exit-codes) — 0, 1, 2 meanings
- [§7.5 Pipe Examples](shruggie-feedtools-spec.md#75-pipe-examples) — stdin/stdout usage patterns
- [§14 Development Scripts](shruggie-feedtools-spec.md#14-development-scripts) — All scripts (§14.1–§14.3)
- [§14.1 venv-setup](shruggie-feedtools-spec.md#141-venv-setupps1--venv-setupsh) — Virtual environment setup
- [§14.2 build](shruggie-feedtools-spec.md#142-buildps1--buildsh) — PyInstaller build
- [§14.3 test](shruggie-feedtools-spec.md#143-testps1--testsh) — Test runner
- [§17.3 test_cli.py](shruggie-feedtools-spec.md#173-test-specifications) — CLI test specifications

### Prerequisites (from Sprints 1–3)

- Full parse pipeline (`parse`, `parse_url`, `parse_file`, `parse_string`)
- Full construct pipeline (`construct`, `construct_batch`, `load_template`)
- `_version.py` for `--version` output

### Goals

This sprint wires up the user-facing CLI with argparse subcommands and implements all six development scripts. The CLI is the primary distribution interface — it calls directly into the library functions built in Sprints 2–3.

### Deliverables

**CLI modules:**

- `cli/__init__.py` — Empty
- `cli/main.py` — `main()` function using `argparse` with subcommands:
  - `parse` subcommand: `--url`, `--url-list`, `--file`, `--files`, `--dir`, `--stdin` (mutually exclusive input group), `--output`, `--output-dir`, `--pretty`, `--indent`, `--quiet`, `--timeout`, `--user-agent`, `--no-verify-ssl`, `--max-items`
  - `construct` subcommand: `--template` (required), `--text`/`--text-stdin`/`--entries`/`--entries-stdin` (mutually exclusive input group), `--timestamp` (required for single-item modes), `--output`, `--pretty`, `--indent`, `--quiet`
  - Global: `--version`, `--help`
  - Exit codes per §7.4: 0 success, 1 partial failure, 2 argument/template error
  - Output routing: stdout by default, file if `--output` specified
  - Quiet mode: suppress stderr logging
  - Pretty print: `json.dumps(indent=N)` when `--pretty` is set
- `__main__.py` — `from shruggie_feedtools.cli.main import main; main()` for `python -m shruggie_feedtools`

**Development scripts (all under `scripts/`):**

- `venv-setup.ps1` — PowerShell: locate project root, check/create `.venv`, verify Python ≥3.12, install editable dev+gui extras, parameterized `-PythonCmd` and `-Force`
- `venv-setup.sh` — Bash: mirror of PS1 with `--python` and `--force` flags, searches for `python3.12`/`python3`/`python`
- `build.ps1` — PowerShell: call venv-setup, read version from `_version.py`, PyInstaller CLI and/or GUI targets, `-Target` (cli/gui/all), `-Release` (copy to `dist/release/` with versioned filenames), `-Clean`
- `build.sh` — Bash mirror of build.ps1
- `test.ps1` — PowerShell: call venv-setup, run pytest with colored output, `-Silent`, `-Coverage`, `-Filter`, `-FailFast`, summary banner
- `test.sh` — Bash mirror of test.ps1 with ANSI color codes

**Tests:**

- `tests/test_cli.py` — All tests from §17.3 CLI tables:
  - Parse subcommand: 11 tests (url stdout, file, stdin, url-list, output file, pretty, indent, quiet, max-items, no-verify-ssl, nonexistent file, no input)
  - Construct subcommand: 11 tests (text arg, text stdin, entries file, entries stdin, output file, pretty, missing template, invalid template, missing timestamp, nonexistent template, bad JSONL entry)
  - Global: 6 tests (version, help, parse help, construct help, unknown subcommand, pipe to jq)

### Verification

```bash
pytest tests/test_cli.py -v
# Also manual smoke test:
python -m shruggie_feedtools --version
python -m shruggie_feedtools parse --file tests/fixtures/rss2/minimal.xml --pretty
echo "Test entry" | python -m shruggie_feedtools construct \
    --template tests/fixtures/templates/minimal.feedtemplate.json \
    --text-stdin --timestamp "2026-02-11T12:00:00Z" --pretty
```

All CLI tests pass. Both subcommands produce correct output for all input modes. Exit codes match §7.4.

---

## Sprint 5 — GUI Application, Release Pipeline, and README

### Spec References

- [§12 GUI Specification](shruggie-feedtools-spec.md#12-gui-specification) — Full GUI spec (§12.1–§12.7)
- [§12.2 Layout](shruggie-feedtools-spec.md#122-layout) — Two-panel layout with sidebar and working area
- [§12.3 Mode: Parse](shruggie-feedtools-spec.md#123-mode-parse) — URL/File/Batch input methods, options bar
- [§12.4 Mode: Construct](shruggie-feedtools-spec.md#124-mode-construct) — Template picker, text area, timestamp field
- [§12.5 Output Panel](shruggie-feedtools-spec.md#125-output-panel) — Scrollable monospaced JSON, Copy/Save buttons
- [§12.6 Appearance](shruggie-feedtools-spec.md#126-appearance) — Dark mode, font stack, minimum size 900×600
- [§12.7 Threading](shruggie-feedtools-spec.md#127-threading) — Background threads, disabled button + spinner during operations
- [§13 Release Pipeline](shruggie-feedtools-spec.md#13-release-pipeline) — GitHub Actions workflow (§13.1–§13.3)
- [§13.1 Release Artifacts](shruggie-feedtools-spec.md#131-release-artifacts) — CLI exe, GUI exe, Python package
- [§13.2 GitHub Actions Workflow](shruggie-feedtools-spec.md#132-github-actions-workflow) — `release.yml` with pre-built asset bypass
- [§13.3 Version Tagging](shruggie-feedtools-spec.md#133-version-tagging) — Tag-based release process
- [§1 Executive Summary](shruggie-feedtools-spec.md#1-executive-summary) — For README content
- [§1.2 Core Capabilities](shruggie-feedtools-spec.md#12-core-capabilities) — Parse and Construct mode descriptions
- [§1.5 What Counts as a "Feed"](shruggie-feedtools-spec.md#15-what-counts-as-a-feed) — Supported source types table
- [Appendix A.5 Typography](shruggie-feedtools-spec.md#a5-typography-gui) — Font stack for GUI
- [Appendix A.6 Version Management](shruggie-feedtools-spec.md#a6-version-management) — Dynamic version sourcing

### Prerequisites (from Sprints 1–4)

- Full parse and construct library code
- CLI interface (the GUI calls the same library functions)
- `_version.py`, `pyproject.toml`, all project metadata

### Goals

This sprint builds the GUI application, sets up the GitHub Actions release pipeline, and writes the README. This is the final layer — after this sprint, the project is release-ready.

### Deliverables

**GUI module:**

- `gui/__init__.py` — Empty
- `gui/app.py` — Full CustomTkinter application:
  - Two-panel layout: left sidebar (mode selection), right working area
  - Parse mode: URL / File / Batch radio buttons, URL text field, file picker, batch text area with "Load from File", options bar (pretty print toggle, max items spinner, SSL verify toggle), "Parse Feed" / "Parse All" action button
  - Construct mode: template file picker (shows `feed.title` on load), multiline text area, timestamp field (pre-filled with current UTC, editable), "Construct Feed" action button
  - Output panel: scrollable, read-only, monospaced (`CTkTextbox`), Copy and Save buttons
  - Error display: error JSON rendered in same output panel (no modal dialogs)
  - Threading: all parse/construct operations in `threading.Thread`, action button disabled with spinner text during operations, output panel cleared on operation start and populated on completion
  - Appearance: dark mode (`customtkinter.set_appearance_mode("dark")`), font stack per Appendix A.5 (JetBrains Mono → Consolas for output, Inter → Segoe UI for controls), minimum window size 900×600, resizable with output panel expanding
  - Window title: "Shruggie FeedTools"

**Release infrastructure:**

- `.github/workflows/release.yml` — Exactly as specified in §13.2: triggered on `v*` tag push, `windows-latest` runner, pre-built asset bypass check, Python 3.12 setup, build from source fallback, `softprops/action-gh-release@v2` with `dist/release/*`
- `dist/release/` directory — Create with `.gitkeep`

**README.md:**

- Project title, badges (license, Python version)
- Overview paragraph from §1 Executive Summary
- Core capabilities (Parse mode + Construct mode)
- Installation (download pre-built executables from GitHub Releases, with Windows "Unblock" instructions)
- Development setup (clone + venv-setup scripts for contributors)
- Quick start examples: parse URL, parse file, construct single item, construct batch
- CLI reference: parse subcommand flags, construct subcommand flags, global options
- Python API reference: key function signatures with brief descriptions
- Supported formats table from §1.5
- Template quick reference (minimal template, strategy summary)
- Development section: clone, venv setup, running tests, building executables
- License (Apache 2.0)
- Link to full spec

### Verification

```bash
# Full test suite — everything from all sprints:
pytest tests/ -v

# GUI smoke test (manual):
python -c "from shruggie_feedtools.gui.app import main; print('GUI import OK')"

# Verify release workflow YAML is valid:
python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"

# Verify README renders (check for broken links):
python -c "import pathlib; r = pathlib.Path('README.md').read_text(); print(f'README: {len(r)} chars')"
```

All tests pass. GUI launches without errors. Release workflow is syntactically valid. README is complete. Project is ready for `git tag v0.1.0` and release.
