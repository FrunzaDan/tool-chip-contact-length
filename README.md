# Tool-Chip Contact Length

A Python computer-vision tool that measures the tool-chip contact length in metal-cutting photos taken by a high-speed camera. It processes a folder of frames in one batch and measures each one in pixels, replacing slow manual measurement of every frame.

---

## 🚀 Key Features

- **Batch processing:** Runs every `.bmp` frame in the input folder through the same pipeline, in sorted order. A failure on one image is logged and the batch moves on.
- **Classic OpenCV pipeline:** Resize, crop, grayscale, Otsu threshold, morphological closing and dilation, Canny edges and contour filtering, then probabilistic Hough line detection.
- **Contact length measurement:** Classifies the detected lines into the tool's vertical edge and the chip's horizontal edge, and measures the pixel distance between them.
- **Annotated results:** Saves each frame with the detected lines and measured length drawn on it.
- **Diagnostic plots:** Saves a 6-panel image per frame showing every intermediate stage, so you can check where a measurement went wrong.
- **Run logging:** `run.sh` checks the environment, installs missing dependencies and writes a timestamped run log with a summary (images found, results produced, timings).

---

## 🛠 Tech Stack

- **Frontend:** N/A (command-line tool)
- **Backend:** Python 3.11+
- **Database / Storage:** Local files: `.bmp` input frames, `.bmp`/`.png` outputs, `.log` files
- **Tooling & Other:** OpenCV (`opencv-python`), NumPy, pytest, Ruff (lint + format), mypy (strict), PEP 621 `pyproject.toml`

---

## 📋 Prerequisites

Before running this project, ensure you have the following installed:

- Python 3.11 or newer, with `pip`
- Bash (macOS, Linux, or WSL/Git Bash on Windows) for `run.sh`
- `unzip`, to extract the sample dataset

---

## ⚙️ Local Setup & Running

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

The script finds a Python 3.11+ interpreter, installs any missing dependencies from `pyproject.toml`, runs `src/main.py` and prints a summary at the end.

To run it manually instead:

```bash
pip install opencv-python numpy
cd src
python main.py
```

Run it from inside `src/`, because the modules import each other as top-level modules.

For development:

```bash
pip install -e '.[dev]'
pytest
ruff check .
ruff format .
mypy
```

---

## 🔌 API / App Usage

Outputs are written to:

| Folder | Contents |
|---|---|
| `Output/folder_hough_results/` | Annotated frames (same name as the input, `.bmp`), only for frames where both edges were found |
| `Output/folder_plot_results/` | One 6-panel diagnostic plot per processed frame (`.png`) |
| `Logs/` | `run_<timestamp>.log` from `run.sh` and `TCCL_process_<timestamp>.log` from the app |

The overall flow is shown in [`Documentation/Diagrams/TCCL_General_Flow.jpeg`](Documentation/Diagrams/TCCL_General_Flow.jpeg). The step-by-step pipeline, with an example image for each stage, is documented in [`ai_docs/index.md`](ai_docs/index.md).

---

## 📝 License & Notes

Personal project with no license file.

- Measurements are in pixels. Converting to millimetres needs the camera's scale, which the tool doesn't apply.
- There's no CSV or other aggregate output yet. Each value is drawn on its result image and written to the process log.
- Known limitations and open questions are listed in [`ai_docs/known_gaps.md`](ai_docs/known_gaps.md).
