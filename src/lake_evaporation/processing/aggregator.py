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
                  Each list contains [timestamp, value] pairs or {"timestamp": ..., "value": ...} dicts.

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

        def extract_value(point: Any) -> Optional[float]:
            if isinstance(point, dict):
                return point.get("value")
            elif isinstance(point, (list, tuple)) and len(point) > 1:
                return point[1]
            return None

        if "temperature" in data and data["temperature"]:
            temps = [extract_value(point) for point in data["temperature"]]
            temps = [t for t in temps if t is not None]
            if temps:
                aggregates["t_min"] = min(temps)
                aggregates["t_max"] = max(temps)
                self.logger.debug(f"Temperature: min={aggregates['t_min']:.1f}, max={aggregates['t_max']:.1f}")
            else:
                self.logger.warning("No valid temperature values")

        if "humidity" in data and data["humidity"]:
            rh = [extract_value(point) for point in data["humidity"]]
            rh = [h for h in rh if h is not None]
            if rh:
                aggregates["rh_min"] = min(rh)
                aggregates["rh_max"] = max(rh)
                self.logger.debug(f"Humidity: min={aggregates['rh_min']:.1f}, max={aggregates['rh_max']:.1f}")
            else:
                self.logger.warning("No valid humidity values")

        if "wind_speed" in data and data["wind_speed"]:
            wind = [extract_value(point) for point in data["wind_speed"]]
            wind = [w for w in wind if w is not None]
            if wind:
                aggregates["wind_speed_avg"] = statistics.mean(wind)
                self.logger.debug(f"Wind speed avg: {aggregates['wind_speed_avg']:.2f}")
            else:
                self.logger.warning("No valid wind speed values")

        if "air_pressure" in data and data["air_pressure"]:
            pressure = [extract_value(point) for point in data["air_pressure"]]
            pressure = [p for p in pressure if p is not None]
            if pressure:
                aggregates["air_pressure_avg"] = statistics.mean(pressure)
                self.logger.debug(f"Air pressure avg: {aggregates['air_pressure_avg']:.2f}")
            else:
                self.logger.warning("No valid air pressure values")

        if "sunshine_hours" in data and data["sunshine_hours"]:
            sunshine = [extract_value(point) for point in data["sunshine_hours"]]
            sunshine = [s for s in sunshine if s is not None]
            if sunshine:
                aggregates["sunshine_hours"] = sum(sunshine)
                self.logger.debug(f"Sunshine hours: {aggregates['sunshine_hours']:.2f}")

        return aggregates

    def aggregate_cloud_layers(
        self,
        data: Dict[str, List[List[Any]]],
        actual_units: Dict[str, str]
    ) -> Dict[str, Optional[float]]:
        """
        Aggregate cloud layer data and convert to octas if needed.

        Args:
            data: Raw sensor data dictionary with cloud layer keys
            actual_units: Unit information for each parameter

        Returns:
            Dictionary with cloud layer values in octas
        """
        from ..processing.converter import UnitConverter

        converter = UnitConverter(self.logger)

        def extract_value(point: Any) -> Optional[float]:
            if isinstance(point, dict):
                return point.get("value")
            elif isinstance(point, (list, tuple)) and len(point) > 1:
                return point[1]
            return None

        def get_mean(data_points: List[Any]) -> Optional[float]:
            if not data_points:
                return None
            values = [extract_value(p) for p in data_points]
            values = [v for v in values if v is not None]
            return sum(values) / len(values) if values else None

        result: Dict[str, Optional[float]] = {}

        for layer in ["low_clouds", "medium_clouds", "high_clouds"]:
            raw_value = get_mean(data.get(layer, []))
            if raw_value is not None:
                unit = actual_units.get(layer, "octas")
                octas_key = f"{layer.replace('_clouds', '_cloud_octas')}"
                result[octas_key] = converter.convert_cloud_cover_to_octas(raw_value, unit)
            else:
                octas_key = f"{layer.replace('_clouds', '_cloud_octas')}"
                result[octas_key] = None

        return result
