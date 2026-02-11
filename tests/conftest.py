"""Shared test fixtures and configuration for shruggie-feedtools tests."""

from __future__ import annotations

import difflib
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom CLI options for pytest."""
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Regenerate snapshot golden files from current output",
    )


@pytest.fixture
def fixtures_path() -> Path:
    """Return the path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def assert_snapshot(request: pytest.FixtureRequest):
    """Compare output against a golden file. Create/update with --update-snapshots."""
    update = request.config.getoption("--update-snapshots", default=False)

    def _assert(output: dict, name: str, subfolder: str = "") -> None:
        snapshot_path = SNAPSHOT_DIR / subfolder / f"{name}.json"
        serialized = (
            json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )

        if update:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(serialized, encoding="utf-8")
            return

        if not snapshot_path.exists():
            pytest.fail(
                f"Snapshot not found: {snapshot_path}\n"
                "Run pytest --update-snapshots to create it."
            )

        expected = snapshot_path.read_text(encoding="utf-8")
        if serialized != expected:
            diff = difflib.unified_diff(
                expected.splitlines(keepends=True),
                serialized.splitlines(keepends=True),
                fromfile=f"snapshot/{name}.json",
                tofile="actual output",
            )
            pytest.fail(f"Snapshot mismatch:\n{''.join(diff)}")

    return _assert


@pytest.fixture
def load_fixture(fixtures_path: Path):
    """Load a fixture file and return its contents as bytes."""

    def _load(relative_path: str) -> bytes:
        path = fixtures_path / relative_path
        return path.read_bytes()

    return _load


@pytest.fixture
def load_fixture_text(fixtures_path: Path):
    """Load a fixture file and return its contents as text."""

    def _load(relative_path: str, encoding: str = "utf-8") -> str:
        path = fixtures_path / relative_path
        return path.read_text(encoding=encoding)

    return _load
