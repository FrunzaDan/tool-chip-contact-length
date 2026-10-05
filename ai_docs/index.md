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
build.sh                Dev checks: sets up .venv with the dev extra, then Ruff, mypy, pytest (no dataset run)
run.sh                  Convenience script: finds Python, checks/installs deps, runs the app, logs everything
pyproject.toml          PEP 621 manifest: deps (OpenCV, NumPy), `dev` extra (pytest, ruff, mypy), tool config — no build-system, the app runs as scripts

src/
  main.py               Entry point: configure_logging(), then folder_loop.process_folder(); returns exit code 0/1
  folder_loop.py        process_folder(): iterates the input folder (sorted), calls process_image for each .bmp; owns the folder-path constants
  process_image.py      process_image(): the per-image pipeline — read -> resize -> crop -> grayscale -> Otsu -> closing -> dilation -> contours -> Hough/measure -> plot
  contours.py           get_contours(): blur + Canny + contour filtering, returns a single-channel contour image for the Hough step
  hough_lines.py        measure_contact_length(): Hough detection, line cleanup/classification, contact-length calculation, result image saving
  plot.py               save_entire_process_plot(): the 6-panel diagnostic grid for each image
  random_color.py       random_line_color(): random bright BGR color for annotations
  logging_config.py     configure_logging(): rotating file + console handlers on the root logger

tests/                  pytest unit tests (hough_lines, contours, process_image helpers, random_color)
ai_docs/                This documentation
Documentation/          Flow diagram, per-step example images (used below), original write-up (PDF/TCCL.pages)
.vscode/                Debug config, install/clean/lint/type-check/test tasks, Ruff as formatter

Input/Complete_Dataset/        Source .bmp images (one per high-speed camera frame) — git-ignored, not in the repo
Output/folder_hough_results/   Annotated result images (same name as input, .bmp) — only for frames where both lines were found
Output/folder_plot_results/    6-panel diagnostic plots (<image_base_name>.png, one per successfully processed image)
Logs/                          run_<timestamp>.log (from run.sh) and TCCL_process_<timestamp>.log (from the app itself)
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
2. Run `python main.py` from inside `src/` (the modules import each other as top-level modules, so `src/` must be the working directory — as in `.vscode/launch.json`).

Either way, put the `.bmp` frames to analyze in `Input/Complete_Dataset/` first (the folder is git-ignored, so a fresh clone has no dataset). Files are processed in sorted name order. Results appear in `Output/folder_hough_results/` and `Output/folder_plot_results/` (both created automatically if missing); a new log file is created in `Logs/` for each run.

**Development:** `./build.sh` sets up `.venv` with `pip install -e '.[dev]'` and runs every check (`--skip-tests` skips pytest). Checks can also run manually, or via the VS Code tasks: `pytest`, `ruff check .`, `ruff format .`, `mypy`. See [dev_environment.md](dev_environment.md).

## Step-by-step pipeline

Each image goes through the same sequence of steps, implemented in `process_image.process_image(image_path)` (a `pathlib.Path`; the image name is `image_path.name`). Every step runs through `_run_step(step_name, image_name, func, *args)`, which catches any exception, logs `"<step> Error at <image>"` with the traceback (`logger.exception`), and returns the `_STEP_FAILED` sentinel; the pipeline then stops for that image and the batch moves on (`folder_loop.py` also catches per-image exceptions for the same reason). A sentinel is used instead of `None` because a step may legitimately return `None` (the plot step does). The sentinel is an `Enum` member and `_run_step` is typed with `ParamSpec`/`TypeVar`, so after each `if result is _STEP_FAILED: return` mypy knows `result` is the step's real return type.

### 1. Read

The `.bmp` file is loaded with `cv2.imread`. Since `cv2.imread` doesn't raise an error on failure — it just returns `None` for a missing/corrupt/unsupported file — that case is checked explicitly and logged as a clear "could not read image" error rather than crashing on the next step.

### 2. Resize

The image is resized to a fixed width of 1080 px (`RESIZE_WIDTH`, height scaled proportionally, `INTER_LINEAR`), so that all subsequent pixel-based thresholds and kernel sizes behave consistently regardless of the camera's native resolution.

| Original |
|---|
| ![Original](../Documentation/Images/Original.png) |

### 3. Crop (right half)

*In plain terms: throw away the left half of the photo — the cutting action always happens on the right side of the frame, so there's no point analyzing the rest.*

Only the right half of the resized image is kept. The camera frame always shows the tool-chip interface on the right side, so cropping removes irrelevant background and roughly halves the pixels the rest of the pipeline has to process. The crop is returned as a real copy (`.copy()`), not a NumPy view, because step 9 draws its annotations onto this image and must not mutate the resized image shown in the diagnostic plot.

