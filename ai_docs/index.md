# Tool-Chip Contact Length (TCCL) — Documentation

## In plain English

When a lathe or milling tool cuts metal, the chip it peels off stays in contact with the tool's face for a short distance before curling away — that distance is the **tool-chip contact length**. A high-speed camera photographs the cutting zone, and this program measures that distance automatically, in pixels, from each photo.

It does this the way you might do it by hand with tracing paper: turn the photo black-and-white so the tool and chip stand out from the background, clean up the shape so its edge is one smooth line instead of a noisy, jagged one, find the two straight edges that matter (the flat edge of the workpiece/chip, and the edge of the tool), and measure the gap between them. The rest of this document walks through exactly how each of those "tracing paper" steps is implemented in code, with a picture of what the image looks like at every stage.

## Overview

This application measures the **Tool-Chip Contact Length** in metal-cutting images taken by a high-speed camera. It uses classic computer vision (OpenCV) to isolate the cutting tool and the chip in each image, detect the two relevant straight edges (the tool's contact edge and the chip's trailing edge), and compute the pixel distance between them.

The program is a batch pipeline: it loops over every image in an input folder, runs each one through the same image-processing pipeline, and writes two kinds of results per image:

- An annotated image showing the detected lines and the measured contact length (in pixels).
- A diagnostic plot showing every intermediate processing stage side by side, for visual verification/debugging.

See `Documentation/Diagrams/TCCL_General_Flow.jpeg` for the original flow diagram referenced in the README.

## Project layout

```
run.sh                   Convenience script: finds Python, checks/installs deps, runs the app, logs everything
pyproject.toml            PEP 621 dependency manifest (OpenCV, NumPy) — no build-system, since the app runs as scripts, not an installed package

src/
  main.py             Entry point — starts the batch run and top-level error handling
  folder_loop.py        Iterates over the input folder, calls process_image for each .bmp file
  process_image.py      The per-image pipeline: resize -> crop -> threshold -> morphology -> edges -> Hough lines -> plot
  contours.py           Blur + Canny + contour filtering, used to clean up the dilated mask before Hough
  hough_lines.py        Hough line detection, line cleanup/classification, contact-length calculation, result image saving
  plot.py               Saves the 6-panel diagnostic figure for each image
  random_color.py       Small helper: random BGR color for annotations
  logging_config.py     configure_logging(): rotating file + console handlers on the root logger

Input/Complete_Dataset/   Source .bmp images (one per high-speed camera frame)
Output/folder_hough_results/   Annotated result images (one per input image, .bmp)
Output/folder_plot_results/    6-panel diagnostic plots (one per input image, always .png)
Logs/                      Timestamped run logs: run_<timestamp>.log (from run.sh) and TCCL_process_<timestamp>.log (from the app itself)
```

## How to run it

**Easiest: use the provided script.**

```
./run.sh
```

`run.sh` (macOS/Linux, or Windows via WSL/Git Bash) does the whole setup-and-run in one step:
1. Locates a Python 3.11+ interpreter on `PATH` (tries `python3`, then `python`) and checks its version. 3.11+ is required so the script can parse `pyproject.toml` with the standard-library `tomllib` module — no extra dependency needed just to read the dependency list.
2. Checks which packages declared in `pyproject.toml`'s `[project.dependencies]` are already installed (reporting each one's exact installed version and location) and installs whatever's missing.
3. Runs `src/main.py` and logs its own steps — plus a final summary of images processed, results produced, and how long it took — to `Logs/run_<timestamp>.log`, in addition to the app's own per-image log.

**Manual alternative:**

1. Install dependencies: `pip install opencv-python numpy` (as declared in `pyproject.toml`).
2. Put the `.bmp` frames to analyze in `Input/Complete_Dataset/`.
3. Run `src/main.py` (working directory `src/`, as configured in `.vscode/launch.json`).

Either way, put the `.bmp` frames to analyze in `Input/Complete_Dataset/` first. Results appear in `Output/folder_hough_results/` and `Output/folder_plot_results/` (both created automatically if missing); a new log file is created in `Logs/` for each run.

## Step-by-step pipeline

