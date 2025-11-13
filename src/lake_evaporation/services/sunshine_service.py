"""
Sunshine hours calculation service.

Handles multiple methods for determining sunshine hours from various data sources.
"""

import logging
from typing import Dict, Any, List, Optional

from ..algorithms import SunshineCalculator


class SunshineService:
    """Service to calculate sunshine hours using multiple fallback methods."""

    def __init__(
        self,
        sunshine_calc: SunshineCalculator,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize sunshine service.

        Args:
            sunshine_calc: Sunshine calculator instance
            logger: Logger instance
        """
        self.sunshine_calc = sunshine_calc
        self.logger = logger or logging.getLogger(__name__)

    def calculate_sunshine_hours(
        self,
        data: Dict[str, List[List[Any]]],
        aggregates: Dict[str, float],
        latitude: float,
        day_number: int,
        location_info: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate sunshine hours using the best available method.

        Tries methods in this order of preference:
        1. Direct measurement from sunshine hours sensor
        2. Calculate from global radiation sensor (Ångström-Prescott)
        3. Calculate from cloud layer data (NWP/observation method)
        4. Fallback: Calculate from temperature range (Hargreaves)

        Args:
            data: Raw sensor data dictionary
            aggregates: Aggregated daily values
            latitude: Location latitude in degrees
            day_number: Day of year (1-365)
            location_info: Optional location metadata (for coastal flag)

        Returns:
            Sunshine hours for the day
        """
        location_info = location_info or {}

        # OPTION 1: Use directly measured sunshine hours if available
        if "sunshine_hours" in aggregates and aggregates["sunshine_hours"] is not None:
            sunshine = aggregates["sunshine_hours"]
            self.logger.info(f"Using directly measured sunshine hours: {sunshine:.2f}h")
            return sunshine

        # OPTION 2: Calculate from global radiation sensor data (Ångström-Prescott)
        if "global_radiation" in data and data["global_radiation"]:
            self.logger.info("Calculating sunshine hours from global radiation (Ångström-Prescott)")
            
            sunshine = self.sunshine_calc.calculate_from_data_points(
                radiation_data=data["global_radiation"],
                latitude=latitude,
                day_number=day_number
            )
            self.logger.info(f"Calculated sunshine hours from radiation: {sunshine:.2f}h")
            return sunshine

        # OPTION 3: Calculate from raster data (cloud layers from NWP)
        if self._has_cloud_layer_data(aggregates):
            self.logger.info("Calculating sunshine hours from cloud layer data (Ne method)")
            
            sunshine = self.sunshine_calc.calculate_from_cloud_cover_layers(
                latitude=latitude,
                day_number=day_number,
                low_cloud_octas=aggregates["low_cloud_octas"],
                medium_cloud_octas=aggregates["medium_cloud_octas"],
                high_cloud_octas=aggregates["high_cloud_octas"]
            )
            self.logger.info(f"Calculated sunshine hours from cloud layers: {sunshine:.2f}h")
            return sunshine

        # FALLBACK: Calculate from temperature range (Hargreaves method)
        if self._has_temperature_data(aggregates):
            self.logger.warning(
                "Using temperature-based fallback estimate (Hargreaves method). "
                "This is less accurate than other methods."
            )
            
            coastal = location_info.get("coastal", False)
            sunshine = self.sunshine_calc.calculate_from_temperature_range(
                latitude=latitude,
                day_number=day_number,
                t_min=aggregates["t_min"],
                t_max=aggregates["t_max"],
                coastal=coastal
            )
            self.logger.warning(f"Temperature-based sunshine estimate: {sunshine:.2f}h")
            return sunshine

        # NO DATA AVAILABLE
        self.logger.error(
            "Cannot calculate sunshine hours - insufficient data. "
            "Missing: direct measurement, global radiation sensor, cloud layer data, or temperature range."
        )
        return 0.0

    def _has_cloud_layer_data(self, aggregates: Dict[str, float]) -> bool:
        """Check if cloud layer data is available."""
        required_keys = ["low_cloud_octas", "medium_cloud_octas", "high_cloud_octas"]
        return all(
            key in aggregates and aggregates[key] is not None
            for key in required_keys
        )

    def _has_temperature_data(self, aggregates: Dict[str, float]) -> bool:
        """Check if temperature data is available."""
        return (
            "t_min" in aggregates and aggregates["t_min"] is not None and
            "t_max" in aggregates and aggregates["t_max"] is not None
        )
