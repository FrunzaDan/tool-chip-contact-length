# Tool-Chip Contact Length

Tool-Chip Contact Length is a Python tool that measures the tool-chip contact length in photos of metal cutting. When a cutting tool removes metal, the chip it peels off stays in contact with the tool's face for a short distance before curling away, and that distance is the contact length. A high-speed camera captures the cutting zone frame by frame, and this tool measures that distance on every frame automatically instead of by hand. It uses classic OpenCV image processing (thresholding, morphology, edge detection and Hough line detection) rather than machine learning, so every step can be inspected. `run.sh` sets up the environment and processes the whole dataset in one command, saving an annotated image and a diagnostic plot for each frame.

---

## Key Features

- **Batch processing:** Every `.bmp` frame in the input folder goes through the same pipeline in sorted name order. If one image fails, the error is logged with a traceback and the batch moves on to the next frame.
- **Classic OpenCV pipeline:** Each frame is resized to a fixed width, cropped to the right half (where the cutting happens), converted to grayscale and thresholded with Otsu. Morphological closing and dilation then turn the tool and chip into solid shapes, and Canny edges with contour filtering keep only their main outline.
- **Contact length measurement:** Probabilistic Hough line detection finds straight edges in that outline. The lines are de-duplicated and classified into the tool's vertical edge and the chip's horizontal edge, and the contact length is the pixel distance between them.
- **Annotated results:** For every frame where both edges were found, an image is saved with the detected lines and the measured length drawn on it.
- **Diagnostic plots:** For each processed frame, a 6-panel image shows every intermediate stage side by side, so you can see exactly where a measurement went wrong.
- **One-command run script:** `run.sh` finds a Python 3.11+ interpreter, creates the project's `.venv` if there isn't one, checks the dependencies declared in `pyproject.toml` and installs any that are missing into it. It then runs the pipeline and writes a timestamped log ending in a summary of images found, results produced and how long it took.
- **Code quality checks:** pytest unit tests cover the line classification, de-duplication, measurement and pipeline helpers. Ruff handles linting and formatting, and mypy runs in strict mode.

---

## Tech Stack

- **Frontend:** N/A (command-line tool)
- **Backend:** Python 3.11+
- **Database / Storage:** Local files: `.bmp` input frames, `.bmp`/`.png` outputs, `.log` files
- **Tooling & Other:** OpenCV (`opencv-python`), NumPy, pytest, Ruff (lint + format), mypy (strict), PEP 621 `pyproject.toml`

---

## Prerequisites

Before running this project, ensure you have the following installed:

- Python 3.11 or newer, with `pip`
- Bash (macOS, Linux, or WSL/Git Bash on Windows) for `run.sh`
- `unzip`, to extract the sample dataset

---

## Local Setup & Running

### 1. Clone the repository

```bash
git clone https://github.com/FrunzaDan/tool-chip-contact-length.git
cd tool-chip-contact-length
```

### 2. Configuration

There are no settings files. Folder paths are constants in `src/folder_loop.py`, and the pipeline parameters (resize width, kernel sizes, Canny and Hough thresholds) are constants in `src/process_image.py`. See [`ai_docs/pipeline_parameters.md`](ai_docs/pipeline_parameters.md) for what each one does.

The input frames go in `Input/Complete_Dataset/`. The repo includes the sample dataset as a zip (about 100 MB, 404 frames). Extract it in place:

```bash
cd Input
unzip Complete_Dataset.zip
cd ..
```

### 3. Installation & Run

```bash
./run.sh
```

The script finds a Python 3.11+ interpreter, creates `.venv` if needed, installs any missing dependencies from `pyproject.toml` into it, runs `src/main.py` and prints a summary at the end.

To run it manually instead:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install opencv-python numpy
cd src
python main.py
```

Run it from inside `src/`, because the modules import each other as top-level modules.

For development, `./build.sh` sets up `.venv` with the dev dependencies and runs all the checks: Ruff (lint and format check), mypy and pytest. Pass `--skip-tests` to skip pytest. It doesn't process the dataset. To run the checks by hand:

```bash
source .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
ruff format .
mypy
```

---

## API / App Usage

Outputs are written to:

| Folder | Contents |
|---|---|
| `Output/folder_hough_results/` | Annotated frames (same name as the input, `.bmp`), only for frames where both edges were found |
| `Output/folder_plot_results/` | One 6-panel diagnostic plot per processed frame (`.png`) |
| `Logs/` | `run_<timestamp>.log` from `run.sh` and `TCCL_process_<timestamp>.log` from the app |

The overall flow is shown in [`Documentation/Diagrams/TCCL_General_Flow.jpeg`](Documentation/Diagrams/TCCL_General_Flow.jpeg). The step-by-step pipeline, with an example image for each stage, is documented in [`ai_docs/index.md`](ai_docs/index.md).

---

## License & Notes

Personal project with no license file.

- Measurements are in pixels. Converting to millimetres needs the camera's scale, which the tool doesn't apply.
- There's no CSV or other aggregate output yet. Each value is drawn on its result image and written to the process log.
- Known limitations and open questions are listed in [`ai_docs/known_gaps.md`](ai_docs/known_gaps.md).
