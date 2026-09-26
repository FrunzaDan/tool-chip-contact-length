# Line Detection & Contact-Length Measurement

## What it is

How the contour image is turned into Hough line segments, filtered down to one horizontal and one vertical line, and turned into a single pixel contact-length measurement.

## Key files / paths

- `src/hough_lines.py` — all of the logic described here
- `src/random_color.py` — `random_line_color()`, a random bright BGR color per annotation
- `src/process_image.py` — step 9 calls `measure_contact_length(contour_image, cropped_image, HOUGH_VOTES_THRESHOLD, HOUGH_MIN_LINE_LENGTH, HOUGH_MAX_LINE_GAP, image_name)` (see [[pipeline_parameters]])
- `tests/test_clean_lines.py`, `tests/test_line_classification.py`, `tests/test_measure_contact_length.py` — unit tests for this module

## How it works

- `measure_contact_length(contour_image, original_image, votes_valid_line, min_line_length, max_line_gap, image_name)` — orchestrator. Always returns `hough_image_plot`, a black 3-channel image of every raw Hough line, which becomes the diagnostic plot's last panel (even when no measurement is made).
- `detect_hough_lines` — `GaussianBlur((3,3), sigma 1)` on the single-channel contour image, then `cv2.HoughLinesP(rho=1, theta=1°, threshold=votes_valid_line, minLineLength, maxLineGap)`. Draws each raw line in red (`HOUGH_PLOT_LINE_COLOR`, BGR `(0, 0, 255)`, thickness 3) onto `hough_image_plot`. Returns the `(N, 1, 4)` int32 array, or `None` when nothing is found (`HoughLinesP` returns `None`, not `[]`) — the caller then logs a warning and skips measurement.
- `clean_lines` — collapses near-duplicate segments. Each line's angle is `degrees(atan2(dx, dy))`; if it's within `ANGLE_SIMILARITY_THRESHOLD_DEGREES` (4.5°) of an already-kept angle it's dropped. Returns an `(M, 4)` int32 array (`(0, 4)` when empty). Order-dependent (first line at a given angle wins), position-unaware.
- `get_horizontal_line_y_index(cleaned_lines, image)` — first line with `|y1 - y2| < HORIZONTAL_LINE_MAX_DY` (10px): the chip/workpiece top edge. Returns `(lowest_y, image)` or `None`. When `y1 == y2` both endpoints get a label.
- `get_vertical_line_y_index(cleaned_lines, contour_image, image)` — first line with `|x1 - x2| < VERTICAL_LINE_MAX_DX` (4px) that also passes the `half_height`/`half_width` position test (see Gotchas): the tool's contact edge. Returns `(lowest_y, image)` or `None`.
- Horizontal is searched first, then vertical. If either returns `None`, a warning is logged and nothing is saved.
- `contact_length = y_point_of_horizontal - y_point_of_vertical`. If `<= 0`, a "result is suspect" warning is logged, but the result image is **still saved** — the value isn't rejected.
- `save_result_image(image_name, annotated_image, contact_length)` — writes the `Dist = <n>px + t` text (random color, at (100, 100)) and saves to `Output/folder_hough_results/<image_name>`. `cv2.imwrite` failure is logged as an error, not raised.
- `cv2.error` raised during classification/saving is caught and logged as a warning ("Not computable!").

## Gotchas / conventions

- **Mutation:** the line, circle marker, and `Y1`/`Y2` label are drawn directly onto the caller's `original_image` (which is `process_image`'s `cropped_image`) as a side effect of finding each line. If only one line is found, the annotations are drawn but never saved.
- **Directed angle in `clean_lines` is deliberate:** `atan2` gives a directed angle over (-180°, 180°], so a segment and its reverse count as different. Normalizing to an undirected angle (mod 180) was tested and dropped 34 of 314 successful measurements on the real dataset — because dedup ignores position, the directed angle is what lets a second parallel edge (often the one the vertical search needs) survive. A real fix needs position-aware dedup. Tracked in [[known_gaps]].
- **Vertical position thresholds are dimensionally odd on purpose:** `half_height = contour_image.shape[0] / 2` is compared against x-coordinates, and `half_width = shape[1] / 2` against `y1` or `x2`. Swapping to the "correct" pairing rejects the real tool edge and regresses detection. Treat as empirically tuned; re-validate against the dataset before changing. Tracked in [[known_gaps]].
- **First match, not best match:** both classifiers return the first qualifying line in `cleaned_lines`, whose order follows Hough output, not position.
- **`+ t` in the annotation is intentional, not a bug.** `t` is the cutting depth between the tool and the material — a constant that isn't visible in the image and so can't be computed by the OpenCV processing. The measured value is therefore only the image-visible part of the contact length, and the full contact length is `<n>px + t`, with `t` added outside this program. Don't remove it or try to substitute a value in code.
- Even without a measurement, the 6-panel diagnostic plot is still produced, so failed frames are visible in `Output/folder_plot_results/`.
- Annotation colors come from `random_color.random_line_color()`, so they differ between runs of the same image.
- Drawing constants (`LINE_THICKNESS`, `MARKER_RADIUS`, `MARKER_THICKNESS`, `FONT_SCALE`, `FONT_THICKNESS`) are at the top of the file; label offsets (e.g. `-150, +40` for the vertical label) are inline literals.
