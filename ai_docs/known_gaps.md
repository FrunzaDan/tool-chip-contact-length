# Known Gaps

Things known to be incomplete, fragile, or empirically-hacky, kept here so future work has a starting list instead of rediscovering them by reading code.

## Contact-length annotation text has a stray literal

`src/hough_lines.py`, `save_result_image` — the annotation text is built as `f"Dist = {contact_length}px + t"`. The trailing `+ t` is not a variable, it's literal text baked into the f-string, so every result image is annotated e.g. `Dist = 42px + t` instead of `Dist = 42px`. Looks like a leftover debug artifact rather than intended output.

## Vertical-line position thresholds are dimensionally inconsistent

`src/hough_lines.py`, `get_vertical_line_y_index` — `half_height` is compared against x-coordinates, and `half_width` is compared against a mix of `y1` and `x2` (not a consistent `y1`/`y2` pair). The in-code comment says this was tested deliberately: swapping to the dimensionally "correct" pairing rejects the real tool edge and regresses detection on the actual dataset. It works, but the geometric criterion it's actually encoding has never been re-derived — worth revisiting with a principled position filter (e.g. bounding-box based) rather than reusing a magic pair of `shape[0]/2`, `shape[1]/2` thresholds. See [[line_detection_and_measurement]].

## Automated tests cover unit logic only, not the full pipeline

`tests/` (pytest, run via `python3 -m pytest`, config in `pyproject.toml`) covers the pure/deterministic pieces: line classification and cleanup in `hough_lines.py`, contour extraction in `contours.py`, the per-step helpers and `_run_step` in `process_image.py`, and `random_color.random_line_color`. There's still no test that exercises `folder_loop.process_folder` or `main.py` end-to-end against a real (or fixture) image, and no CI wiring to run the suite automatically — a pipeline regression from a parameter change (see [[pipeline_parameters]]) can still only be caught by eyeballing `Output/folder_plot_results/` for a full dataset run, or by extending the unit tests to the case in question.

## Pipeline parameters are tuned to one dataset/camera setup

Every threshold in [[pipeline_parameters]] (resize width, OTSU range, morphology kernels, Hough thresholds, angle/position tolerances) was tuned against the single dataset in `Input/Complete_Dataset/`. Nothing is measured or derived from the image itself (e.g. relative to detected object size), so a different camera, lens, or lighting setup would likely require re-tuning most of these by hand, with no documented process for how the current values were chosen.

## No CLI arguments or config file

Input/output folder paths (`Input/Complete_Dataset/`, `Output/folder_hough_results/`, `Output/folder_plot_results/`) are hardcoded relative to `src/` in `folder_loop.py`. Running against a different dataset means either replacing the contents of `Input/Complete_Dataset/` or editing source — there's no `--input`/`--output` flag or config file.

## `ai_docs/` scaffold is partially set up

`ai_docs/learning_approach.md` describes a workflow that also expects `todo.md` and `glossary.md` to track documented-vs-pending concepts and terminology — neither file exists yet, so that part of the protocol isn't actually followable yet.
