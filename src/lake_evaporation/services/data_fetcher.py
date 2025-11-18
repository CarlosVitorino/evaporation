"""
Data fetching service for sensor measurements.

Fetches time series data from the API for processing.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
from datetime import datetime, timezone

from .raster_fetcher import RasterDataFetcher
from ..core import DateUtils

if TYPE_CHECKING:
    from ..api import KistersAPI
    from ..core.config import Config


class DataFetcher:
    """Fetch sensor data from time series."""

    def __init__(
        self,
        api_client: "KistersAPI",
        config: Optional["Config"] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize data fetcher.

        Args:
            api_client: API client instance
            config: Configuration object (for raster fallback)
            logger: Logger instance
        """
        self.api_client = api_client
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.date_utils = DateUtils(logger)

        # Lookup maps for timeseries references
        self._path_to_id_map: Dict[str, str] = {}
        self._exchange_id_to_id_map: Dict[str, str] = {}
        self._id_to_unit_map: Dict[str, str] = {}

        # Raster data fetcher (for fallback)
        self.raster_fetcher: Optional[RasterDataFetcher] = None
        if config and config.raster_enabled:
            self.raster_fetcher = RasterDataFetcher(api_client, config, logger)

    def set_timeseries_list(self, timeseries_list: List[Dict[str, Any]]) -> None:
        """
        Set the timeseries list and build lookup maps.

        This allows the data fetcher to resolve tsPath and exchangeId references
        to their corresponding tsId values, and to retrieve unit information.

        Args:
            timeseries_list: List of timeseries objects from the API
        """
        self._path_to_id_map.clear()
        self._exchange_id_to_id_map.clear()
        self._id_to_unit_map.clear()

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

            # Map ID to unit
            unit = ts.get("unit")
            if unit:
                self._id_to_unit_map[ts_id] = unit

        self.logger.info(
            f"Built lookup maps: {len(self._path_to_id_map)} paths, "
            f"{len(self._exchange_id_to_id_map)} exchange IDs, "
            f"{len(self._id_to_unit_map)} units"
        )

    def fetch_time_series_data(
        self,
        time_series_ref: str,
        start_date: datetime,
        end_date: datetime,
        organization_id: str
    ) -> List[List[Any]]:
        """
        Fetch data for a time series reference.

        Args:
            time_series_ref: Time series reference (tsId, tsPath, or exchangeId)
            start_date: Start date for data fetch (timezone-aware)
            end_date: End date for data fetch (timezone-aware)
            organization_id: Organization ID

        Returns:
            List of data points with timestamps and values
        """
        self.logger.debug(f"Fetching data for {time_series_ref}")

        try:
            # Extract actual time series ID from reference
            ts_id = self._parse_time_series_reference(time_series_ref)

            # Convert to ISO format with timezone
            start_iso = self.date_utils.to_iso_with_timezone(start_date)
            end_iso = self.date_utils.to_iso_with_timezone(end_date)

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

        except ValueError as e:
            self.logger.error(f"Invalid time series reference {time_series_ref}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {time_series_ref}: {e}", exc_info=True)
            return []

    def get_timeseries_unit(self, reference: str) -> Optional[str]:
        """
        Get the unit for a time series reference.

        Args:
            reference: Time series reference string (tsId, tsPath, or exchangeId)

        Returns:
            Unit string if found, None otherwise
        """
        try:
            ts_id = self._parse_time_series_reference(reference)
            return self._id_to_unit_map.get(ts_id)
        except Exception as e:
            self.logger.warning(f"Could not get unit for {reference}: {e}")
            return None

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
    ) -> Tuple[Dict[str, List[List[Any]]], Dict[str, str]]:
        """
        Fetch all required sensor data for a specific day.

        Args:
            location_metadata: Location metadata with time series references and organization timezone
            target_date: Date to fetch data for (can be naive or aware)

        Returns:
            Tuple of (data dictionary, units dictionary)
        """
        organization_id = location_metadata.get("organization_id")
        if not organization_id:
            raise ValueError("Organization ID is required")

        # Get organization timezone
        org_timezone = location_metadata.get("organization_timezone", "UTC")
        self.logger.info(f"Fetching daily data for {target_date.date()} in timezone {org_timezone}")

        # Get full day range in the organization's timezone
        start_date, end_date = self.date_utils.get_day_range(target_date, org_timezone)

        self.logger.info(
            f"Date range: {start_date.isoformat()} to {end_date.isoformat()}"
        )

        # Fetch all sensor data from timeseries
        data, units = self._fetch_all_sensors(
            location_metadata, start_date, end_date, organization_id
        )

        # Apply raster fallback if needed
        data, units = self._apply_raster_fallback_if_needed(
            data, units, location_metadata, start_date, end_date, organization_id
        )

        # Log data availability
        self._log_data_availability(data, units)

        return data, units

    def _fetch_all_sensors(
        self,
        location_metadata: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        organization_id: str
    ) -> Tuple[Dict[str, List[List[Any]]], Dict[str, str]]:
        """
        Fetch data from all sensor timeseries.

        Args:
            location_metadata: Location metadata
            start_date: Start date
            end_date: End date
            organization_id: Organization ID

        Returns:
            Tuple of (data, units)
        """
        data: Dict[str, List[List[Any]]] = {}
        units: Dict[str, str] = {}

        # Define sensor mappings
        sensor_mappings = [
            ("temperature_ts", "temperature"),
            ("humidity_ts", "humidity"),
            ("wind_speed_ts", "wind_speed"),
            ("air_pressure_ts", "air_pressure"),
            ("sunshine_hours_ts", "sunshine_hours"),
            ("global_radiation_ts", "global_radiation"),
        ]

        # Fetch each sensor
        for metadata_key, data_key in sensor_mappings:
            ts_ref = location_metadata.get(metadata_key)
            if ts_ref:
                data[data_key] = self.fetch_time_series_data(
                    ts_ref, start_date, end_date, organization_id
                )
                unit = self.get_timeseries_unit(ts_ref)
                if unit:
                    units[data_key] = unit

        return data, units

    def _apply_raster_fallback_if_needed(
        self,
        data: Dict[str, List[List[Any]]],
        units: Dict[str, str],
        location_metadata: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        organization_id: str
    ) -> Tuple[Dict[str, List[List[Any]]], Dict[str, str]]:
        """
        Apply raster fallback for missing required parameters.

        Args:
            data: Current data
            units: Current units
            location_metadata: Location metadata
            start_date: Start date
            end_date: End date
            organization_id: Organization ID

        Returns:
            Updated (data, units) tuple
        """
        if not self._should_use_raster_fallback():
            return data, units

        # Check for missing required parameters
        required_params = ["temperature", "humidity", "wind_speed", "air_pressure", "sunshine_hours", "global_radiation"]
        missing_params = [
            param for param in required_params
            if param not in data or not data.get(param)
        ]

        if not missing_params:
            return data, units

        self.logger.info(
            f"Missing required parameters: {', '.join(missing_params)}. "
            f"Attempting raster fallback..."
        )

        # Get location coordinates
        location = location_metadata.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is None or longitude is None:
            self.logger.warning(
                "Cannot use raster fallback: location coordinates not available"
            )
            return data, units

        # Fetch from raster
        return self._fetch_raster_fallback(
            data, units, missing_params, latitude, longitude,
            start_date, end_date, organization_id
        )

    def _should_use_raster_fallback(self) -> bool:
        """Check if raster fallback should be used."""
        return (
            self.raster_fetcher is not None and
            self.config is not None and
            self.config.raster_use_as_fallback
        )

    def _fetch_raster_fallback(
        self,
        data: Dict[str, List[List[Any]]],
        units: Dict[str, str],
        missing_params: List[str],
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
        organization_id: str
    ) -> Tuple[Dict[str, List[List[Any]]], Dict[str, str]]:
        """
        Fetch missing data from raster source.

        Args:
            data: Current data
            units: Current units
            missing_params: List of missing parameters
            latitude: Location latitude
            longitude: Location longitude
            start_date: Start date
            end_date: End date
            organization_id: Organization ID

        Returns:
            Updated (data, units) tuple
        """
        try:
            # Type assertion: we know raster_fetcher is not None here
            assert self.raster_fetcher is not None

            raster_data, raster_units = self.raster_fetcher.fetch_raster_data_for_location(
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
                organization_id=organization_id
            )

            # Fill in missing data
            for param in missing_params:
                if param in raster_data and raster_data[param]:
                    data[param] = raster_data[param]
                    if param in raster_units:
                        units[param] = raster_units[param]
                else:
                    self.logger.warning(
                        f"  {param}: No data available even from raster fallback"
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to fetch raster fallback data: {e}",
                exc_info=True
            )

        return data, units

    def _log_data_availability(
        self,
        data: Dict[str, List[List[Any]]],
        units: Dict[str, str]
    ) -> None:
        """
        Log data availability for each sensor.

        Args:
            data: Sensor data
            units: Sensor units
        """
        for sensor_type, sensor_data in data.items():
            if sensor_data:
                unit_info = f" (unit: {units[sensor_type]})" if sensor_type in units else ""
                self.logger.info(
                    f"  {sensor_type}: {len(sensor_data)} data points{unit_info}"
                )
            else:
                self.logger.warning(f"  {sensor_type}: No data available")

    def check_data_completeness(
        self,
        data: Dict[str, List[List[Any]]],
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
