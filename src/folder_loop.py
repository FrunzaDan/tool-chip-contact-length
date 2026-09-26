import logging
import os

import process_image

logger = logging.getLogger(__name__)

# Define folder paths. os.path.join is used throughout (no hardcoded "/" or "\")
# so these paths are valid on Windows, Linux, and macOS alike.
INPUT_DATASET_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Input", "Complete_Dataset"
)
OUTPUT_HOUGH_RESULTS_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Output", "folder_hough_results"
)
OUTPUT_PLOT_RESULTS_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Output", "folder_plot_results"
)

# Ensure the output folders exist regardless of platform, so a fresh checkout
# (or one where they were deleted) doesn't fail on the first save.
os.makedirs(OUTPUT_HOUGH_RESULTS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_PLOT_RESULTS_FOLDER, exist_ok=True)


def process_folder() -> None:
    """Loop through the input dataset folder and process each BMP image."""
    logger.info(f"The input dataset folder is: {INPUT_DATASET_FOLDER}")

    image_number = 1
    for image_name in sorted(os.listdir(INPUT_DATASET_FOLDER)):
        image_path = os.path.join(INPUT_DATASET_FOLDER, image_name)

        # Skip directories and non-BMP files
        if os.path.isdir(image_path):
            logger.info(f"Skipping directory: {image_name}")
            continue

        # Skip hidden/system files such as macOS's .DS_Store, without logging
        # them as an unexpected/warning-worthy non-BMP file.
        if image_name.startswith("."):
            logger.info(f"Skipping hidden/system file: {image_name}")
            continue

        if image_name.endswith(".bmp"):
            logger.info(f"The nr. {image_number} current image is: {image_path}")

            try:
                process_image.process_image(image_path, image_name)
            except Exception:
                logger.exception("Exception during image processing")

            image_number += 1
        else:
            logger.warning(f"Skipping non-BMP image: {image_name}")
