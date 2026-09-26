# Dev Environment & Run Setup

## What it is

How the project's dependencies, run script, test suite, and editor integration fit together — the "getting it running" concept, as opposed to the image-processing pipeline itself.

## Key files / paths

- `pyproject.toml` — PEP 621 manifest: runtime deps (`opencv-python`, `numpy`), a `dev` extra (`pytest`), and pytest config (`[tool.pytest.ini_options]`: `pythonpath = ["src"]`, `testpaths = ["tests"]`). No `[build-system]` table, since the app runs as scripts, not an installed package.
- `run.sh` — cross-platform setup + run script (Bash).
- `src/main.py` — the entry point both `run.sh` and the VS Code debug config execute.
- `src/logging_config.py` — `configure_logging()`, called once by `main()`.
- `tests/` — pytest unit tests (see [[known_gaps]] for what they don't cover).
- `.vscode/launch.json` — F5 debug config: runs `src/main.py` with cwd `src/`, `preLaunchTask` = `Install Python Dependencies`, `postDebugTask` = `Clean Python Project`.
- `.vscode/tasks.json` — `Install Python Dependencies`, `Clean Python Project` (deletes `.pytest_cache`), `Format with Black` (formats `src/` only) tasks.
- `.vscode/settings.json` — Black as formatter, format-on-save/on-type, type inlay hints.
- `.gitignore` — ignores `Input/` (the dataset is not in the repo), `Logs/*.log`, and generated `Output/` images.

## How it works

- `run.sh` is the primary entry point:
  1. Finds a Python 3.11+ interpreter (`python3`, then `python`). 3.11+ is required only so it can read `pyproject.toml` with the standard-library `tomllib`. Also logs OS, interpreter path/implementation/version, venv yes/no, and `pip --version`.
  2. Reads `[project.dependencies]`, checks each with `pip show` (logging version + location), and `pip install`s only the missing ones.
  3. `cd src && python main.py`, tee'ing output into `Logs/run_<timestamp>.log`.
  4. Prints a summary: input `.bmp` count, result/plot files created *by this run* (compared against a temp marker file's mtime), image-processing time, total time. Exits with the app's exit code.
- `main()` calls `configure_logging()` (root logger → console + `Logs/TCCL_process_<timestamp>.log`), then `folder_loop.process_folder()`.
- The VS Code debug config takes a different path: its `preLaunchTask` reads the same `pyproject.toml` dependency list via an inline `tomllib` one-liner and installs into `.venv` (`source .venv/bin/activate`), rather than reusing `run.sh`.
- Tests: `python3 -m pytest` from the repo root. Only `pytest` itself is needed on top of the runtime deps — `pythonpath = ["src"]` makes the flat `src/` modules importable (`import hough_lines`, etc.) without installing the project. The README's `pip install -e .[dev]` is one way to get pytest; quote it as `'.[dev]'` in zsh.
- Importing modules in tests has one side effect: importing `folder_loop` (directly, or via `hough_lines`/`plot`/`process_image`) creates `Output/folder_hough_results/` and `Output/folder_plot_results/`. Logging is *not* configured on import, so tests don't create log files.

## Gotchas / conventions

- Dependency-install logic exists in two independent places (`run.sh` and the VS Code task); both parse `pyproject.toml` directly. Keep both in sync if that logic changes. Neither installs the `dev` extra.
- The VS Code tasks assume a `.venv/` at the repo root and a POSIX shell (`source .venv/bin/activate`); they won't work on plain Windows cmd/PowerShell without edits. `run.sh` requires Bash (WSL or Git Bash on Windows).
- Modules in `src/` import each other as top-level modules (`import folder_loop`), so the app must run with `src/` as cwd or on `sys.path` — `run.sh`, `launch.json`, and pytest's `pythonpath` all arrange that.
- `settings.json` uses `python.formatting.provider`, which newer VS Code Python extensions ignore (formatter is now set per-language via the Black extension).
- No CI config exists; tests are run by hand.
