"""
Evaporation calculator facade for lake evaporation estimation.

This module provides a simplified interface to the Shuttleworth calculation engine,
handling the extraction of parameters from aggregated data and location metadata.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..core import constants
from .shuttleworth import ShuttleworthCalculator, EvaporationComponents


class EvaporationCalculator:
    """
    High-level calculator for lake evaporation.

    This class acts as a facade, providing a clean interface to the Shuttleworth
    calculation engine while handling data extraction and parameter mapping.
    """

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
        albedo: float = constants.DEFAULT_ALBEDO
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
        self.logger.debug("Calculating lake evaporation using Shuttleworth algorithm")

        try:
            evaporation = ShuttleworthCalculator.calculate_lake_evaporation(
                t_max=t_max,
                t_min=t_min,
                rh_max=rh_max,
                rh_min=rh_min,
                u10=wind_speed,
                sunshine_hours=sunshine_hours,
                pressure=air_pressure,
                latitude=latitude,
                altitude=altitude,
                day_number=day_number,
                albedo=albedo
            )

            self.logger.debug(f"Calculated evaporation: {evaporation:.2f} mm/day")
            return evaporation

        except Exception as e:
            self.logger.error(f"Error calculating evaporation: {e}", exc_info=True)
            raise

    def calculate_with_metadata(
        self,
        aggregates: Dict[str, float],
        location_metadata: Dict[str, Any],
        date: datetime,
        albedo: float = constants.DEFAULT_ALBEDO
    ) -> float:
        """
        Calculate evaporation with aggregated data and location metadata.

        This method extracts the necessary parameters from the aggregates dictionary
        and location metadata, then delegates to the Shuttleworth calculation engine.

        Args:
            aggregates: Dictionary with daily aggregates:
                - t_min: Minimum temperature (°C)
                - t_max: Maximum temperature (°C)
                - rh_min: Minimum relative humidity (%)
                - rh_max: Maximum relative humidity (%)
                - wind_speed_avg: Average wind speed (km/h)
                - air_pressure_avg: Average air pressure (kPa)
                - sunshine_hours: Actual hours of sunshine (optional)
            location_metadata: Location metadata including lat/lon/altitude
            date: Date of calculation
            albedo: Surface albedo (default 0.23 for water)

        Returns:
            Lake evaporation in mm/day
        """
        location = location_metadata.get("location", {})
        latitude = location.get("latitude", 0)
        altitude = location.get("elevation", 0)
        day_number = date.timetuple().tm_yday
        sunshine_hours = aggregates.get("sunshine_hours", 0)

        self.logger.info(
            f"Evaporation calculation parameters - "
            f"Date: {date.strftime('%Y-%m-%d')}, "
            f"T_min: {aggregates['t_min']:.2f}°C, "
            f"T_max: {aggregates['t_max']:.2f}°C, "
            f"RH_min: {aggregates['rh_min']:.1f}%, "
            f"RH_max: {aggregates['rh_max']:.1f}%, "
            f"Wind: {aggregates['wind_speed_avg']:.2f} km/h, "
            f"Pressure: {aggregates['air_pressure_avg']:.2f} kPa, "
            f"Sunshine: {sunshine_hours:.2f}h, "
            f"Lat: {latitude:.4f}°, "
            f"Alt: {altitude:.1f}m, "
            f"Day: {day_number}, "
            f"Albedo: {albedo:.2f}"
        )

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

    def calculate_with_components(
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
        albedo: float = constants.DEFAULT_ALBEDO
    ) -> EvaporationComponents:
        """
        Calculate evaporation with detailed intermediate components.

        This method is useful for debugging, validation, and detailed analysis,
        as it returns all intermediate calculation values.

        Args:
            Same as calculate()

        Returns:
            EvaporationComponents object containing all intermediate values
        """
        self.logger.debug("Calculating lake evaporation with component details")

        try:
            components = ShuttleworthCalculator.calculate_with_components(
                t_max=t_max,
                t_min=t_min,
                rh_max=rh_max,
                rh_min=rh_min,
                u10=wind_speed,
                sunshine_hours=sunshine_hours,
                pressure=air_pressure,
                latitude=latitude,
                altitude=altitude,
                day_number=day_number,
                albedo=albedo
            )

            self.logger.debug(
                f"Calculated evaporation: {components.evaporation_total:.2f} mm/day "
                f"(Ea={components.aerodynamic_component:.2f}, "
                f"Er={components.radiation_component:.2f})"
            )

            return components

        except Exception as e:
            self.logger.error(f"Error calculating evaporation components: {e}", exc_info=True)
            raise
