# Pipeline Tunable Parameters

## What it is

Every magic-number knob that controls how an image is processed or how outputs look, gathered in one place with what it affects and which file owns it. The pipeline steps themselves are documented in `index.md`.

## Key files / paths

- `src/process_image.py` — resize / threshold / morphology / Canny / Hough constants (top of file); Canny and Hough values are passed down as arguments
- `src/contours.py` — blur + contour-filtering constants
- `src/hough_lines.py` — line-classification and annotation-drawing constants
- `src/plot.py` — diagnostic-grid layout constants
- `src/random_color.py` — annotation color range
- `src/logging_config.py` — log location, format, rotation
- `src/folder_loop.py` — input/output folder paths

## How it works

Measurement-affecting (changing these changes contact-length results):

- `RESIZE_WIDTH = 1080` (`process_image`) — every image is resized to this width (height proportional, `INTER_LINEAR`) before anything else; all pixel thresholds below assume this scale.
- `OTSU_MAX_VALUE = 255` (`process_image`) — `cv2.threshold(image, 0, OTSU_MAX_VALUE, THRESH_BINARY | THRESH_OTSU)`. Otsu picks the cutoff (the `0` is ignored); this is the foreground value.
- `MORPH_CLOSE_KERNEL_SIZE = (4, 4)`, `MORPH_CLOSE_ITERATIONS = 10` (`process_image`) — closes holes/speckles inside the bright mask.
- `DILATION_KERNEL_SIZE = (3, 3)`, `DILATION_ITERATIONS = 8` (`process_image`) — grows the mask to seal gaps before contour extraction.
- `CANNY_THRESHOLD_1 = 100`, `CANNY_THRESHOLD_2 = 200`, `CANNY_APERTURE_SIZE = 3` (`process_image`) — passed to `contours.get_contours` → `cv2.Canny` (aperture by keyword `apertureSize=`; before that fix it was passed as the `edges` argument and had no effect).
- `CONTOUR_BLUR_KERNEL_SIZE = (9, 9)`, `CONTOUR_BLUR_SIGMA = 1` (`contours`) — Gaussian blur before Canny.
- `MIN_CONTOUR_ARC_LENGTH = 500` (`contours`) — contours with arc length ≤ this (px) are discarded as noise.
- `HOUGH_VOTES_THRESHOLD = 90`, `HOUGH_MIN_LINE_LENGTH = 90`, `HOUGH_MAX_LINE_GAP = 80` (`process_image`) — passed to `measure_contact_length` → `cv2.HoughLinesP` (as `votes_valid_line`, `min_line_length`, `max_line_gap`).
- `ANGLE_SIMILARITY_THRESHOLD_DEGREES = 4.5` (`hough_lines`) — lines within this angle of a kept line are duplicates (see [[line_detection_and_measurement]]).
- `VERTICAL_LINE_MAX_DX = 4`, `HORIZONTAL_LINE_MAX_DY = 10` (`hough_lines`) — how straight a line must be to count as vertical/horizontal.
- Inline literals, not named constants: contour draw thickness `2` (`contours`); Hough pre-blur `(3, 3)`, sigma `1`, `rho = 1`, `theta = np.pi / 180` (`hough_lines.detect_hough_lines`); the vertical-line position thresholds `shape[0] / 2`, `shape[1] / 2`.

Output-appearance only (don't affect the measurement):

- `LINE_THICKNESS = 3`, `MARKER_RADIUS = 10`, `MARKER_THICKNESS = 2`, `FONT_SCALE = 1.2`, `FONT_THICKNESS = 3` (`hough_lines`) — result-image annotations. `HOUGH_PLOT_LINE_COLOR = (0, 0, 255)` (red, BGR) (`hough_lines`) — raw Hough lines on the plot's `HOUGH LINES` panel.
- `MIN_CHANNEL_VALUE = 120`, `MAX_CHANNEL_VALUE = 255` (`random_color`) — per-channel range of random annotation colors (kept bright).
- `GRID_ROWS = 2`, `GRID_COLS = 3`, `CELL_CONTENT_WIDTH = 380`, `CELL_CONTENT_HEIGHT = 300`, `CELL_TITLE_HEIGHT = 28`, `SUPTITLE_HEIGHT = 40`, `MARGIN = 6`, `IMAGE_BORDER_COLOR = (0, 0, 0)` / `IMAGE_BORDER_THICKNESS = 1` (thin black frame around each panel's image), plus background/title colors and font sizes (`plot`) — diagnostic grid layout.
- `LOG_DIR` (`<repo>/Logs`), `LOG_FORMAT`, `LOG_MAX_BYTES = 10 MB`, `LOG_BACKUP_COUNT = 5` (`logging_config`).
- `INPUT_DATASET_FOLDER`, `OUTPUT_HOUGH_RESULTS_FOLDER`, `OUTPUT_PLOT_RESULTS_FOLDER` (`folder_loop`) — `pathlib.Path`s under `PROJECT_ROOT` (`src/`'s parent).

## Gotchas / conventions

- All measurement-affecting values were tuned empirically against the one dataset in `Input/Complete_Dataset/` (fixed camera position, lighting, resolution). None are configurable at runtime; a different setup would likely need most re-tuned, not just `RESIZE_WIDTH`. See [[known_gaps]].
- The plot panel titles `MORPH CLOSING: 4x4` / `DILATION: 3x3` are hardcoded strings in `plot.py`, not derived from the kernel constants — they go stale if the kernels change.
- Constants are named, `UPPER_CASE`, and grouped at the top of each file so they can be found without reading function bodies — keep new tunables there, not as inline literals.
