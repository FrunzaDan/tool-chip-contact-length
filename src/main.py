import logging

import folder_loop
from logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Main function to start folder processing."""
    configure_logging()
    logger.info("Start!")
    try:
        folder_loop.process_folder()
    except Exception:
        logger.exception("An error occurred")
    else:
        logger.info("Folder processing completed successfully.")
    finally:
        logger.info("End!")


if __name__ == "__main__":
    main()
