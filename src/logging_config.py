import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Log directory, relative to this file so it works from any working directory.
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Logs")

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5


def configure_logging() -> None:
    """Send log records from every module to a timestamped file in LOG_DIR
    and to the console.

    Each module gets its own logger via logging.getLogger(__name__); this
    configures the root logger once, from the entry point, so importing a
    module (e.g. from the tests) has no side effects.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    current_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOG_DIR, f"TCCL_process_{current_time_str}.log")

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Clear previous handlers in case this gets called more than once.
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
