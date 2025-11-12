"""
Sunshine hours calculation using Ångström-Prescott method.

Estimates actual sunshine hours from global radiation measurements.
"""

import logging
import math
import statistics
from typing import Dict, Any, List, Optional
from datetime import datetime


class SunshineCalculator:
    """Calculate sunshine hours from global radiation."""

    def __init__(
        self,
        a: float = 0.25,
        b: float = 0.5,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize sunshine calculator.

        Args:
            a: Ångström-Prescott coefficient a (default 0.25)
            b: Ångström-Prescott coefficient b (default 0.5)
            logger: Logger instance
        """
        self.a = a
        self.b = b
        self.logger = logger or logging.getLogger(__name__)

    def calculate_sunshine_hours(
        self,
        global_radiation: float,
        latitude: float,
        day_number: int
    ) -> float:
        """
        Calculate actual sunshine hours using Ångström-Prescott method.

        The Ångström-Prescott equation relates global radiation to sunshine duration:
        Rs/Ra = a + b * (n/N)

        Where:
        - Rs = measured global radiation
        - Ra = extraterrestrial radiation
        - n = actual sunshine hours
        - N = maximum possible sunshine hours (day length)
        - a, b = empirical coefficients

        Solving for n:
        n = N * (Rs/Ra - a) / b

        Args:
            global_radiation: Measured global radiation (MJ/m²/day)
            latitude: Location latitude (degrees)
            day_number: Day of year (1-365/366)

        Returns:
            Actual sunshine hours
        """
        self.logger.debug(f"Calculating sunshine hours from global radiation: {global_radiation:.2f} MJ/m²/day")

        # Calculate extraterrestrial radiation
        Ra = self._calculate_extraterrestrial_radiation(latitude, day_number)
        self.logger.debug(f"Extraterrestrial radiation: {Ra:.2f} MJ/m²/day")

        # Calculate maximum possible sunshine hours (day length)
        N = self._calculate_daylight_hours(latitude, day_number)
        self.logger.debug(f"Maximum daylight hours: {N:.2f} hours")

        # Apply Ångström-Prescott equation to solve for n
        if Ra > 0:
            ratio = global_radiation / Ra
            n = N * (ratio - self.a) / self.b

            # Ensure sunshine hours are within valid range [0, N]
            n = max(0, min(n, N))
        else:
            n = 0

        self.logger.debug(f"Calculated sunshine hours: {n:.2f} hours")
        return n

    def calculate_from_data_points(
        self,
        radiation_data: List[List[Any]],
        latitude: float,
        day_number: int
    ) -> float:
        """
        Calculate sunshine hours from global radiation data points.

        Args:
            radiation_data: List of [timestamp, radiation_value] pairs in W/m²
            latitude: Latitude in decimal degrees
            day_number: Day of year (1-365)

        Returns:
            Estimated sunshine hours
        """
        if not radiation_data:
            return 0.0

        # Extract radiation values (second element of each [timestamp, value] pair)
        radiation_values = [point[1] for point in radiation_data if len(point) > 1 and point[1] is not None]
        
        if not radiation_values:
            return 0.0

        # Calculate mean radiation for the day
        mean_radiation = statistics.mean(radiation_values)

        return self.calculate_sunshine_hours(
            mean_radiation,
            latitude=latitude,
            day_number=day_number
        )

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

    def _calculate_solar_declination(self, day_number: int) -> float:
        """
        Calculate solar declination.

        Args:
            day_number: Day of year (1-365/366)

        Returns:
            Solar declination in radians
        """
        return 0.409 * math.sin((2 * math.pi / 365) * day_number - 1.39)

    def _calculate_daylight_hours(self, latitude: float, day_number: int) -> float:
        """
        Calculate maximum possible sunshine hours (day length).

        Args:
            latitude: Latitude in degrees
            day_number: Day of year

        Returns:
            Maximum daylight hours
        """
        # Convert latitude to radians
        lat_rad = latitude * math.pi / 180

        # Solar declination
        delta = self._calculate_solar_declination(day_number)

        # Sunset hour angle
        ws = math.acos(-math.tan(lat_rad) * math.tan(delta))

        # Day length in hours
        N = (24 / math.pi) * ws

        return N

    def estimate_from_cloud_cover(
        self,
        cloud_cover_low: float,
        cloud_cover_medium: float,
        cloud_cover_high: float,
        latitude: float,
        day_number: int
    ) -> float:
        """
        Estimate sunshine hours from cloud cover data (NWP analysis).

        This is an alternative method when global radiation is not available.

        Args:
            cloud_cover_low: Low cloud cover (%)
            cloud_cover_medium: Medium cloud cover (%)
            cloud_cover_high: High cloud cover (%)
            latitude: Location latitude
            day_number: Day of year

        Returns:
            Estimated sunshine hours
        """
        self.logger.debug("Estimating sunshine hours from cloud cover")

        # Calculate maximum possible sunshine hours
        N = self._calculate_daylight_hours(latitude, day_number)

        # Weight cloud layers (low clouds have more impact)
        total_cloud = (
            cloud_cover_low * 1.0 +
            cloud_cover_medium * 0.6 +
            cloud_cover_high * 0.3
        ) / 1.9

        # Estimate clear sky fraction
        clear_fraction = 1 - (total_cloud / 100)

        # Estimated sunshine hours
        n = N * clear_fraction

        self.logger.debug(f"Estimated sunshine hours from cloud cover: {n:.2f} hours")
        return n
