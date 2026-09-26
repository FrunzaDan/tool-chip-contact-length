import numpy as np

from hough_lines import clean_lines


def _as_hough_lines(segments: list[tuple[int, int, int, int]]) -> np.ndarray:
    """Build an array shaped like cv2.HoughLinesP's output: (N, 1, 4)."""
    return np.array([[segment] for segment in segments], dtype=np.int32)


def test_collapses_near_duplicate_angles_to_one_line():
    # Two near-vertical segments (same angle within the similarity threshold)
    # plus one clearly horizontal segment.
    hough_lines = _as_hough_lines(
        [
            (10, 0, 10, 100),
            (12, 0, 13, 100),
            (0, 50, 100, 50),
        ]
    )

    cleaned = clean_lines(hough_lines)

    assert cleaned.shape == (2, 4)


def test_keeps_lines_with_distinct_angles():
    hough_lines = _as_hough_lines(
        [
            (0, 0, 0, 100),  # vertical
            (0, 0, 100, 0),  # horizontal
            (0, 0, 100, 100),  # diagonal
        ]
    )

    cleaned = clean_lines(hough_lines)

    assert cleaned.shape == (3, 4)


def test_empty_input_returns_empty_array_with_expected_shape():
    hough_lines = np.empty((0, 1, 4), dtype=np.int32)

    cleaned = clean_lines(hough_lines)

    assert cleaned.shape == (0, 4)

