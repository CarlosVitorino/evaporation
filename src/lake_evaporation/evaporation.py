"""
Shuttleworth algorithm for lake evaporation calculation.

Implements the lake evaporation algorithm based on the Excel reference.
"""

import logging
import math
from typing import Dict, Any, Optional
from datetime import datetime


class EvaporationCalculator:
    """Calculate lake evaporation using Shuttleworth algorithm."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize evaporation calculator.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def calculate(
        self,
        t_min: float,
        t_max: float,
        rh_min: float,
        rh_max: float,
        wind_speed: float,
        air_pressure: float,
        sunshine_hours: float,
        latitude: float,
        altitude: float,
        day_number: int,
        albedo: float = 0.23
    ) -> float:
        """
        Calculate daily lake evaporation using Shuttleworth algorithm.

        Args:
            t_min: Minimum temperature (°C)
            t_max: Maximum temperature (°C)
            rh_min: Minimum relative humidity (%)
            rh_max: Maximum relative humidity (%)
            wind_speed: Average wind speed at 10m (km/h)
            air_pressure: Average air pressure at station height (kPa)
            sunshine_hours: Actual hours of sunshine (hours)
            latitude: Location latitude (degrees)
            altitude: Station altitude (meters)
            day_number: Day of year (1-365/366)
            albedo: Surface albedo (default 0.23 for water)

        Returns:
            Lake evaporation in mm/day
        """
        self.logger.debug("Calculating lake evaporation")

        # Calculate mean temperature
        t_mean = (t_min + t_max) / 2

        # Calculate mean relative humidity
        rh_mean = (rh_min + rh_max) / 2

        # TODO: Implement full Shuttleworth algorithm
        # This is a placeholder that will be implemented in Phase 2
        # The algorithm should include:
        # 1. Solar radiation calculations
        # 2. Vapor pressure calculations
        # 3. Psychrometric constant
        # 4. Net radiation calculations
        # 5. Aerodynamic and surface resistance
        # 6. Final evaporation calculation

        self.logger.warning("Using placeholder evaporation calculation - implement full algorithm in Phase 2")

        # Placeholder calculation (will be replaced with actual algorithm)
        # This is just a simple approximation for testing
        evaporation = 0.0

        self.logger.debug(f"Calculated evaporation: {evaporation:.2f} mm/day")
        return evaporation

    def _calculate_saturation_vapor_pressure(self, temperature: float) -> float:
        """
        Calculate saturation vapor pressure at given temperature.

        Args:
            temperature: Temperature in °C

        Returns:
            Saturation vapor pressure in kPa
        """
        # Tetens formula
        return 0.6108 * math.exp((17.27 * temperature) / (temperature + 237.3))

    def _calculate_actual_vapor_pressure(
        self,
        temperature: float,
        relative_humidity: float
    ) -> float:
        """
        Calculate actual vapor pressure.

        Args:
            temperature: Temperature in °C
            relative_humidity: Relative humidity in %

        Returns:
            Actual vapor pressure in kPa
        """
        es = self._calculate_saturation_vapor_pressure(temperature)
        return (relative_humidity / 100) * es

    def _calculate_psychrometric_constant(
        self,
        air_pressure: float,
        temperature: float
    ) -> float:
        """
        Calculate psychrometric constant.

        Args:
            air_pressure: Air pressure in kPa
            temperature: Temperature in °C

        Returns:
            Psychrometric constant in kPa/°C
        """
        # Simplified calculation
        # gamma = 0.665 * 10^-3 * P
        return 0.000665 * air_pressure

    def _calculate_solar_declination(self, day_number: int) -> float:
        """
        Calculate solar declination for given day of year.

        Args:
            day_number: Day of year (1-365/366)

        Returns:
            Solar declination in radians
        """
        return 0.409 * math.sin((2 * math.pi / 365) * day_number - 1.39)

    def _calculate_extraterrestrial_radiation(
        self,
        latitude: float,
        day_number: int
    ) -> float:
        """
        Calculate extraterrestrial radiation.

        Args:
            latitude: Latitude in degrees
            day_number: Day of year

        Returns:
            Extraterrestrial radiation in MJ/m²/day
        """
        # Convert latitude to radians
        lat_rad = latitude * math.pi / 180

        # Solar declination
        delta = self._calculate_solar_declination(day_number)

        # Relative distance Earth-Sun
        dr = 1 + 0.033 * math.cos(2 * math.pi * day_number / 365)

        # Sunset hour angle
        ws = math.acos(-math.tan(lat_rad) * math.tan(delta))

        # Solar constant
        Gsc = 0.0820  # MJ/m²/min

        # Extraterrestrial radiation
        Ra = (24 * 60 / math.pi) * Gsc * dr * (
            ws * math.sin(lat_rad) * math.sin(delta) +
            math.cos(lat_rad) * math.cos(delta) * math.sin(ws)
        )

        return Ra

    def calculate_with_metadata(
        self,
        aggregates: Dict[str, float],
        location_metadata: Dict[str, Any],
        date: datetime,
        albedo: float = 0.23
    ) -> float:
        """
        Calculate evaporation with aggregated data and location metadata.

        Args:
            aggregates: Dictionary with daily aggregates
            location_metadata: Location metadata including lat/lon/altitude
            date: Date of calculation
            albedo: Surface albedo

        Returns:
            Lake evaporation in mm/day
        """
        # Extract location parameters
        location = location_metadata.get("location", {})
        latitude = location.get("latitude", 0)
        altitude = location.get("altitude", 0)

        # Get day of year
        day_number = date.timetuple().tm_yday

        # Extract required aggregates with defaults
        sunshine_hours = aggregates.get("sunshine_hours", 0)

        return self.calculate(
            t_min=aggregates["t_min"],
            t_max=aggregates["t_max"],
            rh_min=aggregates["rh_min"],
            rh_max=aggregates["rh_max"],
            wind_speed=aggregates["wind_speed_avg"],
            air_pressure=aggregates["air_pressure_avg"],
            sunshine_hours=sunshine_hours,
            latitude=latitude,
            altitude=altitude,
            day_number=day_number,
            albedo=albedo
        )
