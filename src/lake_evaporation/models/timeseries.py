"""
Time series data models.

Contains DTOs for time series-related data structures.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class TimeSeries:
    """Organization time series data."""

    id: str
    name: str
    location_id: Optional[str] = None
    location_name: Optional[str] = None
    location_latitude: Optional[float] = None
    location_longitude: Optional[float] = None
    location_elevation: Optional[float] = None
    location_geometry_type: Optional[str] = None
    variable: Optional[str] = None
    unit: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    coverage: Optional[Dict[str, str]] = None


@dataclass
class TimeSeriesData:
    """Time series data point."""

    timestamp: str
    value: float
    quality: Optional[str] = None
    flags: Optional[list] = None
