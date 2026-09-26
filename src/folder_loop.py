"""Batch loop over the input dataset folder, and the input/output folder paths."""

import logging
from pathlib import Path

import process_image

logger = logging.getLogger(__name__)

# Folder paths, relative to this file so they work from any working directory.
# pathlib builds them with the right separator on Windows, Linux, and macOS.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DATASET_FOLDER = PROJECT_ROOT / "Input" / "Complete_Dataset"
OUTPUT_HOUGH_RESULTS_FOLDER = PROJECT_ROOT / "Output" / "folder_hough_results"
OUTPUT_PLOT_RESULTS_FOLDER = PROJECT_ROOT / "Output" / "folder_plot_results"

# Ensure the output folders exist regardless of platform, so a fresh checkout
# (or one where they were deleted) doesn't fail on the first save.
OUTPUT_HOUGH_RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_PLOT_RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)


def process_folder() -> None:
    """Loop through the input dataset folder and process each BMP image."""
    logger.info("The input dataset folder is: %s", INPUT_DATASET_FOLDER)

    image_number = 1
    for image_path in sorted(INPUT_DATASET_FOLDER.iterdir()):
        image_name = image_path.name

        # Skip directories and non-BMP files
        if image_path.is_dir():
            logger.info("Skipping directory: %s", image_name)
            continue

        # Skip hidden/system files such as macOS's .DS_Store, without logging
        # them as an unexpected/warning-worthy non-BMP file.
        if image_name.startswith("."):
            logger.info("Skipping hidden/system file: %s", image_name)
            continue

        if image_path.suffix == ".bmp":
            logger.info("The nr. %d current image is: %s", image_number, image_path)

            try:
                process_image.process_image(image_path)
            except Exception:
                logger.exception("Exception during image processing")

            image_number += 1
        else:
            logger.warning("Skipping non-BMP image: %s", image_name)
