"""
Logging configuration for the outreach engine.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from src.config import config


def setup_logging():
    """Configure logging for the application."""

    # Create logs directory if it doesn't exist
    config.LOGS_DIR.mkdir(exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # File handler for all logs
    log_file = config.LOGS_DIR / f"outreach_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_log_file = config.LOGS_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info("Logging initialized successfully")


# Initialize logging on module import
setup_logging()
