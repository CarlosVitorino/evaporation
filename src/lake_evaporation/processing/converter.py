"""
Unit conversion module.

Converts between different units for meteorological measurements.
"""

import logging
from typing import Dict, Optional


class UnitConverter:
    """Convert between different meteorological units."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize unit converter.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

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
                converted[temp_field] = self.convert_temperature(
                    converted[temp_field], unit, "celsius"
                )

        # Wind speed conversions
        if "wind_speed_avg" in converted:
            unit = source_units.get("wind_speed", "km/h")
            converted["wind_speed_avg"] = self.convert_wind_speed(
                converted["wind_speed_avg"], unit, "km/h"
            )

        # Air pressure conversions
        if "air_pressure_avg" in converted:
            unit = source_units.get("air_pressure", "kPa")
            converted["air_pressure_avg"] = self.convert_pressure(
                converted["air_pressure_avg"], unit, "kPa"
            )

        return converted

    def convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert temperature between units.

        Args:
            value: Temperature value
            from_unit: Source unit (celsius, fahrenheit, kelvin)
            to_unit: Target unit

        Returns:
            Converted temperature value
        """
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

    def convert_wind_speed(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert wind speed between units.

        Args:
            value: Wind speed value
            from_unit: Source unit (km/h, m/s, mph, knots)
            to_unit: Target unit

        Returns:
            Converted wind speed value
        """
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

    def convert_pressure(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert air pressure between units.

        Args:
            value: Pressure value
            from_unit: Source unit (kPa, hPa, Pa, mbar, atm, mmHg)
            to_unit: Target unit

        Returns:
            Converted pressure value
        """
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
