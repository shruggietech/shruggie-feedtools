#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# test.sh — Run the shruggie-feedtools test suite with colored output
#
# Usage:
#   ./scripts/test.sh [--silent] [--coverage] [--filter <expr>] [--fail-fast] [--help]
#
# Options:
#   --silent      Suppress all output; exit code only (for CI)
#   --coverage    Generate coverage report
#   --filter <e>  pytest -k expression to run a subset of tests
#   --fail-fast   Stop on first failure
#   --help        Show this help and exit
# ---------------------------------------------------------------------------

SILENT=false
COVERAGE=false
FILTER=""
FAIL_FAST=false

usage() {
    sed -n '/^# Usage:/,/^# ---/p' "$0" | sed 's/^# //' | sed 's/^#//' | head -n -1
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --silent)
            SILENT=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --filter)
            FILTER="$2"
            shift 2
            ;;
        --fail-fast)
            FAIL_FAST=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Color support
# ---------------------------------------------------------------------------

USE_COLOR=false
if [[ -t 1 ]]; then
    if command -v tput &>/dev/null && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
        USE_COLOR=true
    elif [[ -n "${TERM:-}" ]] && [[ "$TERM" != "dumb" ]]; then
        USE_COLOR=true
    fi
fi

GREEN=""
RED=""
YELLOW=""
WHITE=""
GRAY=""
BOLD=""
RESET=""

if [[ "$USE_COLOR" == true ]]; then
    GREEN="\033[32m"
    RED="\033[31m"
    YELLOW="\033[33m"
    WHITE="\033[1;37m"
    GRAY="\033[90m"
    BOLD="\033[1m"
    RESET="\033[0m"
fi

# ---------------------------------------------------------------------------
# Locate project root
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

while [[ "$PROJECT_ROOT" != "/" ]]; do
    if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        break
    fi
    PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
done

if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    echo "Error: Could not find pyproject.toml in any parent directory." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Ensure venv is ready
# ---------------------------------------------------------------------------

bash "$SCRIPT_DIR/venv-setup.sh"

VENV_DIR="$PROJECT_ROOT/.venv"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ---------------------------------------------------------------------------
# Silent mode
# ---------------------------------------------------------------------------

if [[ "$SILENT" == true ]]; then
    python -m pytest --tb=no --no-header -q
    exit $?
fi

# ---------------------------------------------------------------------------
# Build pytest command
# ---------------------------------------------------------------------------

PYTHON_VERSION=$(python --version 2>&1)
TIMESTAMP=$(date +"%Y-%m-%dT%H:%M:%S")

echo ""
printf "${WHITE}%s${RESET}\n" "$(printf '=%.0s' {1..60})"
printf "${WHITE}  shruggie-feedtools Test Suite${RESET}\n"
printf "${GRAY}  %s | %s${RESET}\n" "$PYTHON_VERSION" "$TIMESTAMP"
printf "${WHITE}%s${RESET}\n" "$(printf '=%.0s' {1..60})"
echo ""

PYTEST_ARGS=("--tb=short" "-v")

if [[ "$COVERAGE" == true ]]; then
    PYTEST_ARGS+=("--cov=shruggie_feedtools" "--cov-report=term-missing")
fi

if [[ -n "$FILTER" ]]; then
    PYTEST_ARGS+=("-k" "$FILTER")
fi

if [[ "$FAIL_FAST" == true ]]; then
    PYTEST_ARGS+=("-x")
fi

# ---------------------------------------------------------------------------
# Run pytest and process output
# ---------------------------------------------------------------------------

START_TIME=$(date +%s)

set +e
python -m pytest "${PYTEST_ARGS[@]}" 2>&1 | while IFS= read -r line; do
    if echo "$line" | grep -q "PASSED"; then
        printf "  ${GREEN}✓ PASS${RESET}  %s\n" "$(echo "$line" | sed 's/PASSED//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
    elif echo "$line" | grep -q "FAILED"; then
        printf "  ${RED}✗ FAIL${RESET}  %s\n" "$(echo "$line" | sed 's/FAILED//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
    elif echo "$line" | grep -q "SKIPPED"; then
        printf "  ${YELLOW}○ SKIP${RESET}  %s\n" "$(echo "$line" | sed 's/SKIPPED//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
    elif echo "$line" | grep -qE "^tests[/\\\\]"; then
        echo ""
        printf "  ${WHITE}%s${RESET}\n" "$line"
    else
        echo "  $line"
    fi
done
EXIT_CODE=${PIPESTATUS[0]}
set -e

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------

echo ""
printf "${WHITE}%s${RESET}\n" "$(printf '=%.0s' {1..60})"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    printf "  ${GREEN}ALL TESTS PASSED${RESET}\n"
else
    printf "  ${RED}SOME TESTS FAILED${RESET}\n"
fi

printf "  ${GRAY}Duration: %ss${RESET}\n" "$ELAPSED"
printf "${WHITE}%s${RESET}\n" "$(printf '=%.0s' {1..60})"
echo ""

exit "$EXIT_CODE"
