"""
Data processing module for aggregations and unit conversions.

Processes raw sensor data into daily aggregates with proper units.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import statistics


class DataProcessor:
    """Process sensor data for evaporation calculations."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize data processor.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def calculate_daily_aggregates(
        self,
        data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, float]:
        """
        Calculate daily aggregates from raw sensor data.

        Args:
            data: Dictionary with sensor data lists

        Returns:
            Dictionary with aggregated values:
                - t_min: Minimum temperature (°C)
                - t_max: Maximum temperature (°C)
                - rh_min: Minimum relative humidity (%)
                - rh_max: Maximum relative humidity (%)
                - wind_speed_avg: Average wind speed (km/h)
                - air_pressure_avg: Average air pressure (kPa)
                - sunshine_hours: Actual hours of sunshine (if available)
        """
        self.logger.info("Calculating daily aggregates")
        aggregates = {}

        # Temperature aggregates
        if "temperature" in data and data["temperature"]:
            temps = [point["value"] for point in data["temperature"] if point.get("value") is not None]
            if temps:
                aggregates["t_min"] = min(temps)
                aggregates["t_max"] = max(temps)
                self.logger.debug(f"Temperature: min={aggregates['t_min']:.1f}, max={aggregates['t_max']:.1f}")
            else:
                self.logger.warning("No valid temperature values")

        # Humidity aggregates
        if "humidity" in data and data["humidity"]:
            rh = [point["value"] for point in data["humidity"] if point.get("value") is not None]
            if rh:
                aggregates["rh_min"] = min(rh)
                aggregates["rh_max"] = max(rh)
                self.logger.debug(f"Humidity: min={aggregates['rh_min']:.1f}, max={aggregates['rh_max']:.1f}")
            else:
                self.logger.warning("No valid humidity values")

        # Wind speed average
        if "wind_speed" in data and data["wind_speed"]:
            wind = [point["value"] for point in data["wind_speed"] if point.get("value") is not None]
            if wind:
                aggregates["wind_speed_avg"] = statistics.mean(wind)
                self.logger.debug(f"Wind speed avg: {aggregates['wind_speed_avg']:.2f}")
            else:
                self.logger.warning("No valid wind speed values")

        # Air pressure average
        if "air_pressure" in data and data["air_pressure"]:
            pressure = [point["value"] for point in data["air_pressure"] if point.get("value") is not None]
            if pressure:
                aggregates["air_pressure_avg"] = statistics.mean(pressure)
                self.logger.debug(f"Air pressure avg: {aggregates['air_pressure_avg']:.2f}")
            else:
                self.logger.warning("No valid air pressure values")

        # Sunshine hours (if directly measured)
        if "sunshine_hours" in data and data["sunshine_hours"]:
            sunshine = [point["value"] for point in data["sunshine_hours"] if point.get("value") is not None]
            if sunshine:
                # Sum or average depending on how it's measured
                aggregates["sunshine_hours"] = sum(sunshine)
                self.logger.debug(f"Sunshine hours: {aggregates['sunshine_hours']:.2f}")

        return aggregates

    def convert_units(
        self,
        aggregates: Dict[str, float],
        source_units: Dict[str, str]
    ) -> Dict[str, float]:
        """
        Convert aggregated values to required units.

        Target units:
        - Temperature: °C
        - Humidity: %
        - Wind speed: km/h
        - Air pressure: kPa
        - Sunshine: hours

        Args:
            aggregates: Dictionary with aggregated values
            source_units: Dictionary mapping field names to their source units

        Returns:
            Dictionary with converted values
        """
        self.logger.info("Converting units")
        converted = aggregates.copy()

        # Temperature conversions
        for temp_field in ["t_min", "t_max"]:
            if temp_field in converted:
                unit = source_units.get("temperature", "celsius")
                converted[temp_field] = self._convert_temperature(
                    converted[temp_field], unit, "celsius"
                )

        # Wind speed conversions
        if "wind_speed_avg" in converted:
            unit = source_units.get("wind_speed", "km/h")
            converted["wind_speed_avg"] = self._convert_wind_speed(
                converted["wind_speed_avg"], unit, "km/h"
            )

        # Air pressure conversions
        if "air_pressure_avg" in converted:
            unit = source_units.get("air_pressure", "kPa")
            converted["air_pressure_avg"] = self._convert_pressure(
                converted["air_pressure_avg"], unit, "kPa"
            )

        return converted

    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert temperature between units."""
        if from_unit == to_unit:
            return value

        # Convert to Celsius first
        if from_unit.lower() in ["fahrenheit", "f"]:
            celsius = (value - 32) * 5 / 9
        elif from_unit.lower() in ["kelvin", "k"]:
            celsius = value - 273.15
        else:
            celsius = value

        # Convert from Celsius to target
        if to_unit.lower() in ["fahrenheit", "f"]:
            return celsius * 9 / 5 + 32
        elif to_unit.lower() in ["kelvin", "k"]:
            return celsius + 273.15
        else:
            return celsius

    def _convert_wind_speed(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert wind speed between units."""
        if from_unit == to_unit:
            return value

        # Convert to m/s first
        from_unit_lower = from_unit.lower()
        if from_unit_lower in ["km/h", "kmh", "kph"]:
            ms = value / 3.6
        elif from_unit_lower in ["mph", "mi/h"]:
            ms = value * 0.44704
        elif from_unit_lower in ["knots", "kt"]:
            ms = value * 0.514444
        else:
            ms = value  # Assume m/s

        # Convert from m/s to target
        to_unit_lower = to_unit.lower()
        if to_unit_lower in ["km/h", "kmh", "kph"]:
            return ms * 3.6
        elif to_unit_lower in ["mph", "mi/h"]:
            return ms / 0.44704
        elif to_unit_lower in ["knots", "kt"]:
            return ms / 0.514444
        else:
            return ms

    def _convert_pressure(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert air pressure between units."""
        if from_unit == to_unit:
            return value

        # Convert to kPa first
        from_unit_lower = from_unit.lower()
        if from_unit_lower in ["hpa", "hecto", "hectopascal"]:
            kpa = value / 10
        elif from_unit_lower in ["pa", "pascal"]:
            kpa = value / 1000
        elif from_unit_lower in ["mbar", "millibar"]:
            kpa = value / 10
        elif from_unit_lower in ["atm", "atmosphere"]:
            kpa = value * 101.325
        elif from_unit_lower in ["mmhg", "torr"]:
            kpa = value * 0.133322
        else:
            kpa = value  # Assume kPa

        # Convert from kPa to target
        to_unit_lower = to_unit.lower()
        if to_unit_lower in ["hpa", "hecto", "hectopascal"]:
            return kpa * 10
        elif to_unit_lower in ["pa", "pascal"]:
            return kpa * 1000
        elif to_unit_lower in ["mbar", "millibar"]:
            return kpa * 10
        elif to_unit_lower in ["atm", "atmosphere"]:
            return kpa / 101.325
        elif to_unit_lower in ["mmhg", "torr"]:
            return kpa / 0.133322
        else:
            return kpa

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