| Cropped (half) |
|---|
| ![Half](../Documentation/Images/Half.png) |

### 4. Grayscale

The cropped color image is converted to a single-channel grayscale image, which is what all the subsequent thresholding/edge steps expect.

### 5. OTSU threshold

*In plain terms: turn the gray photo into pure black and white, letting the computer pick the best cutoff point automatically instead of guessing a fixed brightness value.*

`cv2.threshold(image, 0, OTSU_MAX_VALUE, THRESH_BINARY | THRESH_OTSU)` automatically picks a global brightness threshold (the `0` passed in is ignored) and produces a binary image with foreground pixels set to `OTSU_MAX_VALUE` (255). This separates the bright tool/chip material from the dark background.

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

`get_contours(dilated_image, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2, CANNY_APERTURE_SIZE)`, on the dilated mask:
1. A Gaussian blur (9×9, sigma 1) smooths the shape boundary.
2. `cv2.Canny` (100 / 200, `apertureSize=3`) extracts edges from the blurred mask. The aperture must be passed by keyword: Canny's 4th positional parameter is the `edges` output buffer. (It used to be passed positionally, so `CANNY_APERTURE_SIZE` was silently ignored; results were unaffected only because OpenCV's default aperture is also 3.)
3. `cv2.findContours` (`RETR_EXTERNAL`, `CHAIN_APPROX_NONE`) finds the external contours in the edge map.
4. Only contours with arc length > 500 px are redrawn (white, thickness 2) onto a black **single-channel** image — this discards small noise contours and keeps just the main tool/chip outline. That single-channel `contour_image` is what the Hough step consumes.

If the blur or Canny call raises `cv2.error`, it's logged and a blank image is returned (the pipeline continues; the Hough step then finds no lines).

| Canny / contours |
|---|
| ![Canny](../Documentation/Images/Canny.png) |

### 9. Hough line detection (`hough_lines.py`)

*In plain terms: this is the "measuring" step — find the two straight edges that matter (the flat workpiece/chip edge and the tool's edge), mark the key point on each, and subtract to get the contact length.*

This is where the actual measurement happens.

Entry point: `measure_contact_length(contour_image, cropped_image, 90, 90, 80, image_name)`. Full detail in [line_detection_and_measurement.md](line_detection_and_measurement.md).

1. **Line detection** (`detect_hough_lines`) — the contour image is blurred (3×3) and passed through the probabilistic Hough transform (`cv2.HoughLinesP`, 90 votes, min length 90, max gap 80) to get candidate line segments, each also drawn onto a separate `hough_image_plot` for the diagnostic grid. `HoughLinesP` returns `None` (not an empty list) when it finds no lines; that case is handled explicitly — the frame's measurement is skipped with a warning.
2. **Line cleanup** (`clean_lines`) — lines whose angle is within 4.5° of an already-kept line are treated as duplicates and discarded, collapsing many overlapping detections to a handful of distinct lines. The angle is deliberately *directed* (`atan2`, so a segment and its reverse differ) — normalizing it was tested and lost 34 of 314 measurements.

   | Hough lines (raw) | Cleaned lines |
   |---|---|
   | ![Hough_Lines](../Documentation/Images/Hough_Lines.png) | ![Cleaned_Lines](../Documentation/Images/Cleaned_Lines.png) |

3. **Classification** — from the cleaned lines, the code looks for:
   - A **horizontal** line (`get_horizontal_line_y_index`): near-flat (`|y1 - y2| < 10`), representing the visible top of the workpiece/chip edge.
   - A **vertical** line (`get_vertical_line_y_index`): near-vertical (`|x1 - x2| < 4`) and past an empirically tuned position threshold (half the image height/width, compared in a dimensionally odd way that is intentional — see [known_gaps.md](known_gaps.md)), representing the tool's contact edge.

   Each takes the *first* qualifying line. For each, the lowest point (largest y) on the line is taken as the reference point, marked with a circle and its Y coordinate printed on the image.

4. **Contact length calculation** — the tool-chip contact length is simply the difference between the two reference Y coordinates:

   ```
   contact_length = y_point_of_horizontal - y_point_of_vertical
   ```

   This is only the part of the contact length that is visible in the image. The full contact length is `contact_length + t`, where `t` is the **cutting depth** between the tool and the material: a constant of the cutting setup that can't be computed from the image by the OpenCV processing. That's why the result image is labeled `Dist = <n>px + t` — `t` is added outside this program.

   A result `<= 0` logs a "result is suspect" warning (likely line misclassification) but is still saved.

   The diagram below illustrates the geometry: `a` and `b` are distances from the top of the frame to the horizontal and vertical reference points respectively, `c` is the vertical line's extent, and `d = a - c` is the resulting contact length.

   | Geometry (blueprint) |
   |---|
   | ![Blueprint](../Documentation/Images/Blueprint.png) |

5. **Result image** — the two lines and their labeled points are drawn on the cropped original image, along with a `Dist = <n>px + t` text annotation, and saved to `Output/folder_hough_results/<image_name>`. The annotations are drawn directly onto the cropped image (a mutation, by design).

   | Overlay result |
   |---|
   | ![Overlay](../Documentation/Images/Overlay.png) |

If either the horizontal or vertical line can't be found, a warning is logged and no result image is saved for that frame. `measure_contact_length` always returns `hough_image_plot` (raw Hough lines on black), so step 10 runs either way.

### 10. Diagnostic plot (`plot.py`)

`save_entire_process_plot(...)` assembles a 2×3 diagnostic grid — `Original` (the resized full frame, not the crop) / `OTSU BINARY` / `MORPH CLOSING: 4x4` / `DILATION: 3x3` / `CANNY` (actually the filtered contour image; title kept to match `Documentation/Images/Canny.png`) / `HOUGH LINES` — under the image name as a title — each panel's image framed by a thin (1 px) black border, and the raw Hough lines drawn in red — and saves it to `Output/folder_plot_results/<image_base_name>.png` for visual QA of the whole pipeline on that frame.

The grid is composited directly with OpenCV (resize-to-fit + tile + `cv2.putText` titles) rather than Matplotlib: profiling showed Matplotlib's `savefig()` alone accounted for ~94% of total per-image processing time, since this is plain image tiling with plain titles, not an actual data plot. The OpenCV version produces the same 6-panel layout (each panel's aspect ratio preserved via letterboxing) in roughly a quarter of the time — around a 3-4x speedup for the whole pipeline in practice.

