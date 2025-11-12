"""
Core utilities for lake evaporation system.

Provides configuration management and logging functionality.
"""

from .config import Config
from .logger import setup_logger, LoggerContext

__all__ = [
    "Config",
    "setup_logger",
    "LoggerContext",
]
