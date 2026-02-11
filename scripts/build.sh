#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# build.sh — Build shruggie-feedtools release executables using PyInstaller
#
# Usage:
#   ./scripts/build.sh [--target cli|gui|all] [--release] [--clean] [--help]
#
# Options:
#   --target <t>  Build target: cli, gui, or all (default: all)
#   --release     Copy artifacts to dist/release/ with versioned filenames
#   --clean       Delete build/ and dist/ before building
#   --help        Show this help and exit
# ---------------------------------------------------------------------------

TARGET="all"
RELEASE=false
CLEAN=false

usage() {
    sed -n '/^# Usage:/,/^# ---/p' "$0" | sed 's/^# //' | sed 's/^#//' | head -n -1
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            TARGET="$2"
            shift 2
            ;;
        --release)
            RELEASE=true
            shift
            ;;
        --clean)
            CLEAN=true
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

# Validate target
case "$TARGET" in
    cli|gui|all) ;;
    *)
        echo "Error: Invalid target '$TARGET'. Must be cli, gui, or all." >&2
        exit 2
        ;;
esac

START_TIME=$(date +%s)

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

echo "Ensuring virtual environment is ready..."
bash "$SCRIPT_DIR/venv-setup.sh"

VENV_DIR="$PROJECT_ROOT/.venv"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ---------------------------------------------------------------------------
# Read version
# ---------------------------------------------------------------------------

VERSION_FILE="$PROJECT_ROOT/src/shruggie_feedtools/_version.py"
VERSION=$(grep -oP '__version__\s*=\s*"\K[^"]+' "$VERSION_FILE")

if [[ -z "$VERSION" ]]; then
    echo "Error: Could not extract version from $VERSION_FILE" >&2
    exit 1
fi

echo "Building shruggie-feedtools v$VERSION"

# ---------------------------------------------------------------------------
# Clean if requested
# ---------------------------------------------------------------------------

if [[ "$CLEAN" == true ]]; then
    if [[ -d "$PROJECT_ROOT/build" ]]; then
        echo "Removing build/ ..."
        rm -rf "$PROJECT_ROOT/build"
    fi
    if [[ -d "$PROJECT_ROOT/dist" ]]; then
        if [[ "$RELEASE" == true ]]; then
            # Keep release/ subfolder
            find "$PROJECT_ROOT/dist" -maxdepth 1 -mindepth 1 ! -name "release" -exec rm -rf {} +
        else
            echo "Removing dist/ ..."
            rm -rf "$PROJECT_ROOT/dist"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Build targets
# ---------------------------------------------------------------------------

cd "$PROJECT_ROOT"

if [[ "$TARGET" == "cli" ]] || [[ "$TARGET" == "all" ]]; then
    echo "Building CLI target..."
    python -m PyInstaller \
        --onefile \
        --name "shruggie-feedtools-cli" \
        --console \
        src/shruggie_feedtools/__main__.py

    echo "CLI build complete."
fi

if [[ "$TARGET" == "gui" ]] || [[ "$TARGET" == "all" ]]; then
    echo "Building GUI target..."
    python -m PyInstaller \
        --onefile \
        --name "shruggie-feedtools-gui" \
        --windowed \
        --add-data "src/shruggie_feedtools/gui:shruggie_feedtools/gui" \
        src/shruggie_feedtools/gui/app.py

    echo "GUI build complete."
fi

# ---------------------------------------------------------------------------
# Release artifacts
# ---------------------------------------------------------------------------

if [[ "$RELEASE" == true ]]; then
    RELEASE_DIR="$PROJECT_ROOT/dist/release"
    mkdir -p "$RELEASE_DIR"

    ARCH=$(uname -m)
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')

    if [[ "$TARGET" == "cli" ]] || [[ "$TARGET" == "all" ]]; then
        CLI_SRC="$PROJECT_ROOT/dist/shruggie-feedtools-cli"
        CLI_DST="$RELEASE_DIR/shruggie-feedtools-cli-$VERSION-$OS-$ARCH"
        if [[ -f "$CLI_SRC" ]]; then
            cp "$CLI_SRC" "$CLI_DST"
            SIZE=$(stat -f%z "$CLI_DST" 2>/dev/null || stat -c%s "$CLI_DST" 2>/dev/null || echo "unknown")
            echo "  CLI: $CLI_DST ($SIZE bytes)"
        fi
    fi

    if [[ "$TARGET" == "gui" ]] || [[ "$TARGET" == "all" ]]; then
        GUI_SRC="$PROJECT_ROOT/dist/shruggie-feedtools-gui"
        GUI_DST="$RELEASE_DIR/shruggie-feedtools-gui-$VERSION-$OS-$ARCH"
        if [[ -f "$GUI_SRC" ]]; then
            cp "$GUI_SRC" "$GUI_DST"
            SIZE=$(stat -f%z "$GUI_DST" 2>/dev/null || stat -c%s "$GUI_DST" 2>/dev/null || echo "unknown")
            echo "  GUI: $GUI_DST ($SIZE bytes)"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "Build complete."
echo "  Target: $TARGET"
echo "  Version: $VERSION"
echo "  Duration: ${ELAPSED}s"
