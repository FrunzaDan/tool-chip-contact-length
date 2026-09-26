"""Logging setup for the application: one call, from the entry point."""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Log directory, relative to this file so it works from any working directory.
LOG_DIR = Path(__file__).resolve().parent.parent / "Logs"

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5


def configure_logging() -> None:
    """Send log records from every module to a timestamped file and the console.

    Each module gets its own logger via logging.getLogger(__name__); this
    configures the root logger once, from the entry point, so importing a
    module (e.g. from the tests) has no side effects.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    current_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = LOG_DIR / f"TCCL_process_{current_time_str}.log"

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
