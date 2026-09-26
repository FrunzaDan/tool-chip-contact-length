import numpy as np

import process_image
from process_image import (
    _STEP_FAILED,
    RESIZE_WIDTH,
    _apply_dilation,
    _apply_otsu_threshold,
    _crop_right_half,
    _resize_to_fixed_width,
    _run_step,
)


def test_resize_to_fixed_width_preserves_aspect_ratio():
    image = np.zeros((200, 400, 3), dtype=np.uint8)  # height=200, width=400

    resized = _resize_to_fixed_width(image)

    assert resized.shape[1] == RESIZE_WIDTH
    assert resized.shape[0] == 200 * RESIZE_WIDTH // 400


def test_crop_right_half_keeps_only_right_half():
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[:, :5] = 1  # left half
    image[:, 5:] = 2  # right half

    cropped = _crop_right_half(image)

    assert cropped.shape == (10, 5, 3)
    assert np.all(cropped == 2)


def test_crop_right_half_returns_an_independent_copy():
    image = np.zeros((10, 10, 3), dtype=np.uint8)

    cropped = _crop_right_half(image)
    cropped[:] = 255

    assert not np.any(image[:, 5:] == 255)


def test_apply_otsu_threshold_produces_binary_image():
    image = np.zeros((50, 50), dtype=np.uint8)
    image[:25] = 10
    image[25:] = 240

    thresholded = _apply_otsu_threshold(image)

    assert set(np.unique(thresholded)).issubset({0, 255})


def test_apply_dilation_grows_foreground_region():
    image = np.zeros((50, 50), dtype=np.uint8)
    image[25, 25] = 255

    dilated = _apply_dilation(image)

    assert np.count_nonzero(dilated) > 1


def test_apply_morphological_closing_fills_small_gap(monkeypatch):
    # The production kernel/iteration count (4x4, 10 iterations - tuned for
    # the real dataset, see ai_docs/known_gaps.md) drifts the shape noticeably
    # over that many iterations, which would make this test sensitive to
    # exact pixel positions rather than to the closing behavior itself. Use a
    # small, deterministic kernel/iteration count to test that behavior in
    # isolation: a small hole surrounded by foreground gets filled in.
    monkeypatch.setattr(process_image, "MORPH_CLOSE_KERNEL_SIZE", (3, 3))
    monkeypatch.setattr(process_image, "MORPH_CLOSE_ITERATIONS", 1)

    image = np.zeros((50, 50), dtype=np.uint8)
    image[20:30, 20:30] = 255
    image[24:26, 24:26] = 0  # small hole inside the filled square

    closed = process_image._apply_morphological_closing(image)

    assert closed[25, 25] == 255


def test_run_step_returns_function_result_on_success():
    result = _run_step("Add", "image.bmp", lambda a, b: a + b, 2, 3)

    assert result == 5


def test_run_step_returns_sentinel_and_does_not_raise_on_error():
    def _boom():
        raise RuntimeError("boom")

    result = _run_step("Boom", "image.bmp", _boom)

    assert result is _STEP_FAILED