## Logging

Each module logs through its own `logging.getLogger(__name__)`; `main()` calls `logging_config.configure_logging()` once at startup, which sets the root logger to INFO, clears any existing handlers, and attaches a console handler plus a rotating file handler (`Logs/TCCL_process_<timestamp>.log`, 10 MB per file, 5 backups; format `time - module - LEVEL - message`). Log calls use lazy `%`-style arguments (`logger.info("Saved %s", path)`), not f-strings, so messages are only formatted if emitted. Nothing is configured at import time, so importing modules (e.g. from tests) doesn't create log files. Every step of the pipeline logs its progress or errors, so a full run can be audited after the fact without re-running it. When the app is launched via `run.sh`, that script additionally writes its own `Logs/run_<timestamp>.log` covering the setup steps (Python/dependency checks) and a copy of the app's console output.

## Error handling philosophy

Every image is processed independently: an exception at any pipeline step (read, resize, crop, threshold, morphology, contour extraction, Hough detection, or plotting) is caught with a broad `except Exception` in `_run_step` (not just OpenCV-specific errors, since real failures often surface as plain Python exceptions rather than `cv2.error`) and logged with the step, image name, and traceback. Anything escaping `process_image` is caught in `folder_loop.process_folder` and `main()` via `logger.exception` (with traceback), and the loop moves on to the next image. A single malformed or unusual frame never aborts the whole batch. Only a failure of the batch itself (e.g. missing input folder) makes `main()` return exit code 1.

"Soft" failures — unreadable file (`cv2.imread` → `None`), no Hough lines, horizontal/vertical line not found, non-positive length — are logged as errors/warnings rather than raised.

## Cross-platform notes

- All file paths are `pathlib.Path` objects built with `/` (the right separator is used per platform), so the app runs unmodified on Windows, Linux, and macOS. They're converted with `str()` only where passed to `cv2.imread`/`cv2.imwrite`.
- The `Output/folder_hough_results/` and `Output/folder_plot_results/` folders are created automatically when `folder_loop` is imported, and `Logs/` when logging is configured.
- Hidden/system files such as macOS's `.DS_Store` are skipped quietly (logged at info level) rather than being flagged as an unexpected non-BMP file. Subdirectories are skipped too.
- The `.bmp` extension check is case-sensitive: `*.BMP` files are skipped with a warning.

## Documented Concepts

Deeper dives into specific parts of the system, kept as separate files per `learning_approach.md`:

- [line_detection_and_measurement.md](line_detection_and_measurement.md) — Hough line detection, cleanup/classification, and the contact-length calculation
- [pipeline_parameters.md](pipeline_parameters.md) — every tunable constant across the pipeline, gathered in one place
- [dev_environment.md](dev_environment.md) — how `run.sh`, `pyproject.toml`, and the VS Code config fit together
- [known_gaps.md](known_gaps.md) — known bugs, empirically-hacky code, and missing pieces (test coverage, config, etc.) for future work
- [learning_approach.md](learning_approach.md) — how this `ai_docs/` knowledge base is meant to be maintained
