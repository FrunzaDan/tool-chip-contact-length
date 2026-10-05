# Dev Environment & Run Setup

## What it is

How the project's dependencies, run script, code-quality tooling (tests, linter, type checker), and editor integration fit together — the "getting it running" concept, as opposed to the image-processing pipeline itself.

## Key files / paths

- `pyproject.toml` — PEP 621 manifest: runtime deps (`opencv-python`, `numpy`), a `dev` extra (`pytest`, `ruff`, `mypy`), and all tool config: `[tool.pytest.ini_options]` (`pythonpath = ["src"]`, `testpaths = ["tests"]`), `[tool.ruff]`, `[tool.mypy]`. No `[build-system]` table, since the app runs as scripts, not an installed package.
- `run.sh` — cross-platform setup + run script (Bash).
- `build.sh` — dev checks (Bash): sets up `.venv`, then Ruff, mypy, pytest.
- `src/main.py` — the entry point both `run.sh` and the VS Code debug config execute.
- `src/logging_config.py` — `configure_logging()`, called once by `main()`.
- `tests/` — pytest unit tests (see [[known_gaps]] for what they don't cover).
- `.vscode/launch.json` — F5 debug config: runs `src/main.py` with cwd `src/`, `preLaunchTask` = `Install Python Dependencies`, `postDebugTask` = `Clean Python Project`.
- `.vscode/tasks.json` — `Install Python Dependencies` (`pip install -e '.[dev]'` into `.venv`), `Clean Python Project` (deletes pytest/mypy/ruff caches), `Lint & Format (ruff)`, `Type Check (mypy)`, `Run Tests (pytest)`.
- `.vscode/settings.json` — the interpreter is `.venv/bin/python`, and `src` is on Pylance's import path (mirroring pytest's `pythonpath`). Ruff as the Python formatter; on save: format, fix lint issues, sort imports. Type inlay hints.
- `.vscode/extensions.json` — recommends the Python, Ruff, and Mypy Type Checker extensions.
- `.gitignore` — ignores `Input/` (the dataset is not in the repo), `Logs/*.log`, and generated `Output/` images.

## How it works

- `run.sh` is the primary entry point:
  1. Finds a Python 3.11+ interpreter (`python3`, then `python`). 3.11+ is required only so it can read `pyproject.toml` with the standard-library `tomllib`. Also logs OS, interpreter path/implementation/version and `pip --version`. Then creates `.venv` with it if missing (the same one VS Code uses) and switches to `.venv`'s Python for everything after, so nothing is installed into the system interpreter.
  2. Reads `[project.dependencies]`, checks each with `pip show` (logging version + location), and `pip install`s only the missing ones, into `.venv`.
  3. `cd src && python main.py`, tee'ing output into `Logs/run_<timestamp>.log`.
  4. Prints a summary: input `.bmp` count, result/plot files created *by this run* (compared against a temp marker file's mtime), image-processing time, total time. Exits with the app's exit code.
- `main()` calls `configure_logging()` (root logger → console + `Logs/TCCL_process_<timestamp>.log`), then `folder_loop.process_folder()`.
- `main()` returns an exit code, passed to `sys.exit`: `0` on success, `1` if the batch itself failed (e.g. missing input folder). A failure on a single image does not change the exit code. `run.sh` passes it through.
- `build.sh` is the check entry point (also called by the workspace-level `build-all.sh`): finds Python 3.11+, creates `.venv` if missing, runs `pip install -e '.[dev]'` into it (the same install as the VS Code task), then `ruff check .`, `ruff format --check .`, `mypy` and `pytest` through `.venv`'s Python, stopping at the first failure. `--skip-tests` skips pytest. It never runs `src/main.py`.
- The VS Code debug config takes a different path: its `preLaunchTask` runs `pip install -e '.[dev]'` into `.venv` (`source .venv/bin/activate`), rather than reusing `run.sh`.
- Dev setup: `pip install -e '.[dev]'` (quote it in zsh). Editable install works without a `[build-system]` table because pip falls back to setuptools; it leaves a git-ignored `src/*.egg-info/`.
- Tests: `python3 -m pytest` from the repo root. `pythonpath = ["src"]` makes the flat `src/` modules importable (`import hough_lines`, etc.) even without installing the project.
- Linting and formatting: [Ruff](https://docs.astral.sh/ruff/) does both — `ruff check .` (add `--fix` to auto-fix) and `ruff format .`. It replaces Black (formatter), isort, flake8, and pydocstyle. Enabled rule sets (`[tool.ruff.lint] select`): pycodestyle `E`/`W`, pyflakes `F`, isort `I`, pep8-naming `N`, pydocstyle `D` (PEP 257 convention; not required in `tests/`), pyupgrade `UP`, bugbear `B`, simplify `SIM`, blind-except `BLE`, logging-format `G`, pathlib `PTH`. Line length is Ruff's default, 88.
- Type checking: `mypy` (config `files = ["src"]`, `strict = true`). OpenCV's bundled stubs type most return values as a broad `MatLike`, so results are narrowed to `npt.NDArray[np.uint8]` / `NDArray[np.int32]` with `typing.cast` where they come out of `cv2` calls.
- Importing modules in tests has one side effect: importing `folder_loop` (directly, or via `hough_lines`/`plot`/`process_image`) creates `Output/folder_hough_results/` and `Output/folder_plot_results/`. Logging is *not* configured on import, so tests don't create log files.

## Gotchas / conventions

- Dependency-install logic exists in two independent places: `run.sh` (runtime deps only, installs just what's missing) and `pip install -e '.[dev]'`, run by both `build.sh` and the VS Code task. Both are driven by `pyproject.toml`.
- The VS Code tasks assume a `.venv/` at the repo root and a POSIX shell (`source .venv/bin/activate`); they won't work on plain Windows cmd/PowerShell without edits. `run.sh` and `build.sh` require Bash (WSL or Git Bash on Windows).
- Modules in `src/` import each other as top-level modules (`import folder_loop`), so the app must run with `src/` as cwd or on `sys.path` — `run.sh`, `launch.json`, and pytest's `pythonpath` all arrange that.
- There are no git hooks or CI: the checks run only when invoked by hand or through the VS Code tasks. Ruff also formats and fixes files on save in VS Code (`.vscode/settings.json`).
