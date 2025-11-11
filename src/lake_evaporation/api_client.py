"""
API client for KISTERS Web Portal API with x-csrf-token authentication.

Handles API requests, session-based authentication, and error handling.
"""

import os
import logging
from typing import Dict, Any, Optional, List

import requests  # type: ignore
from requests.adapters import HTTPAdapter  # type: ignore
from urllib3.util.retry import Retry  # type: ignore


class APIClient:
    """Client for interacting with KISTERS Web Portal API."""

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL for the API
            username: Username for authentication (alternative to email)
            email: Email for authentication (alternative to username)
            password: Password for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            logger: Logger instance
        """
        self.base_url = base_url.rstrip("/")
        self.username = username or os.getenv("API_USERNAME")
        self.email = email or os.getenv("API_EMAIL")
        self.password = password or os.getenv("API_PASSWORD")
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

        # Session state
        self.csrf_token: Optional[str] = None
        self.user_data: Optional[Dict[str, Any]] = None
        self.is_authenticated = False

        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self._update_headers()

    def _update_headers(self) -> None:
        """Update session headers with authentication token."""
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        if self.csrf_token:
            self.session.headers.update({
                "x-csrf-token": self.csrf_token
            })

    def login(self) -> Dict[str, Any]:
        """
        Login to the portal with credentials.

        Returns:
            User data from successful login

        Raises:
            requests.exceptions.RequestException: On login failure
        """
        self.logger.info("Logging in to KISTERS Web Portal")

        if not self.password:
            raise ValueError("Password is required for authentication")

        if not self.username and not self.email:
            raise ValueError("Either username or email is required for authentication")

        # Prepare credentials
        credentials = {
            "password": self.password
        }

        if self.username:
            credentials["userName"] = self.username
        else:
            credentials["email"] = self.email

        try:
            url = f"{self.base_url}/auth/login"
            self.logger.debug(f"POST {url}")

            response = self.session.post(
                url,
                json=credentials,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Extract CSRF token from response headers
            self.csrf_token = response.headers.get("x-csrf-token")
            if not self.csrf_token:
                self.logger.warning("No x-csrf-token received in login response")

            # Store user data
            self.user_data = response.json()
            self.is_authenticated = True

            # Update headers with new CSRF token
            self._update_headers()

            self.logger.info(f"Successfully logged in as {self.user_data.get('userName', 'unknown')}")
            return self.user_data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Login failed: {e}")
            self.is_authenticated = False
            raise

    def logout(self) -> None:
        """
        Logout from the portal and destroy the session.

        Raises:
            requests.exceptions.RequestException: On logout failure
        """
        if not self.is_authenticated:
            self.logger.warning("Not authenticated, skipping logout")
            return

        self.logger.info("Logging out from KISTERS Web Portal")

        try:
            url = f"{self.base_url}/auth/logout"
            response = self.session.post(url, timeout=self.timeout)
            response.raise_for_status()

            self.is_authenticated = False
            self.csrf_token = None
            self.user_data = None

            self.logger.info("Successfully logged out")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Logout failed: {e}")
            raise

    def refresh(self) -> Dict[str, Any]:
        """
        Refresh the session and extend token expiry.

        Returns:
            Updated user data

        Raises:
            requests.exceptions.RequestException: On refresh failure
        """
        if not self.is_authenticated:
            raise RuntimeError("Not authenticated, cannot refresh session")

        self.logger.debug("Refreshing session")

        try:
            url = f"{self.base_url}/auth/refresh"
            response = self.session.post(url, timeout=self.timeout)
            response.raise_for_status()

            # Update user data
            self.user_data = response.json()

            # Update CSRF token if provided
            new_token = response.headers.get("x-csrf-token")
            if new_token:
                self.csrf_token = new_token
                self._update_headers()

            self.logger.debug("Session refreshed successfully")
            return self.user_data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Session refresh failed: {e}")
            self.is_authenticated = False
            raise

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request to API.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        # Ensure we're authenticated for non-auth endpoints
        if not endpoint.startswith("/auth") and not self.is_authenticated:
            raise RuntimeError("Not authenticated. Call login() first.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.debug(f"{method} {url}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {method} {url} - {e}")
            raise

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        response = self._make_request("GET", endpoint, params=params)
        return response.json()

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make POST request.

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            JSON response as dictionary
        """
        response = self._make_request("POST", endpoint, json=data)
        return response.json()

    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make PUT request.

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            JSON response as dictionary
        """
        response = self._make_request("PUT", endpoint, json=data)
        return response.json()

    def get_locations(
        self,
        organization_id: str,
        name: Optional[str] = None,
        tags: Optional[str] = None,
        include_geometry: bool = False,
        include_geometry_ids: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get organization locations list.

        Args:
            organization_id: Organization ID
            name: Filter locations by name
            tags: Filter locations by tags
            include_geometry: Add location geometry
            include_geometry_ids: Add location geometry IDs
            **kwargs: Additional query parameters

        Returns:
            List of location objects
        """
        self.logger.info(f"Fetching locations for org {organization_id}")
        endpoint = f"/organizations/{organization_id}/locations"

        params = {}
        if name:
            params["name"] = name
        if tags:
            params["tags"] = tags
        if include_geometry:
            params["includeGeometry"] = "true"
        if include_geometry_ids:
            params["includeGeometryIds"] = "true"

        # Add any additional query parameters
        params.update(kwargs)

        result = self.get(endpoint, params=params if params else None)

        # API returns a list or dict with locations
        if isinstance(result, list):
            return result
        return result.get("locations", [])

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
        self.logger.info(f"Fetching timeseries for org {organization_id}")
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

        params = {}
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
            timeseries_data: Timeseries data to update (OrganizationTimeseriesDTO)

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
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get time series data for a date range.

        Note: This method may need to be updated based on the actual
        data retrieval endpoint in the KISTERS API.

        Args:
            time_series_id: Time series ID
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            organization_id: Organization ID (if required by API)

        Returns:
            Time series data
        """
        self.logger.debug(f"Fetching data for time series {time_series_id}")
        # TODO: Update this endpoint based on actual KISTERS API documentation
        # This is a placeholder that may need adjustment
        endpoint = f"/timeseries/{time_series_id}/data"
        params = {
            "start": start_date,
            "end": end_date
        }
        return self.get(endpoint, params=params)

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

        Note: This method may need to be updated based on the actual
        data writing endpoint in the KISTERS API.

        Args:
            time_series_id: Time series ID
            timestamp: Timestamp (ISO format)
            value: Value to write
            metadata: Optional metadata
            organization_id: Organization ID (if required by API)

        Returns:
            Response from API
        """
        self.logger.debug(f"Writing value {value} to time series {time_series_id}")
        # TODO: Update this endpoint based on actual KISTERS API documentation
        # This is a placeholder that may need adjustment
        endpoint = f"/timeseries/{time_series_id}/data"
        data = {
            "timestamp": timestamp,
            "value": value,
            "metadata": metadata or {}
        }
        return self.post(endpoint, data)

    def close(self) -> None:
        """Close the session and logout if authenticated."""
        if self.is_authenticated:
            try:
                self.logout()
            except Exception as e:
                self.logger.warning(f"Error during logout: {e}")
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
