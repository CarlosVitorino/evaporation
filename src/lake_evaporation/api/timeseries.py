"""
Time series operations for KISTERS Web Portal API.

Handles retrieval and updating of time series data.
"""

from typing import List, Dict, Any, Optional


class TimeSeriesAPI:
    """Time series-related API operations."""

    def get_time_series_list(
        self,
        organization_id: str,
        location: Optional[str] = None,
        variable: Optional[str] = None,
        include_location_data: bool = False,
        include_coverage: bool = True,
        include_timezone: bool = False,
        **kwargs
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
        self.logger.info(f"Fetching timeseries for org {organization_id}")  # type: ignore
        endpoint = f"/organizations/{organization_id}/timeSeries"

        params = {}
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

        result = self.get(endpoint, params=params if params else None)  # type: ignore

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
        self.logger.debug(f"Fetching timeseries {timeseries_id}")  # type: ignore
        endpoint = f"/organizations/{organization_id}/timeSeries/{timeseries_id}"

        params = {}
        if include_location_data:
            params["includeLocationData"] = "true"
        if include_coverage:
            params["includeCoverage"] = "true"
        if include_timezone:
            params["includeTimeZone"] = "true"

        return self.get(endpoint, params=params if params else None)  # type: ignore

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
        self.logger.debug(f"Updating timeseries {timeseries_id}")  # type: ignore
        endpoint = f"/organizations/{organization_id}/timeSeries/{timeseries_id}"
        return self.put(endpoint, timeseries_data)  # type: ignore

    def get_time_series_data(
        self,
        time_series_id: str,
        start_date: str,
        end_date: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get time series data for a date range.

        Args:
            time_series_id: Time series ID
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            organization_id: Organization ID (if required by API)

        Returns:
            Time series data
        """
        self.logger.debug(f"Fetching data for time series {time_series_id}")  # type: ignore
        endpoint = f"/timeseries/{time_series_id}/data"
        params = {
            "start": start_date,
            "end": end_date
        }
        return self.get(endpoint, params=params)  # type: ignore

    def write_time_series_value(
        self,
        time_series_id: str,
        timestamp: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write a value to a time series.

        Args:
            time_series_id: Time series ID
            timestamp: Timestamp (ISO format)
            value: Value to write
            metadata: Optional metadata
            organization_id: Organization ID (if required by API)

        Returns:
            Response from API
        """
        self.logger.debug(f"Writing value {value} to time series {time_series_id}")  # type: ignore
        endpoint = f"/timeseries/{time_series_id}/data"
        data = {
            "timestamp": timestamp,
            "value": value,
            "metadata": metadata or {}
        }
        return self.post(endpoint, data)  # type: ignore
