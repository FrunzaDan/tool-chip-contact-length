#!/usr/bin/env bash
#
# Runs the Tool-Chip Contact Length (TCCL) application.
#
# What it does, in order:
#   1. Locates a usable Python 3 interpreter (and checks its version), then
#      creates the project's .venv with it if there isn't one yet.
#   2. Checks which packages declared in pyproject.toml are already installed
#      in .venv, and installs whatever is missing there.
#   3. Runs the app (src/main.py) and logs everything to Logs/.
#
# Usage: ./run.sh

set -eu

# ---------------------------------------------------------------------------
# Setup: resolve paths so the script works from any working directory.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYPROJECT_FILE="$SCRIPT_DIR/pyproject.toml"
VENV_DIR="$SCRIPT_DIR/.venv"
LOG_DIR="$SCRIPT_DIR/Logs"
mkdir -p "$LOG_DIR"
RUN_LOG="$LOG_DIR/run_$(date +%Y-%m-%d_%H-%M-%S).log"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$RUN_LOG"
}

# Formats a whole number of seconds as e.g. "1h 02m 03s" / "2m 03s" / "45s".
format_duration() {
    local total_seconds=$1
    local hours=$((total_seconds / 3600))
    local minutes=$(((total_seconds % 3600) / 60))
    local seconds=$((total_seconds % 60))
    if [ "$hours" -gt 0 ]; then
        printf '%dh %02dm %02ds' "$hours" "$minutes" "$seconds"
    elif [ "$minutes" -gt 0 ]; then
        printf '%dm %02ds' "$minutes" "$seconds"
    else
        printf '%ds' "$seconds"
    fi
}

SCRIPT_START_EPOCH=$(date +%s)

log "===== TCCL run script started ====="

# ---------------------------------------------------------------------------
# Step 1: Find and validate a Python interpreter, then create/use .venv.
# ---------------------------------------------------------------------------
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11  # 3.11+ needed for the standard-library 'tomllib' TOML parser

PYTHON_BIN=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    log "ERROR: No Python interpreter found on PATH (tried 'python3' and 'python')."
    log "Install Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ from https://www.python.org/downloads/ and try again."
    exit 1
fi

PYTHON_PATH="$(command -v "$PYTHON_BIN")"
PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
PYTHON_FULL_VERSION="$("$PYTHON_BIN" -c 'import sys; print(sys.version.replace(chr(10), " "))')"
PYTHON_IMPLEMENTATION="$("$PYTHON_BIN" -c 'import platform; print(platform.python_implementation())')"
OS_NAME="$(uname -s)"
OS_ARCH="$(uname -m)"

log "----- Environment -----"
log "OS: $OS_NAME ($OS_ARCH)"
log "Python executable: $PYTHON_PATH"
log "Python implementation: $PYTHON_IMPLEMENTATION"
log "Python version: $PYTHON_FULL_VERSION"

if ! "$PYTHON_BIN" -c "import sys; sys.exit(0 if sys.version_info >= (${MIN_PYTHON_MAJOR}, ${MIN_PYTHON_MINOR}) else 1)"; then
    log "ERROR: Python $PYTHON_VERSION was found, but this app requires ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} or newer."
    exit 1
fi

# Dependencies go into the project's own virtual environment (the same .venv VS Code
# uses), never into the system interpreter: package-managed Pythons such as Homebrew's
# refuse a global `pip install` (PEP 668), and it keeps this project's versions
# separate from everything else on the machine.
if [ ! -d "$VENV_DIR" ]; then
    log "No virtual environment at $VENV_DIR, creating one with $PYTHON_PATH..."
    if ! "$PYTHON_BIN" -m venv "$VENV_DIR" >>"$RUN_LOG" 2>&1; then
        log "ERROR: Failed to create the virtual environment. See $RUN_LOG for details."
        exit 1
    fi
fi
# Git Bash on Windows lays a venv out as Scripts/python.exe instead of bin/python.
if [ -x "$VENV_DIR/bin/python" ]; then
    PYTHON_BIN="$VENV_DIR/bin/python"
else
    PYTHON_BIN="$VENV_DIR/Scripts/python.exe"
fi
if ! "$PYTHON_BIN" -c "import sys; sys.exit(0 if sys.version_info >= (${MIN_PYTHON_MAJOR}, ${MIN_PYTHON_MINOR}) else 1)" 2>/dev/null; then
    log "ERROR: $VENV_DIR is broken or uses a Python older than ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}. Delete it and re-run."
    exit 1
fi
log "Virtual environment: $VENV_DIR ($("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'))"

if ! PIP_VERSION_OUTPUT="$("$PYTHON_BIN" -m pip --version 2>&1)"; then
    log "ERROR: pip is not available for $PYTHON_BIN. Install pip (e.g. '$PYTHON_BIN -m ensurepip') and try again."
    exit 1
fi
log "pip: $PIP_VERSION_OUTPUT"
log "------------------------"

# ---------------------------------------------------------------------------
# Step 2: Check installed dependencies against pyproject.toml's
# [project.dependencies], install whatever is missing.
# ---------------------------------------------------------------------------
if [ ! -f "$PYPROJECT_FILE" ]; then
    log "ERROR: pyproject.toml not found at $PYPROJECT_FILE"
    exit 1
