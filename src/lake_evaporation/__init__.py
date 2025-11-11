"""
Lake Evaporation Estimation System

This package provides functionality to estimate lake evaporation based on
sensor observations using the Shuttleworth algorithm.
"""

from .main import LakeEvaporationApp

__version__ = "0.1.0"
__author__ = "Kisters AG"
__description__ = "Lake evaporation estimation based on sensor observations"

__all__ = [
    "LakeEvaporationApp",
]