Each image goes through the same sequence of steps, implemented in `process_image.py`. Every step is wrapped in its own try/except so a failure on one image is logged and skipped without stopping the batch (`folder_loop.py` also catches per-image exceptions for the same reason).

### 1. Read

The `.bmp` file is loaded with `cv2.imread`. Since `cv2.imread` doesn't raise an error on failure — it just returns `None` for a missing/corrupt/unsupported file — that case is checked explicitly and logged as a clear "could not read image" error rather than crashing on the next step.

### 2. Resize

The image is resized to a fixed width of 1080 px (height scaled proportionally), so that all subsequent pixel-based thresholds and kernel sizes behave consistently regardless of the camera's native resolution.

| Original |
|---|
| ![Original](../Documentation/Images/Original.png) |

### 3. Crop (right half)

*In plain terms: throw away the left half of the photo — the cutting action always happens on the right side of the frame, so there's no point analyzing the rest.*

Only the right half of the resized image is kept. The camera frame always shows the tool-chip interface on the right side, so cropping removes irrelevant background and roughly halves the pixels the rest of the pipeline has to process.

| Cropped (half) |
|---|
| ![Half](../Documentation/Images/Half.png) |

### 4. Grayscale

The cropped color image is converted to a single-channel grayscale image, which is what all the subsequent thresholding/edge steps expect.

### 5. OTSU threshold

*In plain terms: turn the gray photo into pure black and white, letting the computer pick the best cutoff point automatically instead of guessing a fixed brightness value.*

`cv2.threshold` with `THRESH_BINARY + THRESH_OTSU` automatically picks a global brightness threshold and produces a binary (black/white) image. This separates the bright tool/chip material from the dark background.

| Binary |
|---|
| ![Binary](../Documentation/Images/Binary.png) |

### 6. Morphological closing

*In plain terms: patch up tiny holes or speckles inside the white shape so it's one solid blob instead of a shape full of little dark dots.*

A 4×4 kernel with 10 iterations of `MORPH_CLOSE` closes small dark gaps/holes inside the bright regions, producing solid, continuous shapes for the tool and chip.

| Noise reduction (closing) |
|---|
| ![Noise_Reduction](../Documentation/Images/Noise_Reduction.png) |

### 7. Dilation

*In plain terms: fatten up the white shape a bit more, so any remaining thin gaps along its edge get sealed shut before we try to trace that edge.*

A 3×3 kernel with 8 iterations of `cv2.dilate` grows the white regions further, closing any remaining gaps along the tool-chip contact zone so the edge that will be detected later is continuous rather than jagged/broken.

| Dilation |
|---|
| ![Dilation](../Documentation/Images/Dilation.png) |

### 8. Contours / Canny edges (`contours.py`)

*In plain terms: trace the outline of the solid white blob as a clean line, and throw away any tiny stray outlines that are just leftover noise.*

On the dilated mask:
1. A Gaussian blur (9×9) smooths the shape boundary.
2. `cv2.Canny` extracts edges from the blurred mask.
3. `cv2.findContours` finds the external contours in the edge map.
4. Only contours with arc length > 500 px are kept and redrawn onto a blank image — this discards small noise contours and keeps just the main tool/chip outline.

| Canny / contours |
|---|
| ![Canny](../Documentation/Images/Canny.png) |

### 9. Hough line detection (`hough_lines.py`)

