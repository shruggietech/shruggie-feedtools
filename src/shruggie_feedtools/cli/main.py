"""CLI main entry point.

Implements ``shruggie-feedtools parse`` and ``shruggie-feedtools construct``
subcommands using :mod:`argparse`.  Exit codes follow §7.4:
- 0 = success
- 1 = partial failure (some feeds/entries failed)
- 2 = argument error or template validation error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from shruggie_feedtools._version import __version__
from shruggie_feedtools.utils.logging import setup_logging

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _serialize(data: dict[str, Any] | list[dict[str, Any]], *, pretty: bool, indent: int) -> str:
    """Serialize data to a JSON string."""
    if pretty:
        return json.dumps(data, indent=indent, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


def _write_output(text: str, output_path: str | None) -> None:
    """Write JSON text to a file or stdout."""
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Parse subcommand
# ---------------------------------------------------------------------------


def _handle_parse(args: argparse.Namespace) -> int:
    """Execute the ``parse`` subcommand.  Returns an exit code."""
    from shruggie_feedtools.core.config import ParserConfig
    from shruggie_feedtools.core.parser import (
        parse_file as _parse_file,
    )
    from shruggie_feedtools.core.parser import (
        parse_files as _parse_files,
    )
    from shruggie_feedtools.core.parser import (
        parse_url as _parse_url,
    )
    from shruggie_feedtools.core.parser import (
        parse_urls as _parse_urls,
    )

    config = ParserConfig(
        max_items=args.max_items,
        verify_ssl=not args.no_verify_ssl,
        pretty_print=args.pretty,
        indent=args.indent,
    )
    if args.timeout is not None:
        config.timeout_read = args.timeout
        config.timeout_connect = min(args.timeout, config.timeout_connect)
    if args.user_agent is not None:
        config.user_agent = args.user_agent

    results: list[dict[str, Any]] = []

    # -- Determine input mode ------------------------------------------------
    if args.url:
        results.append(_parse_url(args.url, config))

    elif args.url_list:
        url_path = Path(args.url_list)
        if not url_path.exists():
            print(f"Error: URL list file not found: {args.url_list}", file=sys.stderr)
            return 2
        urls = [
            line.strip()
            for line in url_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        results.extend(_parse_urls(urls, config))

    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            return 2
        results.append(_parse_file(file_path, config))

    elif args.files:
        missing = [f for f in args.files if not Path(f).exists()]
        if missing:
            print(f"Error: Files not found: {', '.join(missing)}", file=sys.stderr)
            return 2
        results.extend(_parse_files([Path(f) for f in args.files], config))

    elif args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
            return 2
        feed_files = sorted(dir_path.iterdir())
        feed_files = [f for f in feed_files if f.is_file()]
        if not feed_files:
            print(f"Error: No files found in directory: {args.dir}", file=sys.stderr)
            return 2
        results.extend(_parse_files(feed_files, config))

    elif args.stdin:
        # Read URLs from stdin, one per line
        lines = sys.stdin.read().splitlines()
        urls = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
        if not urls:
            print("Error: No URLs provided on stdin", file=sys.stderr)
            return 2
        results.extend(_parse_urls(urls, config))

    else:
        print("Error: No input specified. Use --url, --file, --stdin, etc.", file=sys.stderr)
        print("Run 'shruggie-feedtools parse --help' for usage.", file=sys.stderr)
        return 2

    # -- Output routing ------------------------------------------------------
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, result in enumerate(results):
            fname = f"feed_{i + 1}.json"
            out_path = out_dir / fname
            text = _serialize(result, pretty=args.pretty, indent=args.indent)
            out_path.write_text(text + "\n", encoding="utf-8")
    elif len(results) == 1:
        text = _serialize(results[0], pretty=args.pretty, indent=args.indent)
        _write_output(text, args.output)
    else:
        # Multiple results — emit as a JSON array
        text = _serialize(results, pretty=args.pretty, indent=args.indent)
        _write_output(text, args.output)

    # -- Determine exit code -------------------------------------------------
    has_error = any(r.get("status") == "error" for r in results)
    has_ok = any(r.get("status") == "ok" for r in results)

    if has_error and has_ok:
        return 1  # partial failure
    if has_error:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Construct subcommand
# ---------------------------------------------------------------------------


def _handle_construct(args: argparse.Namespace) -> int:
    """Execute the ``construct`` subcommand.  Returns an exit code."""
    from shruggie_feedtools.construct import construct, construct_batch
    from shruggie_feedtools.construct.entry import parse_entries
    from shruggie_feedtools.construct.template import TemplateValidationError, load_template

    # -- Validate template ---------------------------------------------------
    template_path = Path(args.template)
    if not template_path.exists():
        print(f"Error: Template file not found: {args.template}", file=sys.stderr)
        return 2

    try:
        template = load_template(template_path)
    except TemplateValidationError as exc:
        print(f"TemplateValidationError: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON in template: {exc}", file=sys.stderr)
        return 2

    # -- Determine input mode ------------------------------------------------
    if args.text is not None:
        # Single item from --text argument
        if not args.timestamp:
            print("Error: --timestamp is required for single-item modes.", file=sys.stderr)
            return 2
        result = construct(args.text, args.timestamp, template)

    elif args.text_stdin:
        # Single item from stdin
        if not args.timestamp:
            print("Error: --timestamp is required for single-item modes.", file=sys.stderr)
            return 2
        text = sys.stdin.read()
        result = construct(text, args.timestamp, template)

    elif args.entries:
        # Batch from JSONL file
        entries_path = Path(args.entries)
        if not entries_path.exists():
            print(f"Error: Entries file not found: {args.entries}", file=sys.stderr)
            return 2
        parsed_entries = parse_entries(entries_path)
        if not parsed_entries:
            print("Error: No valid entries found in file.", file=sys.stderr)
            return 2
        result = construct_batch(parsed_entries, template)

    elif args.entries_stdin:
        # Batch from stdin JSONL
        lines = sys.stdin.read().splitlines()
        parsed_entries = parse_entries(lines)
        if not parsed_entries:
            print("Error: No valid entries found on stdin.", file=sys.stderr)
            return 2
        result = construct_batch(parsed_entries, template)

    else:
        print(
            "Error: No input specified. Use --text, --text-stdin, "
            "--entries, or --entries-stdin.",
            file=sys.stderr,
        )
        return 2

    # -- Check for partial failures (bad JSONL entries) ----------------------
    exit_code = 0
    if args.entries or args.entries_stdin:
        # If we read a file/stdin and got fewer items than input lines,
        # some entries were skipped (warnings already logged by parse_entries).
        if args.entries:
            total_lines = sum(
                1
                for line in Path(args.entries).read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        else:
            total_lines = sum(1 for line in lines if line.strip())
        actual_items = len(result.get("items", []))
        if actual_items < total_lines:
            exit_code = 1  # partial failure

    # -- Output routing ------------------------------------------------------
    text_out = _serialize(result, pretty=args.pretty, indent=args.indent)
    _write_output(text_out, args.output)

    return exit_code


# ---------------------------------------------------------------------------
# Argument parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argparse parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="shruggie-feedtools",
        description=(
            "Normalize web feeds into a single predictable JSON schema, "
            "or construct feeds from text and templates."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"shruggie-feedtools {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # -- Parse subcommand ----------------------------------------------------
    parse_parser = subparsers.add_parser(
        "parse",
        help="Parse web feeds from URLs, files, or stdin",
        description="Parse web feeds and normalize them to JSON.",
    )

    # Input modes (mutually exclusive)
    input_group = parse_parser.add_mutually_exclusive_group()
    input_group.add_argument("--url", help="Parse a single remote feed URL")
    input_group.add_argument("--url-list", help="Parse URLs from a file (one per line)")
    input_group.add_argument("--file", help="Parse a single local file")
    input_group.add_argument("--files", nargs="+", help="Parse multiple local files")
    input_group.add_argument("--dir", help="Parse all feed files in a directory")
    input_group.add_argument(
        "--stdin", action="store_true", help="Read URLs from stdin"
    )

    # Output options
    parse_parser.add_argument("--output", help="Write JSON to file (default: stdout)")
    parse_parser.add_argument(
        "--output-dir", help="For batch: write individual .json files to directory"
    )
    parse_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    parse_parser.add_argument(
        "--indent", type=int, default=2, help="Indentation level (default: 2)"
    )
    parse_parser.add_argument(
        "--quiet", action="store_true", help="Suppress logs; only emit JSON"
    )

    # Behavior options
    parse_parser.add_argument(
        "--timeout", type=float, help="HTTP timeout in seconds (default: 30)"
    )
    parse_parser.add_argument("--user-agent", help="Custom User-Agent header")
    parse_parser.add_argument(
        "--no-verify-ssl", action="store_true", help="Disable SSL verification"
    )
    parse_parser.add_argument(
        "--max-items", type=int, help="Limit items per feed"
    )

    # -- Construct subcommand ------------------------------------------------
    construct_parser = subparsers.add_parser(
        "construct",
        help="Construct feeds from text and templates",
        description="Construct schema-compliant feeds from text content and templates.",
    )

    # Required
    construct_parser.add_argument(
        "--template", required=True, help="Path to .feedtemplate.json file"
    )

    # Input modes (mutually exclusive)
    construct_input = construct_parser.add_mutually_exclusive_group()
    construct_input.add_argument("--text", help="Text content for a single item")
    construct_input.add_argument(
        "--text-stdin", action="store_true", help="Read text from stdin (single item)"
    )
    construct_input.add_argument(
        "--entries", help="JSONL file with multiple entries"
    )
    construct_input.add_argument(
        "--entries-stdin",
        action="store_true",
        help="Read JSONL entries from stdin",
    )

    # Timestamp
    construct_parser.add_argument(
        "--timestamp",
        help="Timestamp for the item (required for single-item modes)",
    )

    # Output options
    construct_parser.add_argument(
        "--output", help="Write JSON to file (default: stdout)"
    )
    construct_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    construct_parser.add_argument(
        "--indent", type=int, default=2, help="Indentation level (default: 2)"
    )
    construct_parser.add_argument(
        "--quiet", action="store_true", help="Suppress logs; only emit JSON"
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Parameters
    ----------
    argv:
        Command-line arguments.  Defaults to ``sys.argv[1:]``.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # -- Handle no subcommand ------------------------------------------------
    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(2)

    # -- Configure logging ---------------------------------------------------
    quiet = getattr(args, "quiet", False)
    if quiet:
        setup_logging(level=logging.CRITICAL)
    else:
        setup_logging(level=logging.WARNING)

    # -- Dispatch to handler -------------------------------------------------
    if args.command == "parse":
        exit_code = _handle_parse(args)
    elif args.command == "construct":
        exit_code = _handle_construct(args)
    else:
        print(f"Error: Unknown subcommand: {args.command}", file=sys.stderr)
        exit_code = 2

    sys.exit(exit_code)
