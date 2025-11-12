"""
Data aggregation module.

Calculates daily aggregates from raw sensor measurements.
"""

import logging
import statistics
from typing import Dict, Any, List, Optional


class DataAggregator:
    """Calculate daily aggregates from sensor data."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize data aggregator.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def calculate_daily_aggregates(
        self,
        data: Dict[str, List[List[Any]]]
    ) -> Dict[str, float]:
        """
        Calculate daily aggregates from raw sensor data.

        Args:
            data: Dictionary with sensor data lists.
                  Each list contains [timestamp, value] pairs.

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

        # Temperature aggregates - data points are [timestamp, value]
        if "temperature" in data and data["temperature"]:
            temps = [point[1] for point in data["temperature"] if len(point) > 1 and point[1] is not None]
            if temps:
                aggregates["t_min"] = min(temps)
                aggregates["t_max"] = max(temps)
                self.logger.debug(f"Temperature: min={aggregates['t_min']:.1f}, max={aggregates['t_max']:.1f}")
            else:
                self.logger.warning("No valid temperature values")

        # Humidity aggregates
        if "humidity" in data and data["humidity"]:
            rh = [point[1] for point in data["humidity"] if len(point) > 1 and point[1] is not None]
            if rh:
                aggregates["rh_min"] = min(rh)
                aggregates["rh_max"] = max(rh)
                self.logger.debug(f"Humidity: min={aggregates['rh_min']:.1f}, max={aggregates['rh_max']:.1f}")
            else:
                self.logger.warning("No valid humidity values")

        # Wind speed average
        if "wind_speed" in data and data["wind_speed"]:
            wind = [point[1] for point in data["wind_speed"] if len(point) > 1 and point[1] is not None]
            if wind:
                aggregates["wind_speed_avg"] = statistics.mean(wind)
                self.logger.debug(f"Wind speed avg: {aggregates['wind_speed_avg']:.2f}")
            else:
                self.logger.warning("No valid wind speed values")

        # Air pressure average
        if "air_pressure" in data and data["air_pressure"]:
            pressure = [point[1] for point in data["air_pressure"] if len(point) > 1 and point[1] is not None]
            if pressure:
                aggregates["air_pressure_avg"] = statistics.mean(pressure)
                self.logger.debug(f"Air pressure avg: {aggregates['air_pressure_avg']:.2f}")
            else:
                self.logger.warning("No valid air pressure values")

        # Sunshine hours (if directly measured)
        if "sunshine_hours" in data and data["sunshine_hours"]:
            sunshine = [point[1] for point in data["sunshine_hours"] if len(point) > 1 and point[1] is not None]
            if sunshine:
                # Sum for total daily sunshine hours
                aggregates["sunshine_hours"] = sum(sunshine)
                self.logger.debug(f"Sunshine hours: {aggregates['sunshine_hours']:.2f}")

        return aggregates
