"""
Data processing module for lake evaporation system.

Provides aggregation, unit conversion, and validation of sensor data.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from .aggregator import DataAggregator
from .converter import UnitConverter
from .validator import DataValidator


class DataProcessor:
    """
    Unified data processor combining aggregation, conversion, and validation.

    This class provides a convenient interface to all processing operations.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize data processor.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.aggregator = DataAggregator(logger)
        self.converter = UnitConverter(logger)
        self.validator = DataValidator(logger)

    def calculate_daily_aggregates(
        self,
        data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, float]:
        """
        Calculate daily aggregates from raw sensor data.

        Args:
            data: Dictionary with sensor data lists

        Returns:
            Dictionary with aggregated values
        """
        return self.aggregator.calculate_daily_aggregates(data)

    def convert_units(
        self,
        aggregates: Dict[str, float],
        source_units: Dict[str, str]
    ) -> Dict[str, float]:
        """
        Convert aggregated values to required units.

        Args:
            aggregates: Dictionary with aggregated values
            source_units: Dictionary mapping field names to their source units

        Returns:
            Dictionary with converted values
        """
        return self.converter.convert_units(aggregates, source_units)

    def validate_aggregates(self, aggregates: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Validate that all required aggregates are present and in valid ranges.

        Args:
            aggregates: Dictionary with aggregated values

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return self.validator.validate_aggregates(aggregates)

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
        return self.validator.check_data_completeness(data, required_fields)


__all__ = [
    "DataAggregator",
    "UnitConverter",
    "DataValidator",
    "DataProcessor",
]
