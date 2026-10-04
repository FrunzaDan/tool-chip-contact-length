"""Hough line detection, line classification, and contact-length measurement."""

import logging
import math
from typing import cast

import cv2
import numpy as np
import numpy.typing as npt

import folder_loop
import random_color

logger = logging.getLogger(__name__)

# Line-classification thresholds.
ANGLE_SIMILARITY_THRESHOLD_DEGREES = 4.5
VERTICAL_LINE_MAX_DX = 4
HORIZONTAL_LINE_MAX_DY = 10

# Annotation drawing constants.
LINE_THICKNESS = 3
MARKER_RADIUS = 10
MARKER_THICKNESS = 2
FONT_SCALE = 1.2
FONT_THICKNESS = 3

# Color (BGR) of the raw Hough lines on the diagnostic plot's last panel.
HOUGH_PLOT_LINE_COLOR = (0, 0, 255)  # red


def measure_contact_length(
    contour_image: npt.NDArray[np.uint8],
    original_image: npt.NDArray[np.uint8],
    votes_valid_line: int,
    min_line_length: int,
    max_line_gap: int,
    image_name: str,
) -> npt.NDArray[np.uint8]:
    """Measure the tool-chip contact length and save the annotated result.

    Detects the tool's vertical edge and the chip's horizontal edge in
    contour_image, and saves original_image annotated with the contact length
    (the vertical distance between them).

    Returns a 3-channel image of all the raw Hough lines, for the diagnostic plot.
    """
    # NOTE: this function draws directly onto (mutates) `original_image` as
    # part of computing the contact length - it is not treated as read-only.
    hough_image_plot: npt.NDArray[np.uint8] = np.zeros(
        (contour_image.shape[0], contour_image.shape[1], 3), np.uint8
    )

    hough_lines: npt.NDArray[np.int32] | None = detect_hough_lines(
        contour_image,
        votes_valid_line,
        min_line_length,
        max_line_gap,
        hough_image_plot,
    )
    if hough_lines is None:
        logger.warning(
            "No Hough lines detected for %s; skipping contact-length calculation.",
            image_name,
        )
        return hough_image_plot

    cleaned_lines: npt.NDArray[np.int32] = clean_lines(hough_lines)

    # calculate the tool-chip contact length (difference between the 2 lines):
    try:
        horizontal_result: tuple[int, npt.NDArray[np.uint8]] | None = (
            get_horizontal_line_y_index(cleaned_lines, original_image)
        )
        vertical_result: tuple[int, npt.NDArray[np.uint8]] | None = (
            get_vertical_line_y_index(cleaned_lines, contour_image, original_image)
        )
        if horizontal_result is None:
            logger.warning("Y Points not found on horizontal line!")
        elif vertical_result is None:
            logger.warning("Y Points not found on vertical line!")
        else:
            # Both results reference the same (mutated) `original_image`, so
            # either one already carries both annotations.
            y_point_of_horizontal, annotated_image = horizontal_result
            y_point_of_vertical, _ = vertical_result

            contact_length: int = y_point_of_horizontal - y_point_of_vertical

            if contact_length <= 0:
                logger.warning(
                    "%s: computed contact length is non-positive (%dpx) - likely "
                    "horizontal/vertical line misclassification, result is suspect.",
                    image_name,
                    contact_length,
                )

            save_result_image(image_name, annotated_image, contact_length)

    except cv2.error as error:
        logger.warning("Not computable! OpenCV error: %s", error)

    return hough_image_plot


def detect_hough_lines(
    contour_image: npt.NDArray[np.uint8],
    votes_valid_line: int,
    min_line_length: int,
    max_line_gap: int,
    hough_image_plot: npt.NDArray[np.uint8],
) -> npt.NDArray[np.int32] | None:
    """Detect line segments on a single-channel edge image.

    Each detected line is also drawn onto hough_image_plot. Returns
    cv2.HoughLinesP's (N, 1, 4) int32 array, or None if nothing is found.
    """
    blurred_contour_image = cv2.GaussianBlur(contour_image, (3, 3), 1)
    hough_lines = cast(
        npt.NDArray[np.int32] | None,
        cv2.HoughLinesP(
            blurred_contour_image,
            1,
            np.pi / 180,
            votes_valid_line,
            None,
            min_line_length,
            max_line_gap,
        ),
    )
    # cv2.HoughLinesP returns None (not an empty array) when no lines are found.
    if hough_lines is None:
        return None
    for hough_line in hough_lines:
        x1, y1, x2, y2 = hough_line[0]
        cv2.line(hough_image_plot, (x1, y1), (x2, y2), HOUGH_PLOT_LINE_COLOR, 3)
    return hough_lines


def clean_lines(hough_lines: npt.NDArray[np.int32]) -> npt.NDArray[np.int32]:
    """Collapse near-duplicate Hough line segments, keeping one line per distinct angle.

    Takes cv2.HoughLinesP's (N, 1, 4) array and returns an (M, 4) array.

    NOTE: the angle is *directed* (atan2 over (-180, 180]), so a segment and
    its reverse count as different angles. That looks like a bug, since
    lines are undirected, but it was tested against the real dataset:
    normalizing to an undirected orientation (mod 180) dropped 34 of 314
    successful measurements. Deduplication here ignores position, so the
    directed angle is what lets a second parallel edge survive - often the
    one get_vertical_line_y_index needs. A proper fix would make the
    deduplication position-aware; until then the directed angle is kept.
    """
    cleaned_lines: list[tuple[int, int, int, int]] = []
    cleaned_angles: list[float] = []
    for hough_line in hough_lines:
        x1, y1, x2, y2 = (int(v) for v in hough_line[0])
        angle = math.degrees(math.atan2(x2 - x1, y2 - y1))
        is_duplicate_angle = any(
            abs(angle - kept_angle) <= ANGLE_SIMILARITY_THRESHOLD_DEGREES
            for kept_angle in cleaned_angles
        )
        if not is_duplicate_angle:
            cleaned_lines.append((x1, y1, x2, y2))
            cleaned_angles.append(angle)

    if not cleaned_lines:
        return np.empty((0, 4), dtype=np.int32)
    return np.array(cleaned_lines, dtype=np.int32)


