"""
Sunshine hours calculation module.

Provides methods to calculate sunshine hours using different methods.
"""

import logging
import math
from typing import List, Tuple, Optional, Any
from datetime import datetime


class SunshineCalculator:

    def __init__(
        self,
        a: float = 0.25,
        b: float = 0.50,
        logger=None
    ):
        """
        Initialize calculator.

        Args:
            a: Ångström-Prescott coefficient a (default 0.25)
            b: Ångström-Prescott coefficient b (default 0.50)
            logger: Logger instance
        """
        self.a = a
        self.b = b
        self.logger = logger or logging.getLogger(__name__)

    def calculate_from_data_points(
        self,
        radiation_data: List[List[Any]],
        latitude: float,
        day_number: int
    ) -> float:
        """
        Calculate sunshine hours from global radiation measurements.

        Uses the Ångström-Prescott equation inverted:
        Rs/Ra = a + b*(n/N)
        Therefore: n = N * (Rs/Ra - a) / b

        Args:
            radiation_data: List of (timestamp, radiation) tuples in W/m²
                           or list of dicts with "value" key
            latitude: Latitude in decimal degrees
            day_number: Day of year (1-365)

        Returns:
            Sunshine hours for the day
        """
        if not radiation_data:
            return 0.0

        def extract_value(point: Any) -> Optional[float]:
            if isinstance(point, dict):
                return point.get("value")
            elif isinstance(point, (list, tuple)) and len(point) > 1:
                return point[1]
            return None

        values = [extract_value(point) for point in radiation_data]
        values = [v for v in values if v is not None]
        
        if not values:
            return 0.0

        total_radiation_wm2 = sum(values)
        mean_radiation_wm2 = total_radiation_wm2 / len(values)
        rs = mean_radiation_wm2 * 0.0864

        return self.calculate_sunshine_hours(
            global_radiation=rs,
            latitude=latitude,
            day_number=day_number
        )

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
    
    def calculate_from_cloud_cover_layers(
        self,
        latitude: float,
        day_number: int,
        low_cloud_octas: float,
        medium_cloud_octas: float,
        high_cloud_octas: float
    ) -> float:
        """
        Calculate sunshine hours from layered cloud cover data (NWP/observation method).
        
        Formula from meteorological practice:
            nel = nl + 0.875 * ((8 - nl) / 8) * nm
            Ne = nel + 0.25 * ((8 - nel) / 8) * nh
        
        Then converts effective cloud cover to sunshine hours using empirical relationship.
        
        Args:
            latitude: Latitude in decimal degrees
            day_number: Day of year (1-365)
            low_cloud_octas: Low cloud cover (0-8 octas, below 2km altitude)
            medium_cloud_octas: Medium cloud cover (0-8 octas, 2-6km altitude)
            high_cloud_octas: High cloud cover (0-8 octas, above 6km altitude)
        
        Returns:
            Sunshine hours for the day
            
    
        """
        # Step 1: Calculate maximum possible sunshine hours
        max_daylight_hours = self._calculate_daylight_hours(latitude, day_number)
        
        # Step 2: Ensure cloud values are within valid range [0, 8]
        nl = max(0.0, min(8.0, low_cloud_octas))
        nm = max(0.0, min(8.0, medium_cloud_octas))
        nh = max(0.0, min(8.0, high_cloud_octas))
        
        # Step 3: Calculate effective low+medium cloud cover (nel)
        effective_low_medium = nl + 0.875 * ((8 - nl) / 8) * nm
        
        # Step 4: Calculate total effective cloud cover (Ne)
        effective_total_cloud = effective_low_medium + 0.25 * ((8 - effective_low_medium) / 8) * nh
        
        # Step 5: Convert effective cloud cover to sunshine fraction
        sunshine_fraction = 1.0 - (effective_total_cloud / 8.0) 
        sunshine_fraction = max(0.0, min(1.0, sunshine_fraction))
        
        # Step 6: Calculate actual sunshine hours
        actual_sunshine_hours = max_daylight_hours * sunshine_fraction
        
        if self.logger:
            self.logger.debug(
                f"Layered cloud sunshine calculation: "
                f"Low={nl:.1f}, Medium={nm:.1f}, High={nh:.1f} octas, "
                f"Effective cloud (Ne)={effective_total_cloud:.2f} octas, "
                f"Max daylight={max_daylight_hours:.2f}h, "
                f"Sunshine fraction={sunshine_fraction:.1%}, "
                f"Estimated sunshine={actual_sunshine_hours:.2f}h"
            )
        
        return actual_sunshine_hours
 
    def calculate_from_temperature_range(
        self,
        latitude: float,
        day_number: int,
        t_min: float,
        t_max: float,
        coastal: bool = False
    ) -> float:
        """
        Calculate sunshine hours from temperature range (Hargreaves method).

        Uses empirical relationship: n/N ≈ kRs * sqrt(Tmax - Tmin)
        where kRs depends on location (interior vs coastal)
        
        Formula: actual_sunshine_hours / max_possible_hours ≈ k_hargreaves * √(T_max - T_min)

        Args:
            latitude: Latitude in decimal degrees
            day_number: Day of year (1-365)
            t_min: Minimum temperature (°C)
            t_max: Maximum temperature (°C)
            coastal: True if location is coastal (within ~50km of coast)

        Returns:
            Sunshine hours for the day
        """
        # Calculate maximum daylight hours
        n_max = self._calculate_daylight_hours(latitude, day_number)

        # Temperature difference
        temp_diff = max(0, t_max - t_min)

        # Hargreaves empirical coefficient
        # Coastal locations have smaller temperature ranges for same radiation
        kRs = 0.16 if coastal else 0.19

        # Estimate sunshine fraction
        sunshine_fraction = kRs * math.sqrt(temp_diff)
        sunshine_fraction = max(0.0, min(1.0, sunshine_fraction))

        n = n_max * sunshine_fraction

        if self.logger:
            self.logger.debug(
                f"Sunshine from temp range: N={n_max:.2f}h, "
                f"ΔT={temp_diff:.1f}°C, n={n:.2f}h"
            )

        return n

    def _calculate_extraterrestrial_radiation(
        self,
        latitude: float,
        day_number: int
    ) -> float:
        """
        Calculate extraterrestrial radiation (Ra) in MJ/m²/day.
        Based on FAO-56 equation 21.

        Args:
            latitude: Latitude in decimal degrees
            day_number: Day of year (1-365)

        Returns:
            Extraterrestrial radiation in MJ/m²/day
        """
        # Convert latitude to radians
        lat_rad = math.radians(latitude)

        # Solar constant
        gsc = 0.0820  # MJ/m²/min

        # Inverse relative distance Earth-Sun
        dr = 1 + 0.033 * math.cos(2 * math.pi * day_number / 365)

        # Solar declination
        delta = 0.409 * math.sin(2 * math.pi * day_number / 365 - 1.39)

        # Sunset hour angle
        ws = math.acos(-math.tan(lat_rad) * math.tan(delta))

        # Extraterrestrial radiation
        ra = (24 * 60 / math.pi) * gsc * dr * (
            ws * math.sin(lat_rad) * math.sin(delta) +
            math.cos(lat_rad) * math.cos(delta) * math.sin(ws)
        )

        return ra

    def _calculate_daylight_hours(
        self,
        latitude: float,
        day_number: int
    ) -> float:
        """
        Calculate maximum possible daylight hours (N).

        Based on FAO-56 equation 34.

        Args:
            latitude: Latitude in decimal degrees
            day_number: Day of year (1-365)

        Returns:
            Maximum daylight hours
        """
        # Convert latitude to radians
        lat_rad = math.radians(latitude)

        # Solar declination
        delta = 0.409 * math.sin(2 * math.pi * day_number / 365 - 1.39)

        # Sunset hour angle
        ws = math.acos(-math.tan(lat_rad) * math.tan(delta))

        # Daylight hours
        n = 24 * ws / math.pi

        return n