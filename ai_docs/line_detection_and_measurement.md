# Line Detection & Contact-Length Measurement

## What it is

How the contour image is turned into Hough line segments, filtered down to one horizontal and one vertical line, and turned into a single pixel contact-length measurement.

## Key files / paths

- `src/hough_lines.py` — all of the logic described here
- `src/random_color.py` — `random_line_color()`, used to pick a distinct color per annotation
- `src/process_image.py` — calls `measure_contact_length` with the tunable Hough parameters (see [[pipeline_parameters]])

## How it works

- `detect_hough_lines` blurs (3x3) the single-channel contour image, then runs `cv2.HoughLinesP`. Returns `None` (not `[]`) when no lines are found at all — checked explicitly by the caller.
- `clean_lines` collapses near-duplicate segments: each line's angle (`atan2(dx, dy)`, degrees) is compared against every already-kept line; if within `ANGLE_SIMILARITY_THRESHOLD_DEGREES` (4.5°) of a kept line it's dropped as a duplicate, otherwise kept. This is order-dependent (first line seen at a given angle wins) rather than a proper clustering.
- `get_horizontal_line_y_index` scans the cleaned lines for one with `|y1 - y2| < HORIZONTAL_LINE_MAX_DY` (10px) — the visible top edge of the workpiece/chip. Returns the line's lowest point (largest y).
- `get_vertical_line_y_index` scans for one with `|x1 - x2| < VERTICAL_LINE_MAX_DX` (4px) AND positioned past `half_height`/`half_width` (see Gotchas) — the tool's contact edge. Returns the line's lowest point.
- Both classification functions return on the *first* matching line, not the best match — the order of `cleaned_lines` (which follows Hough/contour order, not position) decides which candidate wins if more than one line satisfies the angle test.
- `contact_length = y_point_of_horizontal - y_point_of_vertical`. No sign/sanity check — a malformed frame that matches the "wrong" lines can silently produce a negative or nonsensical value.
- Annotations (connecting line, circle marker, `Y1`/`Y2` label) are drawn directly onto the caller's `original_image` (a mutation, not a copy) as a side effect of finding each line.
- `save_result_image` adds the final `Dist = <n>px` text and writes to `Output/folder_hough_results/<image_name>`.

## Gotchas / conventions

- `get_vertical_line_y_index`'s position thresholds are dimensionally odd on purpose: `half_height = contour_image.shape[0] / 2` is compared against x-coordinates, and `half_width = shape[1] / 2` is compared against a mix of `y1` and `x2`. This was tested deliberately against the real dataset — swapping to the dimensionally "correct" `shape[1]`/`shape[0]` pairing rejects the actual tool edge and regresses detection. Treat as empirically-tuned, not a typo to fix without re-validating against the dataset. Tracked in [[known_gaps]].
- If either line isn't found, a warning is logged and no result image is saved for that frame — but the 6-panel diagnostic plot (`plot.py`) is still produced, so a missing measurement is still visible in `Output/folder_plot_results/` even without a hough result image.
- Colors are random per line/run (`random_color.random_line_color()`) — annotation colors are not stable across runs of the same image.
