# Tool-Chip Contact Length — Project Overview

## What is it?

Tool-Chip Contact Length (TCCL) is a small Python program that **measures a distance in photos of metal being cut**.

When a cutting tool (on a lathe, for example) removes metal, the strip of metal it peels off, the **chip**, slides along the face of the tool for a short distance before curling away. That distance is called the **tool-chip contact length**. It matters in machining research because it affects heat, tool wear and cutting forces.

A high-speed camera films the cutting zone, producing hundreds of still frames. Measuring the contact length on each frame by hand would take hours. This program does it automatically: it reads every frame, finds the edge of the tool and the edge of the chip, and measures the gap between them in pixels.

It uses **classic image processing** (OpenCV) rather than machine learning, so every step can be seen and checked.

## Why it exists

The goal is to replace a slow, manual measurement on hundreds of frames with an automatic one. It was also a good way to learn practical computer vision: thresholding, morphology, edge detection and line detection, and how to tune them so they work reliably on real, noisy photos. The original write-up is in `Documentation/PDF/TCCL.pages`, and the overall flow is sketched in `Documentation/Diagrams/TCCL_General_Flow.jpeg`.

---

## The big picture

```
Input/Complete_Dataset/*.bmp          (high-speed camera frames)
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  For each frame, in name order:                                 │
│                                                                 │
│   read → resize → keep right half → grayscale → black & white   │
│        → fill holes → thicken → trace outline                   │
│        → find straight lines → pick tool edge + chip edge       │
│        → measure the distance                                   │
└─────────────────────────────────────────────────────────────────┘
          │                                 │
          ▼                                 ▼
Output/folder_hough_results/        Output/folder_plot_results/
  annotated frame with the            6-panel diagnostic image
  lines and the measurement           showing every stage

                     + Logs/ (what happened, frame by frame)
```

There is no web page, server or database. It's a command-line batch job: files in, files out.

---

## The building blocks

All the code is in `src/`:

| File | What it does |
|---|---|
| `main.py` | The starting point. Sets up logging, then processes the whole folder. |
| `folder_loop.py` | Goes through every `.bmp` in the input folder, in sorted order, and hands each one to the pipeline. Holds the folder paths. |
| `process_image.py` | The per-frame pipeline: read, resize, crop, grayscale, threshold, closing, dilation, then the contour and line steps. Holds most of the tuning numbers. |
| `contours.py` | Blurs the shape, finds its edges, and keeps only the long outline (dropping small specks). |
| `hough_lines.py` | Finds straight lines, removes duplicates, picks the tool edge and the chip edge, measures the distance, and saves the annotated result. |
| `plot.py` | Builds the 6-panel diagnostic image for each frame. |
| `logging_config.py` | Sends log messages to the console and to a log file. |
| `random_color.py` | Picks a bright random colour for drawing the lines. |

Unit tests live in `tests/`.

---

## How a frame is processed

Each step below has an example image in `Documentation/Images/`.

| # | Step | In plain words | Example |
|---|---|---|---|
| 1 | **Read** | Load the `.bmp` file. | |
| 2 | **Resize** | Scale it to 1080 px wide, so all the later numbers work the same whatever the camera resolution. | [Original](Images/Original.png) |
| 3 | **Crop** | Keep only the right half, where the cutting happens. | [Half](Images/Half.png) |
| 4 | **Grayscale** | Drop colour; the next steps only need brightness. | |
| 5 | **Black & white (Otsu)** | Turn the image into pure black and white. Otsu's method picks the best brightness cut-off automatically. | [Binary](Images/Binary.png) |
| 6 | **Fill holes (closing)** | Patch small dark specks inside the white shape, so it becomes one solid blob. | [Noise reduction](Images/Noise_Reduction.png) |
| 7 | **Thicken (dilation)** | Grow the white shape a little, sealing thin gaps along its edge. | [Dilation](Images/Dilation.png) |
| 8 | **Trace the outline (Canny + contours)** | Find the edge of the blob and keep only long outlines, throwing away small noise. | [Canny](Images/Canny.png) |
| 9 | **Find straight lines (Hough)** | Look for straight line segments in the outline. | [Hough lines](Images/Hough_Lines.png) |
| 10 | **Clean up the lines** | Lines at almost the same angle are treated as one, leaving a handful of distinct lines. | [Cleaned lines](Images/Cleaned_Lines.png) |
| 11 | **Pick the two edges** | A nearly **horizontal** line is the top of the workpiece/chip; a nearly **vertical** line past the middle of the image is the tool's edge. | |
| 12 | **Measure** | Take the lowest point of each line and subtract their heights. | [Overlay](Images/Overlay.png) |
| 13 | **Diagnostic plot** | Put six stages side by side in one image, so a bad measurement is easy to trace back. | |

### The measurement itself

```
contact_length = y (horizontal line) − y (vertical line)       in pixels
```

The result is written on the image as `Dist = <n>px + t`. The `t` is the **cutting depth**, a fixed value from the experiment's setup that can't be seen in the photo, so it's added afterwards, outside the program. The geometry is drawn in [`Images/Blueprint.png`](Images/Blueprint.png).

### When something goes wrong

Every step is wrapped so that a problem with one frame (an unreadable file, no lines found, only one of the two edges found) is **logged and skipped**, and the batch moves on to the next frame. One odd frame never stops the run. If the measured length comes out zero or negative, it's saved anyway, with a warning in the log that the result is suspect.

---

