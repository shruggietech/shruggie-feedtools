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
from shruggie_feedtools.utils.logging import setup_file_logging, setup_logging

logger = __import__("logging").getLogger("shruggie_feedtools")

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

    logger.debug("parse subcommand invoked with args: %s", vars(args))

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

    logger.debug("construct subcommand invoked with args: %s", vars(args))

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
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Normalize web feeds into a single predictable JSON schema,\n"
            "or construct feeds from text and templates.\n"
            "\n"
            "Supported feed formats (parse mode):\n"
            "  RSS 2.0, RSS 1.0/RDF, RSS 0.9x, Atom 1.0, Atom 0.3.\n"
            "\n"
            "Supported construction (construct mode):\n"
            "  Template-driven feed generation from text or JSONL input\n"
            "  with configurable GUID strategies (sha256, uuid4, etc.)."
        ),
        epilog=(
            "examples:\n"
            "  # Parse a single feed URL and pretty-print the output\n"
            "  shruggie-feedtools parse --url https://example.com/feed.xml --pretty\n"
            "\n"
            "  # Parse a local feed file\n"
            "  shruggie-feedtools parse --file feed.xml --pretty\n"
            "\n"
            "  # Pipe URLs from stdin\n"
            "  echo \"https://news.ycombinator.com/rss\" | shruggie-feedtools parse --stdin --pretty\n"
            "\n"
            "  # Construct a feed item from text\n"
            "  shruggie-feedtools construct --template my.feedtemplate.json \\\n"
            "      --text \"Server rebooted unexpectedly.\" \\\n"
            "      --timestamp \"2026-02-10T03:00:00Z\" --pretty\n"
            "\n"
            "exit codes:\n"
            "  0  All operations succeeded\n"
            "  1  One or more feeds/entries failed to process\n"
            "  2  Argument error or template validation error"
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
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Parse web feeds and normalize them into a single predictable JSON schema.\n"
            "\n"
            "Supports RSS 2.0, RSS 1.0/RDF, Atom 1.0, and other XML-based feed\n"
            "formats.  Input can come from a\n"
            "single URL, a list of URLs, one or more local files, a directory\n"
            "of feed files, or stdin.  Output is always schema-compliant JSON."
        ),
        epilog=(
            "examples:\n"
            "  # Parse a single URL\n"
            "  shruggie-feedtools parse --url https://example.com/feed.xml --pretty\n"
            "\n"
            "  # Parse a local file\n"
            "  shruggie-feedtools parse --file path/to/feed.json --pretty\n"
            "\n"
            "  # Parse URLs from stdin and chain with jq\n"
            "  shruggie-feedtools parse --url https://example.com/feed | jq '.items[].title'\n"
            "\n"
            "  # Batch-parse URLs from a file, writing individual outputs\n"
            "  shruggie-feedtools parse --url-list urls.txt --output-dir results/\n"
            "\n"
            "  # Pipe URLs in via stdin\n"
            "  echo \"https://news.ycombinator.com/rss\" | shruggie-feedtools parse --stdin --pretty\n"
            "\n"
            "  # Parse all feeds in a directory with a 60-second timeout\n"
            "  shruggie-feedtools parse --dir ./feeds/ --timeout 60 --pretty"
        ),
    )

    # Input modes (mutually exclusive)
    input_group = parse_parser.add_argument_group(
        "input modes (mutually exclusive — pick one)"
    )
    input_mx = input_group.add_mutually_exclusive_group()
    input_mx.add_argument(
        "--url", metavar="URL",
        help="parse a single remote feed URL",
    )
    input_mx.add_argument(
        "--url-list", metavar="FILE",
        help="parse URLs from a text file (one URL per line, # comments ignored)",
    )
    input_mx.add_argument(
        "--file", metavar="FILE",
        help="parse a single local feed file (.xml, .json, .rss, .atom)",
    )
    input_mx.add_argument(
        "--files", nargs="+", metavar="FILE",
        help="parse multiple local feed files",
    )
    input_mx.add_argument(
        "--dir", metavar="DIRECTORY",
        help="parse all feed files found in a directory",
    )
    input_mx.add_argument(
        "--stdin", action="store_true",
        help="read URLs from stdin (one per line)",
    )

    # Output options
    output_group = parse_parser.add_argument_group("output options")
    output_group.add_argument(
        "--output", metavar="FILE",
        help="write JSON output to a file instead of stdout",
    )
    output_group.add_argument(
        "--output-dir", metavar="DIR",
        help="for batch modes: write individual .json result files to this directory",
    )
    output_group.add_argument(
        "--pretty", action="store_true",
        help="pretty-print JSON output (default: minified)",
    )
    output_group.add_argument(
        "--indent", type=int, default=2, metavar="N",
        help="indentation width when --pretty is used (default: 2)",
    )
    output_group.add_argument(
        "--quiet", action="store_true",
        help="suppress all log output; emit only JSON on stdout",
    )

    # Behavior options
    behavior_group = parse_parser.add_argument_group("behavior options")
    behavior_group.add_argument(
        "--timeout", type=float, metavar="SECONDS",
        help="HTTP connect + read timeout per request in seconds (default: 30)",
    )
    behavior_group.add_argument(
        "--user-agent", metavar="STRING",
        help="custom User-Agent header for HTTP requests",
    )
    behavior_group.add_argument(
        "--no-verify-ssl", action="store_true",
        help="disable SSL certificate verification (use with caution)",
    )
    behavior_group.add_argument(
        "--max-items", type=int, metavar="N",
        help="limit the number of items returned per feed",
    )
    behavior_group.add_argument(
        "--debug", action="store_true",
        help="enable debug logging to a .log file next to the executable",
    )

    # -- Construct subcommand ------------------------------------------------
    construct_parser = subparsers.add_parser(
        "construct",
        help="Construct feeds from text and templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Construct schema-compliant feed output from arbitrary text input using\n"
            "template files (.feedtemplate.json).  Supports single-item creation from\n"
            "a text string or stdin, and batch creation from JSONL input.\n"
            "\n"
            "Templates define feed-level metadata, item-mapping rules, and GUID\n"
            "generation strategies (sha256, uuid4, timestamp, sequential).  Output\n"
            "is structurally identical to parsed feed output and can be merged with it."
        ),
        epilog=(
            "examples:\n"
            "  # Construct a single item from inline text\n"
            "  shruggie-feedtools construct --template changelog.feedtemplate.json \\\n"
            "      --text \"Fixed login timeout bug\" \\\n"
            "      --timestamp \"2026-02-10T03:00:00Z\" --pretty\n"
            "\n"
            "  # Construct from piped text via stdin\n"
            "  echo \"The server rebooted unexpectedly.\" | \\\n"
            "      shruggie-feedtools construct \\\n"
            "          --template incident.feedtemplate.json \\\n"
            "          --text-stdin \\\n"
            "          --timestamp \"2026-02-10T03:00:00Z\"\n"
            "\n"
            "  # Batch-construct from a JSONL file\n"
            "  shruggie-feedtools construct --template changelog.feedtemplate.json \\\n"
            "      --entries events.jsonl --pretty\n"
            "\n"
            "  # Batch from stdin JSONL\n"
            "  cat events.jsonl | shruggie-feedtools construct \\\n"
            "      --template changelog.feedtemplate.json --entries-stdin --pretty"
        ),
    )

    # Template (required)
    template_group = construct_parser.add_argument_group("template")
    template_group.add_argument(
        "--template", required=True, metavar="FILE",
        help="path to a .feedtemplate.json template file (required)",
    )

    # Input modes (mutually exclusive)
    construct_input_group = construct_parser.add_argument_group(
        "input modes (mutually exclusive — pick one)"
    )
    construct_input = construct_input_group.add_mutually_exclusive_group()
    construct_input.add_argument(
        "--text", metavar="STRING",
        help="text content for a single feed item (use with --timestamp)",
    )
    construct_input.add_argument(
        "--text-stdin", action="store_true",
        help="read text content from stdin for a single item (use with --timestamp)",
    )
    construct_input.add_argument(
        "--entries", metavar="FILE",
        help="path to a JSONL file with multiple entries (each line is a JSON object)",
    )
    construct_input.add_argument(
        "--entries-stdin", action="store_true",
        help="read JSONL entries from stdin (each line is a JSON object)",
    )

    # Timestamp
    timestamp_group = construct_parser.add_argument_group("timestamp")
    timestamp_group.add_argument(
        "--timestamp", metavar="STRING",
        help=(
            "timestamp for the item, required for --text and --text-stdin modes; "
            "accepts ISO 8601, RFC 822, Unix epoch, or natural-language dates"
        ),
    )

    # Output options
    construct_output_group = construct_parser.add_argument_group("output options")
    construct_output_group.add_argument(
        "--output", metavar="FILE",
        help="write JSON output to a file instead of stdout",
    )
    construct_output_group.add_argument(
        "--pretty", action="store_true",
        help="pretty-print JSON output (default: minified)",
    )
    construct_output_group.add_argument(
        "--indent", type=int, default=2, metavar="N",
        help="indentation width when --pretty is used (default: 2)",
    )
    construct_output_group.add_argument(
        "--quiet", action="store_true",
        help="suppress all log output; emit only JSON on stdout",
    )
    construct_output_group.add_argument(
        "--debug", action="store_true",
        help="enable debug logging to a .log file next to the executable",
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
    debug = getattr(args, "debug", False)

    if debug:
        log_path = setup_file_logging()
        logger.debug("CLI started with --debug (log: %s)", log_path)
        logger.debug("Command: %s, args: %s", args.command, vars(args))
    elif quiet:
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
