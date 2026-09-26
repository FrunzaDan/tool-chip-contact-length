import logging

import numpy as np

import hough_lines


def _patch_pipeline(monkeypatch, *, horizontal_y, vertical_y):
    """Stub out everything measure_contact_length calls internally, so the
    contact-length arithmetic and the sanity-check logging can be tested in
    isolation from real Hough-line detection."""
    monkeypatch.setattr(
        hough_lines, "detect_hough_lines", lambda *a, **k: np.array([[0, 0, 1, 1]])
    )
    monkeypatch.setattr(hough_lines, "clean_lines", lambda lines: lines)
    monkeypatch.setattr(
        hough_lines,
        "get_horizontal_line_y_index",
        lambda cleaned_lines, image: (horizontal_y, image),
    )
    monkeypatch.setattr(
        hough_lines,
        "get_vertical_line_y_index",
        lambda cleaned_lines, contour_image, image: (vertical_y, image),
    )

    saved = {}
    monkeypatch.setattr(
        hough_lines,
        "save_result_image",
        lambda name, image, contact_length: saved.update(contact_length=contact_length),
    )
    return saved


def _run(monkeypatch, caplog, *, horizontal_y, vertical_y):
    saved = _patch_pipeline(
        monkeypatch, horizontal_y=horizontal_y, vertical_y=vertical_y
    )
    contour_image = np.zeros((20, 20), dtype=np.uint8)
    original_image = np.zeros((20, 20, 3), dtype=np.uint8)

    with caplog.at_level(logging.WARNING, logger="hough_lines"):
        hough_lines.measure_contact_length(
            contour_image, original_image, 1, 1, 1, "image.bmp"
        )

    return saved


def test_positive_contact_length_is_saved_without_warning(monkeypatch, caplog):
    saved = _run(monkeypatch, caplog, horizontal_y=90, vertical_y=10)

    assert saved["contact_length"] == 80
    assert not any("non-positive" in record.message for record in caplog.records)


def test_negative_contact_length_is_saved_and_flagged_as_suspect(monkeypatch, caplog):
    saved = _run(monkeypatch, caplog, horizontal_y=10, vertical_y=50)

    assert saved["contact_length"] == -40
    assert any("non-positive" in record.message for record in caplog.records)


def test_no_hough_lines_detected_skips_contact_length_calculation(monkeypatch, caplog):
    monkeypatch.setattr(hough_lines, "detect_hough_lines", lambda *a, **k: None)
    contour_image = np.zeros((20, 20), dtype=np.uint8)
    original_image = np.zeros((20, 20, 3), dtype=np.uint8)

    with caplog.at_level(logging.WARNING, logger="hough_lines"):
        result = hough_lines.measure_contact_length(
            contour_image, original_image, 1, 1, 1, "image.bmp"
        )

    assert result is not None
    assert any("No Hough lines detected" in record.message for record in caplog.records)