## Input, output and storage

| | Where | What |
|---|---|---|
| **Input** | `Input/Complete_Dataset/` | `.bmp` frames from the high-speed camera. The repo includes the sample dataset as `Input/Complete_Dataset.zip` (about 100 MB, 404 frames), to be unzipped in place. |
| **Output** | `Output/folder_hough_results/` | One annotated `.bmp` per frame where both edges were found, with the same name as the input. |
| **Output** | `Output/folder_plot_results/` | One 6-panel `.png` per processed frame. |
| **Logs** | `Logs/` | `TCCL_process_<timestamp>.log` from the program (every step, every warning) and `run_<timestamp>.log` from `run.sh`. |

There is no database. Measurements are in pixels; turning them into millimetres needs the camera's scale, which comes from the experiment setup.

---

## Packages and tools, and why they're used

| Package / tool | Why |
|---|---|
| **Python 3.11+** | The language. 3.11 or newer is needed because `run.sh` reads `pyproject.toml` with the built-in `tomllib` module. |
| **`opencv-python`** (OpenCV) | All the image processing: reading/writing images, resizing, thresholding, morphology, Canny edges, contours, Hough lines and drawing. It also builds the diagnostic plots. |
| **`numpy`** | OpenCV images are NumPy arrays; used for the kernels and array maths. |
| **`pytest`** | Unit tests for line cleanup, line classification, measurement and pipeline helpers. |
| **`ruff`** | Linting and formatting, with a broad rule set (naming, docstrings, pathlib, logging style, security). |
| **`mypy`** (strict mode) | Type checking. |
| **`pyproject.toml`** | One file listing the dependencies (instead of `requirements.txt`) and configuring pytest, Ruff and mypy. |

The diagnostic plots used to be drawn with Matplotlib. Profiling showed that saving the Matplotlib figure took about 94% of the time per image, so they're now assembled with OpenCV directly. The whole run got roughly 3–4× faster.

---

## Setting it up (for future me)

### What you need

- Python 3.11 or newer, with `pip`
- Bash (macOS, Linux, or WSL / Git Bash on Windows)
- `unzip`

### First time

```bash
cd Input
unzip Complete_Dataset.zip
cd ..
```

### Run it

```bash
./run.sh
```

It finds a suitable Python, creates `.venv` if needed, installs any missing dependencies from `pyproject.toml`, runs the program and prints a summary at the end: images found, results produced and how long it took.

To run it by hand instead:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install opencv-python numpy
cd src
python main.py           # must be run from inside src/
```

### Check the code

```bash
./build.sh               # Ruff (lint + format check), mypy, pytest; --skip-tests skips pytest
```

It doesn't process the dataset; it only checks the code.

### Where to change things

| To change… | Look in… |
|---|---|
| Input / output folders | Constants at the top of `src/folder_loop.py` |
| Tuning numbers (resize width, kernel sizes, iterations, Canny and Hough thresholds) | Constants in `src/process_image.py` (and the call into `hough_lines.py`) |
| What each tuning number does | `ai_docs/pipeline_parameters.md` |

---

## Decisions and why I made them

- **Classic image processing, not machine learning.** It needs no training data, and every step is explainable. With OpenCV each stage produces a picture you can look at, so it's clear why a frame was measured the way it was.
- **Crop to the right half.** In this camera setup the cutting zone is always on the right side, so analysing the left half only adds noise and time.
- **Resize everything to 1080 px wide first.** The kernel sizes and line thresholds are in pixels; a fixed width makes them behave the same on every frame.
- **Heavy closing and dilation.** Raw frames are noisy and the edges are jagged. Making the shape solid first gives Canny one clean outline to follow instead of hundreds of small fragments.
- **Keep going when a frame fails.** In a batch of hundreds of frames, a few will always be blurry or unusual. Logging and skipping them is more useful than stopping the run.
- **A diagnostic plot for every frame.** When a number looks wrong, you can see at a glance which stage went off.
- **Line angles keep their direction.** When removing duplicate lines, a line and its reverse count as different angles. Treating them as the same was tested and lost 34 of 314 measurements.
- **Plain scripts, not an installable package.** It's run from `src/`, and `pyproject.toml` only describes dependencies and tool settings.

---

## Interesting bits

- **The results are visual.** You can flick through `Output/folder_hough_results/` like a flip-book and watch the measured contact length change from frame to frame.
- **Cross-platform.** All paths use `pathlib`, so the same code runs on macOS, Linux and Windows. Hidden files such as `.DS_Store` are skipped quietly.
- **Logs are complete.** Every step of every frame is logged, so a run can be checked afterwards without running it again.

## Glossary

| Term | Meaning |
|---|---|
| Chip | The strip of metal removed by the cutting tool. |
| Contact length | How far the chip stays in contact with the tool's face. |
| Frame | One still image from the high-speed camera. |
| Otsu threshold | A method that picks the best brightness cut-off to turn a gray image into black and white. |
| Morphological closing / dilation | Operations that fill small holes and grow white areas in a black-and-white image. |
| Canny | A widely used edge-detection method. |
| Hough transform | A method for finding straight lines in an image of edges. |
| `t` | The cutting depth, a constant from the experiment, added to the measured pixel distance. |

For the step-by-step technical walkthrough see [`ai_docs/index.md`](../ai_docs/index.md), and for line detection in detail see [`ai_docs/line_detection_and_measurement.md`](../ai_docs/line_detection_and_measurement.md).
