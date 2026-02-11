"""CLI interface tests (§17.3 test_cli.py).

Tests the CLI by invoking the ``main()`` entry point in-process via
``shruggie_feedtools.cli.main.main``.  Verifies argument parsing, subcommand
routing, output formatting, exit codes, and pipe behavior.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

from shruggie_feedtools._version import __version__

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Helper: run CLI in-process and capture stdout/stderr/exit code
# ---------------------------------------------------------------------------


def run_cli(args: list[str], stdin_text: str | None = None) -> tuple[str, str, int]:
    """Run the CLI ``main()`` in-process, capturing stdout, stderr, exit code.

    Parameters
    ----------
    args:
        Command-line arguments (without the program name).
    stdin_text:
        Optional text to provide as stdin.

    Returns
    -------
    tuple[str, str, int]
        (stdout, stderr, exit_code)
    """
    from io import StringIO

    from shruggie_feedtools.cli.main import main

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_stdin = sys.stdin

    stdout_capture = StringIO()
    stderr_capture = StringIO()

    stdin_mock = StringIO(stdin_text if stdin_text is not None else "")

    exit_code = 0
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        sys.stdin = stdin_mock
        main(args)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 0
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.stdin = old_stdin

    return stdout_capture.getvalue(), stderr_capture.getvalue(), exit_code


# ═══════════════════════════════════════════════════════════════════════════
# Parse subcommand tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCliParse:
    """Parse subcommand CLI tests."""

    def test_cli_parse_url_stdout(self) -> None:
        """Parse --url writes valid JSON to stdout with exit code 0.

        Uses a mock to avoid real HTTP requests.
        """
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        content = fixture.read_bytes()

        with mock.patch("shruggie_feedtools.core.parser.fetch") as mock_fetch:
            from shruggie_feedtools.core.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                ok=True,
                content=content,
                content_type="application/rss+xml",
                final_url="https://example.com/feed",
                status_code=200,
            )
            stdout, _stderr, code = run_cli(["parse", "--url", "https://example.com/feed"])

        assert code == 0
        data = json.loads(stdout)
        assert data["status"] == "ok"

    def test_cli_parse_file(self) -> None:
        """Parse --file produces valid JSON with source.origin 'file'."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        stdout, _stderr, code = run_cli(["parse", "--file", str(fixture)])

        assert code == 0
        data = json.loads(stdout)
        assert data["status"] == "ok"
        assert data["source"]["origin"] == "file"

    def test_cli_parse_stdin(self) -> None:
        """Parse --stdin reads URLs from stdin and produces JSON."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        content = fixture.read_bytes()

        with mock.patch("shruggie_feedtools.core.parser.fetch") as mock_fetch:
            from shruggie_feedtools.core.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                ok=True,
                content=content,
                content_type="application/rss+xml",
                final_url="https://example.com/feed",
                status_code=200,
            )
            stdout, _stderr, code = run_cli(
                ["parse", "--stdin"],
                stdin_text="https://example.com/feed\n",
            )

        assert code == 0
        data = json.loads(stdout)
        # Could be a single result or array depending on count
        if isinstance(data, list):
            assert data[0]["status"] == "ok"
        else:
            assert data["status"] == "ok"

    def test_cli_parse_url_list(self, tmp_path: Path) -> None:
        """Parse --url-list reads URLs from a file and produces results."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        content = fixture.read_bytes()

        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://example.com/feed1\nhttps://example.com/feed2\n")

        with mock.patch("shruggie_feedtools.core.parser.fetch") as mock_fetch:
            from shruggie_feedtools.core.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                ok=True,
                content=content,
                content_type="application/rss+xml",
                final_url="https://example.com/feed",
                status_code=200,
            )
            stdout, _stderr, code = run_cli(["parse", "--url-list", str(url_file)])

        assert code == 0
        data = json.loads(stdout)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_cli_parse_output_file(self, tmp_path: Path) -> None:
        """Parse --output writes to file; stdout is empty."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        out_file = tmp_path / "out.json"

        stdout, _stderr, code = run_cli(
            ["parse", "--file", str(fixture), "--output", str(out_file)]
        )

        assert code == 0
        assert stdout == ""
        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["status"] == "ok"

    def test_cli_parse_pretty(self) -> None:
        """Parse --pretty produces indented JSON output."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        stdout, _stderr, code = run_cli(["parse", "--file", str(fixture), "--pretty"])

        assert code == 0
        # Pretty-printed JSON contains newlines and indentation
        assert "\n" in stdout
        assert "  " in stdout
        data = json.loads(stdout)
        assert data["status"] == "ok"

    def test_cli_parse_indent_custom(self) -> None:
        """Parse --pretty --indent 4 produces 4-space indented JSON."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        stdout, _stderr, code = run_cli(
            ["parse", "--file", str(fixture), "--pretty", "--indent", "4"]
        )

        assert code == 0
        assert "    " in stdout  # 4-space indent
        data = json.loads(stdout)
        assert data["status"] == "ok"

    def test_cli_parse_quiet(self) -> None:
        """Parse --quiet suppresses stderr logging."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        stdout, stderr, code = run_cli(["parse", "--file", str(fixture), "--quiet"])

        assert code == 0
        assert stderr == ""
        data = json.loads(stdout)
        assert data["status"] == "ok"

    def test_cli_parse_max_items(self) -> None:
        """Parse --max-items limits items in output."""
        fixture = FIXTURES_DIR / "rss2" / "wordpress.xml"
        stdout, _stderr, code = run_cli(
            ["parse", "--file", str(fixture), "--max-items", "2"]
        )

        assert code == 0
        data = json.loads(stdout)
        assert len(data["items"]) <= 2

    def test_cli_parse_no_verify_ssl(self) -> None:
        """Parse --no-verify-ssl passes through to config."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        content = fixture.read_bytes()

        with mock.patch("shruggie_feedtools.core.parser.fetch") as mock_fetch:
            from shruggie_feedtools.core.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                ok=True,
                content=content,
                content_type="application/rss+xml",
                final_url="https://example.com/feed",
                status_code=200,
            )
            _stdout, _stderr, code = run_cli(
                ["parse", "--url", "https://example.com/feed", "--no-verify-ssl"]
            )

        assert code == 0
        # Verify the config was passed with verify_ssl=False
        call_args = mock_fetch.call_args
        config = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("config")
        assert config.verify_ssl is False

    def test_cli_parse_timeout(self) -> None:
        """Parse --timeout passes the timeout value to config."""
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        content = fixture.read_bytes()

        with mock.patch("shruggie_feedtools.core.parser.fetch") as mock_fetch:
            from shruggie_feedtools.core.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                ok=True,
                content=content,
                content_type="application/rss+xml",
                final_url="https://example.com/feed",
                status_code=200,
            )
            _stdout, _stderr, code = run_cli(
                ["parse", "--url", "https://example.com/feed", "--timeout", "5"]
            )

        assert code == 0
        call_args = mock_fetch.call_args
        config = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("config")
        assert config.timeout_read == 5.0

    def test_cli_parse_nonexistent_file(self) -> None:
        """Parse --file with nonexistent path produces error and exit code 2."""
        _stdout, stderr, code = run_cli(["parse", "--file", "does_not_exist.xml"])

        assert code == 2
        assert "not found" in stderr.lower() or "error" in stderr.lower()

    def test_cli_parse_no_input_specified(self) -> None:
        """Parse with no input flags shows usage help and exits 2."""
        _stdout, stderr, code = run_cli(["parse"])

        assert code == 2
        assert "no input" in stderr.lower() or "help" in stderr.lower()


# ═══════════════════════════════════════════════════════════════════════════
# Construct subcommand tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCliConstruct:
    """Construct subcommand CLI tests."""

    def test_cli_construct_text_arg(self) -> None:
        """Construct --text produces valid JSON with source.type 'constructed'."""
        template = FIXTURES_DIR / "templates" / "minimal.feedtemplate.json"
        stdout, _stderr, code = run_cli([
            "construct",
            "--template", str(template),
            "--text", "Hello world",
            "--timestamp", "2026-02-10T12:00:00Z",
        ])

        assert code == 0
        data = json.loads(stdout)
        assert data["source"]["type"] == "constructed"
        assert len(data["items"]) == 1

    def test_cli_construct_text_stdin(self) -> None:
        """Construct --text-stdin reads text from stdin."""
        template = FIXTURES_DIR / "templates" / "minimal.feedtemplate.json"
        stdout, _stderr, code = run_cli(
            [
                "construct",
                "--template", str(template),
                "--text-stdin",
                "--timestamp", "2026-02-10T12:00:00Z",
            ],
            stdin_text="Text from stdin pipe",
        )

        assert code == 0
        data = json.loads(stdout)
        assert data["items"][0]["content"] == "Text from stdin pipe"

    def test_cli_construct_entries_file(self) -> None:
        """Construct --entries reads JSONL file and produces multi-item output."""
        template = FIXTURES_DIR / "templates" / "minimal.feedtemplate.json"
        entries = FIXTURES_DIR / "entries" / "batch_entries.jsonl"
        stdout, _stderr, code = run_cli([
            "construct",
            "--template", str(template),
            "--entries", str(entries),
        ])

        assert code == 0
        data = json.loads(stdout)
        assert len(data["items"]) == 10

    def test_cli_construct_entries_stdin(self) -> None:
        """Construct --entries-stdin reads JSONL from stdin."""
        template = FIXTURES_DIR / "templates" / "minimal.feedtemplate.json"
        entries_path = FIXTURES_DIR / "entries" / "batch_entries.jsonl"
        entries_text = entries_path.read_text(encoding="utf-8")

        stdout, _stderr, code = run_cli(
            [
                "construct",
                "--template", str(template),
                "--entries-stdin",
            ],
            stdin_text=entries_text,
        )

        assert code == 0
        data = json.loads(stdout)
        assert len(data["items"]) == 10

    def test_cli_construct_output_file(self, tmp_path: Path) -> None:
        """Construct --output writes to file; stdout is empty."""
        template = FIXTURES_DIR / "templates" / "minimal.feedtemplate.json"
        out_file = tmp_path / "out.json"

        stdout, _stderr, code = run_cli([
            "construct",
            "--template", str(template),
            "--text", "Output file test",
            "--timestamp", "2026-02-10T12:00:00Z",
            "--output", str(out_file),
        ])

        assert code == 0
        assert stdout == ""
        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["status"] == "ok"

    def test_cli_construct_pretty(self) -> None:
        """Construct --pretty produces indented JSON."""
        template = FIXTURES_DIR / "templates" / "minimal.feedtemplate.json"
        stdout, _stderr, code = run_cli([
            "construct",
            "--template", str(template),
            "--text", "Pretty test",
            "--timestamp", "2026-02-10T12:00:00Z",
            "--pretty",
        ])

        assert code == 0
        assert "\n" in stdout
        assert "  " in stdout

    def test_cli_construct_missing_template(self) -> None:
        """Construct without --template produces error and exit code 2."""
        # argparse makes --template required, so this should error
        _stdout, stderr, code = run_cli([
            "construct",
            "--text", "X",
            "--timestamp", "2026-02-10T12:00:00Z",
        ])

        assert code == 2
        assert "template" in stderr.lower() or "required" in stderr.lower()

    def test_cli_construct_invalid_template(self) -> None:
        """Construct with invalid template produces TemplateValidationError and exit 2."""
        template = FIXTURES_DIR / "templates" / "invalid_missing_title.feedtemplate.json"
        _stdout, stderr, code = run_cli([
            "construct",
            "--template", str(template),
            "--text", "Test",
            "--timestamp", "2026-02-10T12:00:00Z",
        ])

        assert code == 2
        assert "templatevalidationerror" in stderr.lower() or "title" in stderr.lower()

    def test_cli_construct_missing_timestamp(self) -> None:
        """Construct --text without --timestamp produces error and exit code 2."""
        template = FIXTURES_DIR / "templates" / "minimal.feedtemplate.json"
        _stdout, stderr, code = run_cli([
            "construct",
            "--template", str(template),
            "--text", "X",
        ])

        assert code == 2
        assert "timestamp" in stderr.lower()

    def test_cli_construct_nonexistent_template(self) -> None:
        """Construct --template with nonexistent file produces error and exit 2."""
        _stdout, stderr, code = run_cli([
            "construct",
            "--template", "no_such_file.json",
            "--text", "X",
            "--timestamp", "2026-02-10T12:00:00Z",
        ])

        assert code == 2
        assert "not found" in stderr.lower() or "error" in stderr.lower()

    def test_cli_construct_bad_jsonl_entry(self) -> None:
        """Construct with JSONL containing a bad line produces exit code 1 (partial)."""
        template = FIXTURES_DIR / "templates" / "minimal.feedtemplate.json"
        entries = FIXTURES_DIR / "entries" / "bad_entries.jsonl"
        stdout, _stderr, code = run_cli([
            "construct",
            "--template", str(template),
            "--entries", str(entries),
        ])

        assert code == 1  # partial failure — some entries skipped
        data = json.loads(stdout)
        # Should have valid entries (3 valid out of 4 lines)
        assert len(data["items"]) == 3


# ═══════════════════════════════════════════════════════════════════════════
# Global options and edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestCliGlobal:
    """Global CLI option tests."""

    def test_cli_version(self) -> None:
        """--version prints version string matching _version.py."""
        stdout, _stderr, code = run_cli(["--version"])

        assert code == 0
        assert __version__ in stdout

    def test_cli_help(self) -> None:
        """--help prints usage with parse and construct subcommands."""
        stdout, stderr, code = run_cli(["--help"])

        assert code == 0
        combined = stdout + stderr
        assert "parse" in combined.lower()
        assert "construct" in combined.lower()

    def test_cli_parse_help(self) -> None:
        """parse --help prints parse-specific options."""
        stdout, stderr, code = run_cli(["parse", "--help"])

        assert code == 0
        combined = stdout + stderr
        assert "--url" in combined
        assert "--file" in combined

    def test_cli_construct_help(self) -> None:
        """construct --help prints construct-specific options."""
        stdout, stderr, code = run_cli(["construct", "--help"])

        assert code == 0
        combined = stdout + stderr
        assert "--template" in combined
        assert "--text" in combined

    def test_cli_unknown_subcommand(self) -> None:
        """Unknown subcommand produces error and exit code 2."""
        _stdout, _stderr, code = run_cli(["frobnicate"])

        assert code == 2

    def test_cli_pipe_json_to_jq(self) -> None:
        """CLI output parses as valid JSON (simulating jq piping).

        We verify that the output is valid JSON that can be deserialized
        and queried — the actual jq binary is not required.
        """
        fixture = FIXTURES_DIR / "rss2" / "minimal.xml"
        stdout, _stderr, code = run_cli(["parse", "--file", str(fixture)])

        assert code == 0
        data = json.loads(stdout)
        # Simulate jq '.items[0].title' — just access the field
        assert isinstance(data["items"], list)
        if data["items"]:
            assert "title" in data["items"][0]
