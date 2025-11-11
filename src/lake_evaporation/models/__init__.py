"""
Data models for lake evaporation system.

Contains DTOs for authentication, locations, time series, and evaporation data.
"""

from .auth import PortalCredentials, PortalUser
from .location import Location
from .timeseries import TimeSeries, TimeSeriesData
from .evaporation import WeatherData, LocationData, EvaporationResult

__all__ = [
    "PortalCredentials",
    "PortalUser",
    "Location",
    "TimeSeries",
    "TimeSeriesData",
    "WeatherData",
    "LocationData",
    "EvaporationResult",
]
