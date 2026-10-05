#!/usr/bin/env bash
# Sets up the project's .venv with the runtime and dev dependencies, then checks
# linting and formatting (Ruff), type-checks (mypy, strict) and runs the unit tests
# (pytest). It does not process the dataset; ./run.sh does that.
# Pass --skip-tests to skip the test step for a faster sanity build.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
MIN_PYTHON="3.11"  # tomllib (used by run.sh) arrived in 3.11; matches requires-python

SKIP_TESTS=0
for arg in "$@"; do
  case "$arg" in
    --skip-tests) SKIP_TESTS=1 ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Usage: $0 [--skip-tests]" >&2
      exit 1
      ;;
  esac
done

cd "$ROOT_DIR"

echo "==> [1/5] Checking prerequisites"
PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Missing required tool: python3" >&2
  echo "  - Python $MIN_PYTHON+: https://www.python.org/downloads/" >&2
  exit 1
fi
if ! "$PYTHON_BIN" -c "import sys; sys.exit(0 if sys.version_info >= (${MIN_PYTHON/./, }) else 1)"; then
  echo "Python $MIN_PYTHON or newer is required; $(command -v "$PYTHON_BIN") is $("$PYTHON_BIN" --version 2>&1)." >&2
  exit 1
fi

echo "==> [2/5] Installing dependencies into .venv"
# The same .venv run.sh and VS Code use, never the system interpreter (PEP 668).
if [[ ! -d "$VENV_DIR" ]]; then
  echo "    No .venv found, creating one with $(command -v "$PYTHON_BIN")..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# Git Bash on Windows lays a venv out as Scripts/python.exe instead of bin/python.
if [[ -x "$VENV_DIR/bin/python" ]]; then
  VENV_PYTHON="$VENV_DIR/bin/python"
else
  VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
fi
if ! "$VENV_PYTHON" -c "import sys; sys.exit(0 if sys.version_info >= (${MIN_PYTHON/./, }) else 1)" 2>/dev/null; then
  echo "$VENV_DIR is broken or uses a Python older than $MIN_PYTHON. Delete it and re-run." >&2
  exit 1
fi
# Same install as the VS Code "Install Python Dependencies" task.
"$VENV_PYTHON" -m pip install --quiet --disable-pip-version-check -e '.[dev]'

echo "==> [3/5] Checking linting and formatting (Ruff)"
"$VENV_PYTHON" -m ruff check .
"$VENV_PYTHON" -m ruff format --check .

echo "==> [4/5] Type-checking (mypy)"
"$VENV_PYTHON" -m mypy

echo "==> [5/5] Running unit tests (pytest)"
if [[ "$SKIP_TESTS" -eq 1 ]]; then
  echo "    Skipped (--skip-tests)"
else
  "$VENV_PYTHON" -m pytest
fi

echo "==> Build complete."
