"""
Evaporation data models.

Contains DTOs for evaporation calculation data structures.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class WeatherData:
    """Daily weather data aggregates."""

    t_min: float  # Minimum temperature (°C)
    t_max: float  # Maximum temperature (°C)
    rh_min: float  # Minimum relative humidity (%)
    rh_max: float  # Maximum relative humidity (%)
    wind_speed_avg: float  # Average wind speed (km/h)
    air_pressure_avg: float  # Average air pressure (kPa)
    sunshine_hours: Optional[float] = None  # Actual hours of sunshine


@dataclass
class LocationData:
    """Location metadata for evaporation calculation."""

    id: str
    name: str
    latitude: float
    longitude: float
    elevation: float
    organization_id: str
    organization_name: Optional[str] = None
    # Time series references
    temperature_ts: Optional[str] = None
    humidity_ts: Optional[str] = None
    wind_speed_ts: Optional[str] = None
    air_pressure_ts: Optional[str] = None
    sunshine_hours_ts: Optional[str] = None
    global_radiation_ts: Optional[str] = None


@dataclass
class EvaporationResult:
    """Result of evaporation calculation."""

    date: datetime
    evaporation: float  # mm/day
    location_name: str
    organization_id: str
    metadata: Optional[Dict[str, Any]] = None
