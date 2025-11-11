"""
Lake Evaporation Estimation System

This package provides functionality to estimate lake evaporation based on
sensor observations using the Shuttleworth algorithm.
"""

__version__ = "0.1.0"
__author__ = "Kisters AG"
__description__ = "Lake evaporation estimation based on sensor observations"


def __getattr__(name):
    """Lazy import to avoid importing dependencies when not needed."""
    if name == "LakeEvaporationApp":
        from .main import LakeEvaporationApp
        return LakeEvaporationApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LakeEvaporationApp",
]