def _draw_point_label(
    image: npt.NDArray[np.uint8],
    marker_point: tuple[int, int],
    text_point: tuple[int, int],
    label: str,
    value: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a circle marker at marker_point, labeled with its value at text_point.

    The two points can differ (see callers). Mutates image in place.
    """
    cv2.putText(
        image,
        f"{label}: {value}",
        text_point,
        cv2.FONT_HERSHEY_SIMPLEX,
        FONT_SCALE,
        color,
        FONT_THICKNESS,
        cv2.LINE_AA,
    )
    cv2.circle(
        image,
        marker_point,
        MARKER_RADIUS,
        color,
        thickness=MARKER_THICKNESS,
        lineType=cv2.LINE_8,
        shift=0,
    )


def get_vertical_line_y_index(
    cleaned_lines: npt.NDArray[np.int32],
    contour_image: npt.NDArray[np.uint8],
    image: npt.NDArray[np.uint8],
) -> tuple[int, npt.NDArray[np.uint8]] | None:
    """Find, draw, and return the lowest y of the tool's (vertical) edge.

    Takes the first near-vertical line in the expected region, draws it on
    image, and returns the y of its lowest endpoint together with image.
    Returns None if no line qualifies.
    """
    color: tuple[int, int, int] = random_color.random_line_color()

    # NOTE: half_height is compared against x-coordinates and half_width
    # against y/x-coordinates - this looks like a height/width mix-up at a
    # glance. It was tested against the real dataset: "fixing" it to the
    # dimensionally "correct" pairing rejects the actual tool edge (which sits
    # in the upper portion of the cropped frame) and regresses detection. Left
    # as the original, empirically working thresholds.
    half_height = contour_image.shape[0] / 2
    half_width = contour_image.shape[1] / 2

    for line in cleaned_lines:
        x1, y1, x2, y2 = (int(v) for v in line)
        is_vertical = abs(x1 - x2) < VERTICAL_LINE_MAX_DX
        meets_position_thresholds = ((x1 > half_height) or (x2 > half_height)) and (
            (y1 > half_width) or (x2 > half_width)
        )
        if not (is_vertical and meets_position_thresholds):
            continue

        # The connecting line is the same regardless of which endpoint is lowest.
        cv2.line(image, (x1, y1), (x2, y2), color, LINE_THICKNESS)

        # choose only the lowest y point of the line:
        if y2 > y1:
            _draw_point_label(image, (x2, y2), (x2 - 150, y2 + 40), "Y2", y2, color)
            return y2, image
        _draw_point_label(image, (x1, y1), (x1 - 150, y1 + 40), "Y1", y1, color)
        return y1, image

    return None


def get_horizontal_line_y_index(
    cleaned_lines: npt.NDArray[np.int32], image: npt.NDArray[np.uint8]
) -> tuple[int, npt.NDArray[np.uint8]] | None:
    """Find, draw, and return the lowest y of the chip's (horizontal) edge.

    Takes the first near-horizontal line, draws it on image, and returns the
    y of its lowest endpoint together with image. Returns None if no line
    qualifies.
    """
    color: tuple[int, int, int] = random_color.random_line_color()

    for line in cleaned_lines:
        x1, y1, x2, y2 = (int(v) for v in line)
        if abs(y1 - y2) >= HORIZONTAL_LINE_MAX_DY:
            continue

        # The connecting line is the same regardless of which endpoint(s) are lowest.
        cv2.line(image, (x1, y1), (x2, y2), color, LINE_THICKNESS)

        # choose only the lowest y point of the line (both, if they're equal):
        if y2 > y1:
            _draw_point_label(image, (x2, y2), (x2 - 20, y1 - 30), "Y2", y2, color)
            return y2, image
        if y2 == y1:
            _draw_point_label(image, (x2, y2), (x2 - 20, y1 - 30), "Y2", y2, color)
            _draw_point_label(image, (x1, y1), (x1 + 20, y1 - 30), "Y1", y1, color)
            return y1, image
        _draw_point_label(image, (x1, y1), (x1 + 20, y1 - 30), "Y1", y1, color)
        return y1, image

    return None


def save_result_image(
    image_name: str,
    annotated_image: npt.NDArray[np.uint8],
    contact_length: int,
) -> None:
    """Write the contact length onto annotated_image and save it as image_name."""
    output_path = folder_loop.OUTPUT_HOUGH_RESULTS_FOLDER / image_name

    text_color = random_color.random_line_color()
    # "+ t" is intentional: t is the cutting depth between the tool and the
    # material, a constant that can't be measured from the image, so the
    # measured pixel length is reported as "<n>px + t".
    text = f"Dist = {contact_length}px + t"

    cv2.putText(
        annotated_image,
        text,
        (100, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        FONT_SCALE,
        text_color,
        FONT_THICKNESS,
        cv2.LINE_AA,
    )

    success = cv2.imwrite(str(output_path), annotated_image)

    if success:
        logger.info("Saved hough image: %s", output_path)
    else:
        logger.error("Failed to save image: %s", output_path)
