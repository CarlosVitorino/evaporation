"""
Data validation module.

Validates aggregated meteorological data for quality and completeness.
"""

import logging
from typing import Dict, List, Tuple, Optional


class DataValidator:
    """Validate aggregated meteorological data."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize data validator.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def validate_aggregates(self, aggregates: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Validate that all required aggregates are present and in valid ranges.

        Args:
            aggregates: Dictionary with aggregated values

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        required = ["t_min", "t_max", "rh_min", "rh_max", "wind_speed_avg", "air_pressure_avg"]
        for field in required:
            if field not in aggregates:
                errors.append(f"Missing required field: {field}")

        # Validate ranges
        if "t_min" in aggregates and "t_max" in aggregates:
            if aggregates["t_min"] > aggregates["t_max"]:
                errors.append("t_min cannot be greater than t_max")

        if "rh_min" in aggregates:
            if not (0 <= aggregates["rh_min"] <= 100):
                errors.append(f"Invalid rh_min: {aggregates['rh_min']} (must be 0-100)")

        if "rh_max" in aggregates:
            if not (0 <= aggregates["rh_max"] <= 100):
                errors.append(f"Invalid rh_max: {aggregates['rh_max']} (must be 0-100)")

        if "wind_speed_avg" in aggregates:
            if aggregates["wind_speed_avg"] < 0:
                errors.append(f"Invalid wind_speed_avg: {aggregates['wind_speed_avg']} (must be >= 0)")

        if "air_pressure_avg" in aggregates:
            if not (50 < aggregates["air_pressure_avg"] < 120):
                errors.append(
                    f"Suspicious air_pressure_avg: {aggregates['air_pressure_avg']} kPa "
                    "(expected 50-120 kPa)"
                )

        is_valid = len(errors) == 0
        return is_valid, errors

    def check_data_completeness(
        self,
        data: Dict[str, List[Dict]],
        required_fields: Optional[List[str]] = None
    ) -> bool:
        """
        Check if all required data is available.

        Args:
            data: Dictionary with sensor data
            required_fields: List of required field names

        Returns:
            True if all required data is present, False otherwise
        """
        if required_fields is None:
            required_fields = ["temperature", "humidity", "wind_speed", "air_pressure"]

        missing = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing.append(field)

        if missing:
            self.logger.error(f"Missing required data: {', '.join(missing)}")
            return False

        return True