fi

log "Checking dependencies from pyproject.toml..."
missing_requirements=()
satisfied_count=0
total_count=0

# Read the declared dependency specs (e.g. "numpy" or "numpy>=1.20") out of
# pyproject.toml's [project.dependencies] using the standard-library TOML
# parser - one per line, so the rest of this script can stay plain bash.
while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue

    # Extract the bare package name (before any version specifier / extras /
    # environment marker).
    pkg_name="$(printf '%s' "$line" | sed -E 's/[<>=!~;\[].*$//' | sed -e 's/[[:space:]]*$//')"
    [ -z "$pkg_name" ] && continue

    total_count=$((total_count + 1))

    if package_info="$("$PYTHON_BIN" -m pip show "$pkg_name" 2>/dev/null)"; then
        installed_version="$(printf '%s\n' "$package_info" | awk -F': ' '/^Version:/ {print $2}')"
        installed_location="$(printf '%s\n' "$package_info" | awk -F': ' '/^Location:/ {print $2}')"
        log "  [OK]      $pkg_name  requirement='$line'  installed_version=$installed_version  location=$installed_location"
        satisfied_count=$((satisfied_count + 1))
    else
        log "  [MISSING] $pkg_name  requirement='$line'  (not installed)"
        missing_requirements+=("$line")
    fi
done < <("$PYTHON_BIN" -c "
import tomllib
with open('$PYPROJECT_FILE', 'rb') as f:
    data = tomllib.load(f)
for dependency in data.get('project', {}).get('dependencies', []):
    print(dependency)
")

log "Dependency check complete: $satisfied_count/$total_count requirement(s) already satisfied."

if [ ${#missing_requirements[@]} -gt 0 ]; then
    log "Installing missing dependencies (${missing_requirements[*]}) from pyproject.toml..."
    if "$PYTHON_BIN" -m pip install "${missing_requirements[@]}" >>"$RUN_LOG" 2>&1; then
        log "Dependencies installed successfully. Versions now installed:"
        for requirement in "${missing_requirements[@]}"; do
            pkg_name="$(printf '%s' "$requirement" | sed -E 's/[<>=!~;\[].*$//' | sed -e 's/[[:space:]]*$//')"
            installed_version="$("$PYTHON_BIN" -m pip show "$pkg_name" 2>/dev/null | awk -F': ' '/^Version:/ {print $2}')"
            log "  [INSTALLED] $pkg_name ($installed_version)"
        done
    else
        log "ERROR: Failed to install dependencies. See $RUN_LOG for details."
        exit 1
    fi
else
    log "All dependencies are already installed."
fi

# ---------------------------------------------------------------------------
# Step 3: Run the application.
# ---------------------------------------------------------------------------
log "--------------------"
log "Starting the Tool-Chip Contact Length application..."
log "(Detailed per-image processing logs are written by the app itself to $LOG_DIR/TCCL_process_*.log)"

# Marker file used below to count only the output files this run produced,
# not ones left over from earlier runs.
OUTPUT_MARKER="$(mktemp "$LOG_DIR/.output_marker.XXXXXX")"
APP_START_EPOCH=$(date +%s)

cd "$SCRIPT_DIR/src"

set +e
"$PYTHON_BIN" main.py 2>&1 | tee -a "$RUN_LOG"
exit_code=${PIPESTATUS[0]}
set -e

APP_END_EPOCH=$(date +%s)
APP_DURATION=$((APP_END_EPOCH - APP_START_EPOCH))
TOTAL_DURATION=$((APP_END_EPOCH - SCRIPT_START_EPOCH))

# ---------------------------------------------------------------------------
# Summary: counts and timing for this run.
# ---------------------------------------------------------------------------
INPUT_IMAGE_COUNT=$(find "$SCRIPT_DIR/Input/Complete_Dataset" -maxdepth 1 -type f -iname "*.bmp" 2>/dev/null | wc -l | tr -d ' ')
HOUGH_RESULT_COUNT=$(find "$SCRIPT_DIR/Output/folder_hough_results" -type f -newer "$OUTPUT_MARKER" 2>/dev/null | wc -l | tr -d ' ')
PLOT_RESULT_COUNT=$(find "$SCRIPT_DIR/Output/folder_plot_results" -type f -newer "$OUTPUT_MARKER" 2>/dev/null | wc -l | tr -d ' ')
rm -f "$OUTPUT_MARKER"

log "----- Summary -----"
log "Input images found:        $INPUT_IMAGE_COUNT  (in $SCRIPT_DIR/Input/Complete_Dataset)"
log "Annotated results created: $HOUGH_RESULT_COUNT  (in $SCRIPT_DIR/Output/folder_hough_results)"
log "Diagnostic plots created:  $PLOT_RESULT_COUNT  (in $SCRIPT_DIR/Output/folder_plot_results)"
log "Image processing time:     $(format_duration "$APP_DURATION")"
log "Total script time:         $(format_duration "$TOTAL_DURATION")"
log "Full run log:              $RUN_LOG"
log "--------------------"

if [ "$exit_code" -eq 0 ]; then
    log "Application finished successfully."
else
    log "ERROR: Application exited with status $exit_code."
    exit "$exit_code"
fi

log "===== TCCL run script finished ====="
