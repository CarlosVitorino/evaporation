"""
Logging configuration for lake evaporation estimation system.

Provides structured logging to both console and file.
"""

import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str = "lake_evaporation",
    log_file: Optional[str] = None,
    log_level: str = "INFO"
) -> logging.Logger:
    """
    Set up application logger with console and file handlers.

    Args:
        name: Logger name
        log_file: Path to log file. If None, uses LOG_FILE env var or default
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    # Get log file path
    if log_file is None:
        log_file = os.getenv("LOG_FILE", "logs/lake_evaporation.log")

    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


class LoggerContext:
    """Context manager for logging specific operations."""

    def __init__(self, logger: logging.Logger, operation: str):
        """
        Initialize logger context.

        Args:
            logger: Logger instance
            operation: Name of the operation being logged
        """
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        """Enter context and log start."""
        self.start_time = datetime.now()
        self.logger.info(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and log completion or error."""
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is not None:
            self.logger.error(
                f"Failed {self.operation} after {duration:.2f}s: {exc_val}",
                exc_info=True
            )
            return False

        self.logger.info(f"Completed {self.operation} in {duration:.2f}s")
        return True
