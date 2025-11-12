"""
Data fetching service for sensor measurements.

Fetches time series data from the API for processing.
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from ..api import KistersAPI


class DataFetcher:
    """Fetch sensor data from time series."""

    def __init__(
        self,
        api_client: "KistersAPI",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize data fetcher.

        Args:
            api_client: API client instance
            logger: Logger instance
        """
        self.api_client = api_client
        self.logger = logger or logging.getLogger(__name__)

        # Lookup maps for timeseries references
        self._path_to_id_map: Dict[str, str] = {}
        self._exchange_id_to_id_map: Dict[str, str] = {}

    def set_timeseries_list(self, timeseries_list: List[Dict[str, Any]]) -> None:
        """
        Set the timeseries list and build lookup maps.

        This allows the data fetcher to resolve tsPath and exchangeId references
        to their corresponding tsId values.

        Args:
            timeseries_list: List of timeseries objects from the API
        """
        self._path_to_id_map.clear()
        self._exchange_id_to_id_map.clear()

        for ts in timeseries_list:
            ts_id = ts.get("id")
            if not ts_id:
                continue

            # Map path to ID
            ts_path = ts.get("path")
            if ts_path:
                self._path_to_id_map[ts_path] = ts_id

            # Map exchangeId to ID
            exchange_id = ts.get("exchangeId")
            if exchange_id:
                self._exchange_id_to_id_map[exchange_id] = ts_id

        self.logger.info(
            f"Built lookup maps: {len(self._path_to_id_map)} paths, "
            f"{len(self._exchange_id_to_id_map)} exchange IDs"
        )

    def fetch_time_series_data(
        self,
        time_series_ref: str,
        start_date: datetime,
        end_date: datetime,
        organization_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch data for a time series reference.

        Args:
            time_series_ref: Time series reference (tsId, tsPath, or exchangeId)
            start_date: Start date for data fetch
            end_date: End date for data fetch
            organization_id: Organization ID

        Returns:
            List of data points with timestamps and values
        """
        self.logger.debug(f"Fetching data for {time_series_ref}")

        try:
            # Extract actual time series ID from reference
            ts_id = self._parse_time_series_reference(time_series_ref)

            # Format dates as ISO strings (KISTERS expects this format)
            start_iso = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            end_iso = end_date.strftime("%Y-%m-%dT%H:%M:%S")

            # Fetch data from API
            data = self.api_client.get_time_series_data(
                time_series_id=ts_id,
                start_date=start_iso,
                end_date=end_iso,
                organization_id=organization_id
            )

            # Extract data points from response
            # API may return: {"data": [...]} or just [...]
            if isinstance(data, dict):
                data_points = data.get("data", [])
            elif isinstance(data, list):
                data_points = data
            else:
                self.logger.warning(f"Unexpected data format: {type(data)}")
                data_points = []

            self.logger.debug(f"Retrieved {len(data_points)} data points")
            return data_points

        except Exception as e:
            self.logger.error(f"Failed to fetch data for {time_series_ref}: {e}")
            return []

    def _parse_time_series_reference(self, reference: str) -> str:
        """
        Parse time series reference to extract ID.

        Supports formats:
        - tsId(123) - Returns the ID directly
        - tsPath(/path/to/series) - Looks up the ID from path
        - exchangeId(abc123) - Looks up the ID from exchange ID
        - Direct ID: 123 - Returns as-is

        Args:
            reference: Time series reference string

        Returns:
            Extracted time series ID

        Raises:
            ValueError: If reference is empty, invalid, or not found in lookup maps
        """
        if not reference:
            raise ValueError("Empty time series reference")

        # Check for function-style references
        if "(" in reference and ")" in reference:
            # Extract the type and value
            ref_type = reference[:reference.index("(")].strip()
            start = reference.index("(") + 1
            end = reference.index(")")
            ref_value = reference[start:end]

            # Handle different reference types
            if ref_type == "tsId":
                # Direct ID - return as is
                return ref_value

            elif ref_type == "tsPath":
                # Look up ID by path
                if ref_value in self._path_to_id_map:
                    ts_id = self._path_to_id_map[ref_value]
                    self.logger.debug(f"Resolved tsPath({ref_value}) to tsId {ts_id}")
                    return ts_id
                else:
                    raise ValueError(
                        f"tsPath '{ref_value}' not found in timeseries list. "
                        f"Make sure to call set_timeseries_list() before fetching data."
                    )

            elif ref_type == "exchangeId":
                # Look up ID by exchange ID
                if ref_value in self._exchange_id_to_id_map:
                    ts_id = self._exchange_id_to_id_map[ref_value]
                    self.logger.debug(f"Resolved exchangeId({ref_value}) to tsId {ts_id}")
                    return ts_id
                else:
                    raise ValueError(
                        f"exchangeId '{ref_value}' not found in timeseries list. "
                        f"Make sure to call set_timeseries_list() before fetching data."
                    )

            else:
                # Unknown reference type - return the value
                self.logger.warning(f"Unknown reference type '{ref_type}', using value as-is")
                return ref_value

        # Assume it's a direct ID
        return reference

    def fetch_daily_data(
        self,
        location_metadata: Dict[str, Any],
        target_date: datetime
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all required sensor data for a specific day.

        Args:
            location_metadata: Location metadata with time series references
                             and organization_id
            target_date: Date to fetch data for

        Returns:
            Dictionary with data for each sensor type
        """
        self.logger.info(f"Fetching daily data for {target_date.date()}")

        # Get organization ID from metadata
        organization_id = location_metadata.get("organization_id")

        if not organization_id:
            self.logger.error("Organization ID is missing in location metadata")
            raise ValueError("Organization ID is required")

        # Define date range (full day)
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        # End date should be end of day (23:59:59)
        end_date = start_date.replace(hour=23, minute=59, second=59)

        # Fetch data for each required time series
        data = {}

        # Temperature
        if location_metadata.get("temperature_ts"):
            data["temperature"] = self.fetch_time_series_data(
                location_metadata["temperature_ts"],
                start_date,
                end_date,
                organization_id
            )

        # Humidity
        if location_metadata.get("humidity_ts"):
            data["humidity"] = self.fetch_time_series_data(
                location_metadata["humidity_ts"],
                start_date,
                end_date,
                organization_id
            )

        # Wind speed
        if location_metadata.get("wind_speed_ts"):
            data["wind_speed"] = self.fetch_time_series_data(
                location_metadata["wind_speed_ts"],
                start_date,
                end_date,
                organization_id
            )

        # Air pressure
        if location_metadata.get("air_pressure_ts"):
            data["air_pressure"] = self.fetch_time_series_data(
                location_metadata["air_pressure_ts"],
                start_date,
                end_date,
                organization_id
            )

        # Sunshine hours (optional)
        if location_metadata.get("sunshine_hours_ts"):
            data["sunshine_hours"] = self.fetch_time_series_data(
                location_metadata["sunshine_hours_ts"],
                start_date,
                end_date,
                organization_id
            )

        # Global radiation (optional, for calculating sunshine hours)
        if location_metadata.get("global_radiation_ts"):
            data["global_radiation"] = self.fetch_time_series_data(
                location_metadata["global_radiation_ts"],
                start_date,
                end_date,
                organization_id
            )

        # Log data availability
        for sensor_type, sensor_data in data.items():
            if sensor_data:
                self.logger.info(f"  {sensor_type}: {len(sensor_data)} data points")
            else:
                self.logger.warning(f"  {sensor_type}: No data available")

        return data

    def check_data_completeness(
        self,
        data: Dict[str, List[Dict[str, Any]]],
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
