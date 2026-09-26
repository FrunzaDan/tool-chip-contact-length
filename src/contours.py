import logging

import cv2
import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)

CONTOUR_BLUR_KERNEL_SIZE = (9, 9)
CONTOUR_BLUR_SIGMA = 1
MIN_CONTOUR_ARC_LENGTH = 500


def get_contours(
    dilated_image: npt.NDArray[np.uint8],
    canny_threshold_1: int,
    canny_threshold_2: int,
    canny_aperture_size: int,
) -> npt.NDArray[np.uint8]:
    """Perform edge detection and contour extraction.

    Returns a single-channel image with the qualifying contours drawn in white.
    """

    if dilated_image is None:
        raise ValueError("No valid Dilation Image provided.")

    # Initialize a black single-channel image for drawing contours (the Hough
    # step consumes it as grayscale, so 3 channels would only be converted back)
    contour_image = np.zeros(dilated_image.shape[:2], np.uint8)

    try:
        # Step 1: Apply Gaussian Blur to reduce noise
        blurred_image = cv2.GaussianBlur(
            dilated_image, CONTOUR_BLUR_KERNEL_SIZE, CONTOUR_BLUR_SIGMA
        )
    except cv2.error as error:
        logger.error(f"Error during GaussianBlur: {error}")
        return contour_image  # Return blank image on error

    try:
        # Step 2: Apply Canny edge detection
        canny_image = cv2.Canny(
            blurred_image, canny_threshold_1, canny_threshold_2, canny_aperture_size
        )
    except cv2.error as error:
        logger.error(f"Error during Canny edge detection: {error}")
        return contour_image  # Return blank image on error

    # Step 3: Find contours from the Canny edges
    contours, _ = cv2.findContours(
        canny_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )

    # Step 4: Draw contours on the black image
    for contour in contours:
        contour_length = cv2.arcLength(contour, True)
        if contour_length > MIN_CONTOUR_ARC_LENGTH:  # Only draw sufficiently large contours
            cv2.drawContours(contour_image, [contour], -1, 255, 2)

    logger.info(f"Contours detected: {len(contours)}")
    return contour_image
