# Pipeline Tunable Parameters

## What it is

Every magic-number knob that controls how an image is processed, gathered in one place with what it affects and which file owns it — the pipeline steps themselves are documented in `index.md`, but the actual tuning constants live scattered across three files.

## Key files / paths

- `src/process_image.py` — resize/threshold/morphology constants, top of file
- `src/contours.py` — blur + contour-filtering constants
- `src/hough_lines.py` — Hough + line-classification constants

## How it works

- `RESIZE_WIDTH = 1080` — every image is resized to this width (height scaled proportionally) before anything else, so all the pixel-based thresholds below assume this scale.
- `OTSU_MAX_VALUE = 255` — passed to `cv2.threshold(image, 0, OTSU_MAX_VALUE, THRESH_BINARY | THRESH_OTSU)`; OTSU picks the actual cutoff (the `0` threshold argument is ignored), this is the value given to foreground pixels.
- `MORPH_CLOSE_KERNEL_SIZE = (4,4)`, `MORPH_CLOSE_ITERATIONS = 10` — closes small holes/speckles inside the bright mask.
- `DILATION_KERNEL_SIZE = (3,3)`, `DILATION_ITERATIONS = 8` — grows the mask further to seal remaining gaps before contour extraction.
- `CONTOUR_BLUR_KERNEL_SIZE = (9,9)`, `CONTOUR_BLUR_SIGMA = 1` — Gaussian blur applied before Canny, in `contours.py`.
- `CANNY_THRESHOLD_1/2 = 100, 200`, `CANNY_APERTURE_SIZE = 3` — passed to `cv2.Canny`.
- `MIN_CONTOUR_ARC_LENGTH = 500` — contours shorter than this (px) are discarded as noise.
- `HOUGH_VOTES_THRESHOLD = 90`, `HOUGH_MIN_LINE_LENGTH = 90`, `HOUGH_MAX_LINE_GAP = 80` — passed to `cv2.HoughLinesP`.
- `ANGLE_SIMILARITY_THRESHOLD_DEGREES = 4.5` — lines within this angle of each other are treated as duplicates (see [[line_detection_and_measurement]]).
- `VERTICAL_LINE_MAX_DX = 4`, `HORIZONTAL_LINE_MAX_DY = 10` — how "straight" a line must be to count as vertical/horizontal.

## Gotchas / conventions

- All of these were tuned empirically against the one dataset in `Input/Complete_Dataset/` (fixed camera position, lighting, and resolution). None are derived/configurable at runtime — a different camera setup or frame size would likely need most of these re-tuned, not just `RESIZE_WIDTH`. See [[known_gaps]].
- Constants are named and grouped at the top of each file specifically so they can be found without reading the function bodies — keep new tunables there, not as inline literals.