*In plain terms: this is the "measuring" step — find the two straight edges that matter (the flat workpiece/chip edge and the tool's edge), mark the key point on each, and subtract to get the contact length.*

This is where the actual measurement happens.

1. **Line detection** — the single-channel contour image is blurred and passed through the probabilistic Hough transform (`cv2.HoughLinesP`) to get a set of candidate straight line segments. `HoughLinesP` returns `None` (not an empty list) when it finds no lines at all; that case is handled explicitly — the frame is skipped with a warning instead of crashing.
2. **Line cleanup** (`clean_lines`) — lines are grouped by angle; lines whose angle is within 4.5° of an already-kept line are treated as duplicates and discarded. This collapses many overlapping detections down to a handful of distinct lines.

   | Hough lines (raw) | Cleaned lines |
   |---|---|
   | ![Hough_Lines](../Documentation/Images/Hough_Lines.png) | ![Cleaned_Lines](../Documentation/Images/Cleaned_Lines.png) |

3. **Classification** — from the cleaned lines, the code looks for:
   - A **horizontal** line (`get_horizontal_line_y_index`): near-flat (`|y1 - y2| < 10`), representing the visible top of the workpiece/chip edge.
   - A **vertical** line (`get_vertical_line_y_index`): near-vertical (`|x1 - x2| < 4`), positioned in the right half of the frame, representing the tool's contact edge.

   For each, the lowest point (largest y) on the line is taken as the reference point, marked with a circle and its Y coordinate printed on the image.

4. **Contact length calculation** — the tool-chip contact length is simply the difference between the two reference Y coordinates:

   ```
   contact_length = y_point_of_horizontal - y_point_of_vertical
   ```

   The diagram below illustrates the geometry: `a` and `b` are distances from the top of the frame to the horizontal and vertical reference points respectively, `c` is the vertical line's extent, and `d = a - c` is the resulting contact length.

   | Geometry (blueprint) |
   |---|
   | ![Blueprint](../Documentation/Images/Blueprint.png) |

5. **Result image** — the two lines and their labeled points are drawn on the cropped original image, along with a `Dist = <n>px` text annotation, and saved to `Output/folder_hough_results/<image_name>`.

   | Overlay result |
   |---|
   | ![Overlay](../Documentation/Images/Overlay.png) |

If either the horizontal or vertical line can't be found, a warning is logged and no result image is saved for that frame.

### 10. Diagnostic plot (`plot.py`)

A 6-panel diagnostic grid (Original / OTSU binary / morphological closing / dilation / Canny / Hough lines) is assembled and saved to `Output/folder_plot_results/<image_base_name>.png` for visual QA of the whole pipeline on that frame.

The grid is composited directly with OpenCV (resize-to-fit + tile + `cv2.putText` titles) rather than Matplotlib: profiling showed Matplotlib's `savefig()` alone accounted for ~94% of total per-image processing time, since this is plain image tiling with plain titles, not an actual data plot. The OpenCV version produces the same 6-panel layout (each panel's aspect ratio preserved via letterboxing) in roughly a quarter of the time — around a 3-4x speedup for the whole pipeline in practice.

## Logging

Each module logs through its own `logging.getLogger(__name__)`; `main.py` calls `logging_config.configure_logging()` once at startup, which attaches handlers to the root logger that write to both the console and a rotating log file (`Logs/TCCL_process_<timestamp>.log`, 10 MB per file, 5 backups). Every step of the pipeline logs its progress or errors, so a full run can be audited after the fact without re-running it. When the app is launched via `run.sh`, that script additionally writes its own `Logs/run_<timestamp>.log` covering the setup steps (Python/dependency checks) and a copy of the app's console output.

## Error handling philosophy

Every image is processed independently: an exception at any pipeline step (read, resize, crop, threshold, morphology, contour extraction, Hough detection, or plotting) is caught with a broad `except Exception` (not just OpenCV-specific errors, since real failures — e.g. a `None` image or missing lines — often surface as plain Python exceptions rather than `cv2.error`), logged with context (including a traceback at the folder-loop level), and the loop moves on to the next image. A single malformed or unusual frame never aborts the whole batch.

## Cross-platform notes

- All file paths are built with `os.path.join` (no hardcoded `/` or `\`), so the app runs unmodified on Windows, Linux, and macOS.
- The `Output/folder_hough_results/` and `Output/folder_plot_results/` folders are created automatically on startup if they don't already exist.
- Hidden/system files such as macOS's `.DS_Store` are skipped quietly (logged at info level) rather than being flagged as an unexpected non-BMP file.

## Documented Concepts

Deeper dives into specific parts of the system, kept as separate files per `learning_approach.md`:

- [line_detection_and_measurement.md](line_detection_and_measurement.md) — Hough line detection, cleanup/classification, and the contact-length calculation
- [pipeline_parameters.md](pipeline_parameters.md) — every tunable constant across the pipeline, gathered in one place
- [dev_environment.md](dev_environment.md) — how `run.sh`, `pyproject.toml`, and the VS Code config fit together
- [known_gaps.md](known_gaps.md) — known bugs, empirically-hacky code, and missing pieces (tests, config, etc.) for future work
