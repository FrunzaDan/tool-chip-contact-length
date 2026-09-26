# Known Gaps

Things known to be incomplete, fragile, or empirically-hacky, kept here so future work has a starting list instead of rediscovering them by reading code.

## Contact-length annotation text has a stray literal

`src/hough_lines.py`, `save_result_image` — the text is `f"Dist = {contact_length}px + t"`. The trailing `+ t` is literal text, so every result image reads e.g. `Dist = 42px + t`. Looks like a leftover debug artifact.

## Vertical-line position thresholds are dimensionally inconsistent

`src/hough_lines.py`, `get_vertical_line_y_index` — `half_height` is compared against x-coordinates, and `half_width` against a mix of `y1` and `x2`. The in-code NOTE says this was tested: the dimensionally "correct" pairing rejects the real tool edge and regresses detection. It works, but the geometric criterion it encodes has never been re-derived — worth replacing with a principled (e.g. bounding-box based) position filter. See [[line_detection_and_measurement]].

## Line de-duplication is position-unaware and uses a directed angle

`src/hough_lines.py`, `clean_lines` — duplicates are decided by angle alone, first-seen wins, and the angle is directed (a segment and its reverse differ). Normalizing the angle (mod 180) looks like the obvious fix but dropped 34 of 314 measurements on the real dataset, because the directed angle is what currently lets a second parallel edge survive. A proper fix needs position-aware dedup (angle + offset). Related: both line classifiers take the *first* qualifying line, not the best one.

## Non-positive contact lengths are only flagged, not rejected

`src/hough_lines.py`, `measure_contact_length` — a result `<= 0` logs a "result is suspect" warning, but the annotated image is still saved as a normal result. There's no aggregate output (CSV etc.) of measurements either; values exist only as text on result images and in log lines.

## Uppercase `.BMP` files are skipped

`src/folder_loop.py`, `process_folder` — the check is `image_name.endswith(".bmp")` (case-sensitive), so `frame.BMP` is logged as "Skipping non-BMP image". `run.sh`'s summary counts inputs with `-iname "*.bmp"` (case-insensitive), so the two disagree on such files.

## Some failures are swallowed rather than reported as step failures

`src/contours.py`, `get_contours` — a `cv2.error` in the blur or Canny call is logged and a blank image is returned, so the pipeline continues and the Hough step then simply finds no lines. `process_image._run_step` logs step errors with `logger.error` (message only, no traceback); only `folder_loop` / `main` use `logger.exception`.

## Import-time side effects and module coupling

Importing `folder_loop` creates the two `Output/` folders (`os.makedirs` at module level). `hough_lines` and `plot` import `folder_loop` only to read its output-folder constants, so importing either one (e.g. in tests) triggers that too, and there's an import cycle-in-waiting (`folder_loop` → `process_image` → `hough_lines` → `folder_loop`) that only works because the constants are read at call time.

## Log lines don't show which module emitted them

Every module logs through `logging.getLogger(__name__)`, but `LOG_FORMAT` (`logging_config.py`) is `"%(asctime)s - %(levelname)s - %(message)s"` — no `%(name)s` — so the per-module logger names aren't visible in the output.

## Automated tests cover unit logic only, not the full pipeline

`tests/` (23 pytest tests, run via `python3 -m pytest`, config in `pyproject.toml`) covers: `clean_lines` and the two line classifiers; `measure_contact_length`'s arithmetic, suspect-length warning, and no-lines path (with internals monkeypatched); `get_contours`; the `process_image` step helpers and `_run_step`; and `random_line_color`. Not covered: `detect_hough_lines`, `save_result_image`, `plot.py`, `logging_config.py`, `folder_loop.process_folder`, `main.py`, or any end-to-end run on a real/fixture image. No CI runs the suite. A regression from a parameter change (see [[pipeline_parameters]]) is still caught only by a full-dataset run and comparing results.

## Pipeline parameters are tuned to one dataset/camera setup

Every threshold in [[pipeline_parameters]] (resize width, morphology kernels, Canny/Hough thresholds, angle/position tolerances) was tuned against the single dataset in `Input/Complete_Dataset/`. Nothing is derived from the image itself (e.g. relative to detected object size), so a different camera, lens, or lighting would likely need hand re-tuning, with no documented process for how the current values were chosen.

## No CLI arguments or config file

Input/output folder paths are hardcoded relative to `src/` in `folder_loop.py`. Running against a different dataset means replacing the contents of `Input/Complete_Dataset/` or editing source — no `--input`/`--output` flag or config file. Processing is also strictly sequential (one image at a time, single process).

## Cosmetic leftovers

- `plot.py`'s fifth panel is titled `CANNY` though it shows the filtered-contour image (kept to match `Documentation/Images/Canny.png`); its first panel, `Original`, is the resized full frame, not the cropped half used for measurement.
- `process_image._run_step` has no type hints (its `func`/return type would need a `Callable`/`TypeVar` signature).

## `ai_docs/` scaffold is partially set up

`ai_docs/learning_approach.md` describes a workflow that also expects `todo.md` and `glossary.md` — neither exists yet, so that part of the protocol isn't followable.
