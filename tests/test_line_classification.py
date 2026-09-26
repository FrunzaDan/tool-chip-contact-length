import numpy as np

from hough_lines import (
    HORIZONTAL_LINE_MAX_DY,
    VERTICAL_LINE_MAX_DX,
    get_horizontal_line_y_index,
    get_vertical_line_y_index,
)


def _blank_image(height: int = 100, width: int = 100) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_get_horizontal_line_y_index_returns_lower_y_of_matching_line():
    image = _blank_image()
    # Nearly-horizontal line (dy well under the threshold).
    cleaned_lines = np.array([[10, 40, 90, 45]], dtype=np.int32)

    result = get_horizontal_line_y_index(cleaned_lines, image)

    assert result is not None
    y_index, annotated_image = result
    assert y_index == 45  # the larger (lower on screen) of y1/y2
    assert annotated_image is image  # drawing mutates the same array in place


def test_get_horizontal_line_y_index_skips_lines_that_are_too_steep():
    image = _blank_image()
    # dy is exactly at the exclusive threshold, so it must be rejected.
    cleaned_lines = np.array([[10, 0, 90, HORIZONTAL_LINE_MAX_DY]], dtype=np.int32)

    result = get_horizontal_line_y_index(cleaned_lines, image)

    assert result is None


def test_get_vertical_line_y_index_returns_lower_y_of_matching_line():
    image = _blank_image(height=100, width=100)
    contour_image = _blank_image(height=100, width=100)
    # half_height = 50, half_width = 50.
    # A vertical-ish line (dx under VERTICAL_LINE_MAX_DX) positioned past both
    # thresholds, per the (empirically tuned) criterion in get_vertical_line_y_index.
    cleaned_lines = np.array([[70, 20, 71, 90]], dtype=np.int32)

    result = get_vertical_line_y_index(cleaned_lines, contour_image, image)

    assert result is not None
    y_index, annotated_image = result
    assert y_index == 90
    assert annotated_image is image


def test_get_vertical_line_y_index_skips_lines_that_are_too_slanted():
    image = _blank_image(height=100, width=100)
    contour_image = _blank_image(height=100, width=100)
    # dx is at the exclusive threshold, so this must be rejected even though
    # it satisfies the position thresholds.
    cleaned_lines = np.array([[70, 20, 70 + VERTICAL_LINE_MAX_DX, 90]], dtype=np.int32)

    result = get_vertical_line_y_index(cleaned_lines, contour_image, image)

    assert result is None


def test_get_vertical_line_y_index_returns_none_when_no_lines_given():
    image = _blank_image()
    contour_image = _blank_image()
    cleaned_lines = np.empty((0, 4), dtype=np.int32)

    result = get_vertical_line_y_index(cleaned_lines, contour_image, image)

    assert result is None
