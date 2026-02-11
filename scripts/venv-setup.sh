#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# venv-setup.sh — Virtual environment setup for shruggie-feedtools
#
# Usage:
#   ./scripts/venv-setup.sh [--python <cmd>] [--force] [--help]
#
# Options:
#   --python <cmd>  Python interpreter to use (default: python3.12, python3, python)
#   --force         Delete and recreate the venv even if it exists
#   --help          Show this help and exit
# ---------------------------------------------------------------------------

PYTHON_CMD=""
FORCE=false

usage() {
    sed -n '/^# Usage:/,/^# ---/p' "$0" | sed 's/^# //' | sed 's/^#//' | head -n -1
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --python)
            PYTHON_CMD="$2"
            shift 2
            ;;
        --force)
            FORCE=true
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

VENV_DIR="$PROJECT_ROOT/.venv"

# ---------------------------------------------------------------------------
# Find Python interpreter
# ---------------------------------------------------------------------------

find_python() {
    if [[ -n "$PYTHON_CMD" ]]; then
        if command -v "$PYTHON_CMD" &>/dev/null; then
            echo "$PYTHON_CMD"
            return
        fi
        echo "Error: Python interpreter '$PYTHON_CMD' not found." >&2
        exit 1
    fi

    for candidate in python3.12 python3 python; do
        if command -v "$candidate" &>/dev/null; then
            echo "$candidate"
            return
        fi
    done

    echo "Error: No Python interpreter found. Install Python >=3.12 from https://python.org" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Check Python version >= 3.12
# ---------------------------------------------------------------------------

check_python_version() {
    local interpreter="$1"
    local version_output
    version_output=$("$interpreter" --version 2>&1)

    if [[ "$version_output" =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
        local major="${BASH_REMATCH[1]}"
        local minor="${BASH_REMATCH[2]}"
        if [[ "$major" -gt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -ge 12 ]]; }; then
            return 0
        fi
        echo "Error: Python >=3.12 is required. Found: Python $major.$minor. Install from https://python.org" >&2
        return 1
    fi

    echo "Error: Could not parse Python version from: $version_output" >&2
    return 1
}

PYTHON="$(find_python)"
check_python_version "$PYTHON"

# ---------------------------------------------------------------------------
# Check existing venv
# ---------------------------------------------------------------------------

if [[ -d "$VENV_DIR" ]] && [[ "$FORCE" == false ]]; then
    VENV_PYTHON="$VENV_DIR/bin/python"
    if [[ -x "$VENV_PYTHON" ]]; then
        if check_python_version "$VENV_PYTHON"; then
            echo "Virtual environment OK: $VENV_DIR"
            exit 0
        else
            echo "Warning: Existing venv has wrong Python version. Recreating..."
            rm -rf "$VENV_DIR"
        fi
    else
        echo "Warning: Existing venv is missing python. Recreating..."
        rm -rf "$VENV_DIR"
    fi
fi

# ---------------------------------------------------------------------------
# Create venv
# ---------------------------------------------------------------------------

if [[ "$FORCE" == true ]] && [[ -d "$VENV_DIR" ]]; then
    echo "Removing existing venv (--force)..."
    rm -rf "$VENV_DIR"
fi

echo "Creating virtual environment at $VENV_DIR ..."
"$PYTHON" -m venv "$VENV_DIR"

# ---------------------------------------------------------------------------
# Activate and install
# ---------------------------------------------------------------------------

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing shruggie-feedtools in editable mode with dev and GUI extras..."
cd "$PROJECT_ROOT"
pip install -e ".[dev,gui]"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo ""
echo "Virtual environment ready: $VENV_DIR"
python --version
pip list --format=columns
