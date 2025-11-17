"""
Time series operations for KISTERS Web Portal API.

Handles retrieval and updating of time series data.
"""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import APIClient


class TimeSeriesAPI:
    """Time series-related API operations."""

    # Type hints for attributes provided by APIClient base class
    logger: logging.Logger

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Method provided by APIClient base class."""
        ...

    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Method provided by APIClient base class."""
        ...

    def get_time_series_list(
        self,
        organization_id: str,
        location: Optional[str] = None,
        variable: Optional[str] = None,
        include_location_data: bool = False,
        include_coverage: bool = True,
        include_timezone: bool = False,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Get organization timeseries list.

        Args:
            organization_id: Organization ID
            location: Filter for specified location ID
            variable: Filter for specified variable
            include_location_data: Include location data in response
            include_coverage: Include timeseries coverage
            include_timezone: Include timezone information
            **kwargs: Additional query parameters

        Returns:
            List of timeseries objects
        """
        self.logger.info(f"Fetching timeseries for org {organization_id}")
        endpoint = f"/organizations/{organization_id}/timeSeries"

        params: Dict[str, Any] = {}
        if location:
            params["location"] = location
        if variable:
            params["variable"] = variable
        if include_location_data:
            params["includeLocationData"] = "true"
        if include_coverage:
            params["includeCoverage"] = "true"
        if include_timezone:
            params["includeTimeZone"] = "true"

        # Add any additional query parameters
        params.update(kwargs)

        result = self.get(endpoint, params=params if params else None)
        # API returns a list
        if isinstance(result, list):
            return result
        return []

    def get_time_series(
        self,
        organization_id: str,
        timeseries_id: str,
        include_location_data: bool = False,
        include_coverage: bool = True,
        include_timezone: bool = False
    ) -> Dict[str, Any]:
        """
        Get organization timeseries by ID.

        Args:
            organization_id: Organization ID
            timeseries_id: Timeseries ID
            include_location_data: Include location data in response
            include_coverage: Include timeseries coverage
            include_timezone: Include timezone information

        Returns:
            Timeseries object
        """
        self.logger.debug(f"Fetching timeseries {timeseries_id}")
        endpoint = f"/organizations/{organization_id}/timeSeries/{timeseries_id}"

        params: Dict[str, Any] = {}
        if include_location_data:
            params["includeLocationData"] = "true"
        if include_coverage:
            params["includeCoverage"] = "true"
        if include_timezone:
            params["includeTimeZone"] = "true"

        return self.get(endpoint, params=params if params else None)

    def update_time_series(
        self,
        organization_id: str,
        timeseries_id: str,
        timeseries_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an organization timeseries.

        Args:
            organization_id: Organization ID
            timeseries_id: Timeseries ID
            timeseries_data: Timeseries data to update

        Returns:
            Updated timeseries object
        """
        self.logger.debug(f"Updating timeseries {timeseries_id}")
        endpoint = f"/organizations/{organization_id}/timeSeries/{timeseries_id}"
        return self.put(endpoint, timeseries_data)

    def get_time_series_data(
        self,
        time_series_id: str,
        start_date: str,
        end_date: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get time series data for a date range.

        Args:
            time_series_id: Time series ID
            start_date: Start date (ISO format: 2025-11-10T00:00:00)
            end_date: End date (ISO format: 2025-11-11T00:00:00)
            organization_id: Organization ID

        Returns:
            Time series data with 'data' array containing timestamp/value pairs
        """
        self.logger.debug(f"Fetching data for time series {time_series_id}")  # type: ignore
        endpoint = f"/organizations/{organization_id}/timeSeries/{time_series_id}/data"
        params = {
            "from": start_date,
            "to": end_date
        }
        return self.get(endpoint, params=params)  # type: ignore

    def write_time_series_value(
        self,
        time_series_id: str,
        timestamp: str,
        value: float,
        organization_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Write a value to a time series.

        Args:
            time_series_id: Time series ID
            timestamp: Timestamp (ISO format)
            value: Value to write
            organization_id: Organization ID
            metadata: Optional metadata

        Returns:
            Response from API
        """
        self.logger.debug(f"Writing value {value} to time series {time_series_id}")  # type: ignore
        endpoint = f"/organizations/{organization_id}/timeSeries/{time_series_id}/data"

        data: Dict[str, Any] = {
            "columns": ["timestamp", "value"],
            "data": [[timestamp, value]]
        }

        return self.put(endpoint, data=data)  # type: ignore
