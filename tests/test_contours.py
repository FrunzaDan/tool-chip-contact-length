import numpy as np
import pytest

from contours import MIN_CONTOUR_ARC_LENGTH, get_contours


def test_raises_on_none_input():
    with pytest.raises(ValueError):
        get_contours(None, 100, 200, 3)


def test_draws_a_sufficiently_large_contour():
    image = np.zeros((300, 300), dtype=np.uint8)
    # A filled square with a perimeter well above MIN_CONTOUR_ARC_LENGTH.
    image[30:270, 30:270] = 255
    assert 4 * 240 > MIN_CONTOUR_ARC_LENGTH

    result = get_contours(image, 100, 200, 3)

    assert result.shape == (300, 300)
    assert np.any(result != 0)


def test_skips_contours_smaller_than_the_minimum_arc_length():
    image = np.zeros((200, 200), dtype=np.uint8)
    # A tiny square whose perimeter is far below MIN_CONTOUR_ARC_LENGTH.
    assert 4 * 5 < MIN_CONTOUR_ARC_LENGTH
    image[10:15, 10:15] = 255

    result = get_contours(image, 100, 200, 3)

    assert np.all(result == 0)
