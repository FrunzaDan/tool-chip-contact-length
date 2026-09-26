"""Entry point: configure logging and process every image in the input folder."""

import logging
import sys

import folder_loop
from logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> int:
    """Run the batch and return the process exit code (0 on success, 1 on error).

    A failure on a single image is logged and skipped inside the batch; only
    an error that stops the whole batch (e.g. a missing input folder) fails.
    """
    configure_logging()
    logger.info("Start!")
    try:
        folder_loop.process_folder()
    except Exception:
        logger.exception("An error occurred")
        return 1
    else:
        logger.info("Folder processing completed successfully.")
        return 0
    finally:
        logger.info("End!")


if __name__ == "__main__":
    sys.exit(main())
