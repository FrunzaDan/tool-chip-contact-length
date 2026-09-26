"""Per-image pipeline: preprocessing, contact-length measurement, and plot."""

import enum
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Literal, ParamSpec, TypeVar, cast

import cv2
import numpy as np
import numpy.typing as npt

import contours
import hough_lines
import plot

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Tunable pipeline parameters, named so they can all be found/adjusted in one
# place instead of as bare literals scattered through the function below.
RESIZE_WIDTH = 1080

# With cv2.THRESH_OTSU the threshold is computed automatically (the value
# passed in is ignored); this is the value given to pixels above it.
OTSU_MAX_VALUE = 255

MORPH_CLOSE_KERNEL_SIZE = (4, 4)
MORPH_CLOSE_ITERATIONS = 10

DILATION_KERNEL_SIZE = (3, 3)
DILATION_ITERATIONS = 8

CANNY_THRESHOLD_1 = 100
CANNY_THRESHOLD_2 = 200
CANNY_APERTURE_SIZE = 3

HOUGH_VOTES_THRESHOLD = 90
HOUGH_MIN_LINE_LENGTH = 90
HOUGH_MAX_LINE_GAP = 80


class _StepFailed(enum.Enum):
    """Type of the _STEP_FAILED sentinel (an Enum, so type checkers can narrow it)."""

    STEP_FAILED = enum.auto()


# Sentinel distinguishing "the step raised and was already logged" from "the
# step legitimately returned None" (only the plot step does the latter).
_STEP_FAILED = _StepFailed.STEP_FAILED


def _run_step(
    step_name: str,
    image_name: str,
    func: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R | Literal[_StepFailed.STEP_FAILED]:
    """Run one pipeline step, logging and returning _STEP_FAILED on any exception."""
    try:
        return func(*args, **kwargs)
    except Exception:
        logger.exception("%s Error at %s", step_name, image_name)
        return _STEP_FAILED


def _resize_to_fixed_width(image: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Resize image to RESIZE_WIDTH pixels wide, preserving its aspect ratio."""
    target_height = int(image.shape[0] * RESIZE_WIDTH / image.shape[1])
    resized = cv2.resize(
        image, (RESIZE_WIDTH, target_height), interpolation=cv2.INTER_LINEAR
    )
    return cast(npt.NDArray[np.uint8], resized)


def _crop_right_half(image: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Keep only the right half of the frame, where the tool-chip interface is.

    A real copy (not a numpy view) is returned so that later drawing on this
    image (the Hough-line annotations) can never silently mutate `image` itself.
    """
    return image[:, image.shape[1] // 2 :].copy()


def _convert_to_grayscale(image: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Convert a BGR image to single-channel grayscale."""
    return cast(npt.NDArray[np.uint8], cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))


def _apply_otsu_threshold(image: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Binarize image with an automatically chosen (Otsu) global threshold."""
    _, thresholded = cv2.threshold(
        image, 0, OTSU_MAX_VALUE, cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )
    return cast(npt.NDArray[np.uint8], thresholded)


def _apply_morphological_closing(
    image: npt.NDArray[np.uint8],
) -> npt.NDArray[np.uint8]:
    """Close small dark holes/speckles inside the bright regions."""
    kernel = np.ones(MORPH_CLOSE_KERNEL_SIZE, np.uint8)
    closed = cv2.morphologyEx(
        image, cv2.MORPH_CLOSE, kernel, iterations=MORPH_CLOSE_ITERATIONS
    )
    return cast(npt.NDArray[np.uint8], closed)


def _apply_dilation(image: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Grow the bright regions to seal remaining gaps along their edges."""
    kernel = np.ones(DILATION_KERNEL_SIZE, np.uint8)
    dilated = cv2.dilate(image, kernel, iterations=DILATION_ITERATIONS)
    return cast(npt.NDArray[np.uint8], dilated)


def _read_image(image_path: Path) -> npt.NDArray[np.uint8] | None:
    """Load image_path as an 8-bit BGR image, or return None if it can't be read."""
    # cv2.imread does not raise on failure (bad path, corrupt/unsupported file);
    # it returns None, so callers must check for that explicitly.
    image = cv2.imread(str(image_path))
    return cast(npt.NDArray[np.uint8] | None, image)


def process_image(image_path: Path) -> None:
    """Run the full pipeline on one image.

    Preprocesses the image, measures the contact length (saving the annotated
    result), and saves the diagnostic plot. Any step's failure is logged and
    stops processing of this image only.
    """
    image_name = image_path.name

    # Step 1: Read the image
    image = _run_step("Read", image_name, _read_image, image_path)
    if image is _STEP_FAILED:
        return
    if image is None:
        logger.error(
            "Could not read image (missing, corrupt, or unsupported format): %s",
            image_name,
        )
        return

    # Step 2: Resize
    resized_image = _run_step("Resize", image_name, _resize_to_fixed_width, image)
    if resized_image is _STEP_FAILED:
        return

    # Step 3: Crop
    cropped_image = _run_step("Crop", image_name, _crop_right_half, resized_image)
    if cropped_image is _STEP_FAILED:
        return

    # Step 4: Grayscale
    grayscale_image = _run_step(
        "Grayscale", image_name, _convert_to_grayscale, cropped_image
    )
    if grayscale_image is _STEP_FAILED:
        return

    # Step 5: OTSU threshold
    otsu_thresholded_image = _run_step(
        "Otsu", image_name, _apply_otsu_threshold, grayscale_image
    )
    if otsu_thresholded_image is _STEP_FAILED:
        return

    # Step 6: Morphological Closing
    morph_closed_image = _run_step(
        "Morphological Closing",
        image_name,
        _apply_morphological_closing,
        otsu_thresholded_image,
    )
    if morph_closed_image is _STEP_FAILED:
        return

    # Step 7: Dilation
    dilated_image = _run_step(
        "Dilation", image_name, _apply_dilation, morph_closed_image
    )
    if dilated_image is _STEP_FAILED:
        return

    # Step 8: Canny edge detection + contour extraction
    contour_image = _run_step(
        "Contours",
        image_name,
        contours.get_contours,
        dilated_image,
        CANNY_THRESHOLD_1,
        CANNY_THRESHOLD_2,
        CANNY_APERTURE_SIZE,
    )
    if contour_image is _STEP_FAILED:
        return

    # Step 9: Hough Transform + contact-length measurement
    hough_image_plot = _run_step(
        "Hough",
        image_name,
        hough_lines.measure_contact_length,
        contour_image,
        cropped_image,
        HOUGH_VOTES_THRESHOLD,
        HOUGH_MIN_LINE_LENGTH,
        HOUGH_MAX_LINE_GAP,
        image_name,
    )
    if hough_image_plot is _STEP_FAILED:
        return

    # Step 10: Plot
    plot_result = _run_step(
        "Plot",
        image_name,
        plot.save_entire_process_plot,
        resized_image,
        otsu_thresholded_image,
        morph_closed_image,
        dilated_image,
        contour_image,
        hough_image_plot,
        image_name,
    )
    if plot_result is _STEP_FAILED:
        return

    # Final log messages
    logger.info("Finished processing image [%s]", image_name)
    logger.info("--------------------")
