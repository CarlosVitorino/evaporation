"""
API client for datasphere REST API with JWT authentication.

Handles API requests, authentication, and error handling.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIClient:
    """Client for interacting with datasphere REST API."""

    def __init__(
        self,
        base_url: str,
        jwt_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL for the API
            jwt_token: JWT authentication token. If None, uses API_JWT_TOKEN env var
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            logger: Logger instance
        """
        self.base_url = base_url.rstrip("/")
        self.jwt_token = jwt_token or os.getenv("API_JWT_TOKEN")
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

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
        """Update session headers with authentication."""
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.jwt_token}"
        })

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

    def get_organizations(self) -> List[Dict[str, Any]]:
        """
        Get list of all organizations.

        Returns:
            List of organization objects
        """
        self.logger.info("Fetching organizations")
        return self.get("/api/organizations")

    def get_time_series_by_tag(
        self,
        organization_id: str,
        tag: str
    ) -> List[Dict[str, Any]]:
        """
        Get time series filtered by tag.

        Args:
            organization_id: Organization ID
            tag: Tag to filter by

        Returns:
            List of time series objects
        """
        self.logger.info(f"Fetching time series for org {organization_id} with tag '{tag}'")
        endpoint = f"/api/organizations/{organization_id}/timeseries"
        params = {"tag": tag}
        return self.get(endpoint, params=params)

    def get_time_series_data(
        self,
        time_series_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get time series data for a date range.

        Args:
            time_series_id: Time series ID
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            Time series data
        """
        self.logger.debug(f"Fetching data for time series {time_series_id}")
        endpoint = f"/api/timeseries/{time_series_id}/data"
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
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Write a value to a time series.

        Args:
            time_series_id: Time series ID
            timestamp: Timestamp (ISO format)
            value: Value to write
            metadata: Optional metadata

        Returns:
            Response from API
        """
        self.logger.debug(f"Writing value {value} to time series {time_series_id}")
        endpoint = f"/api/timeseries/{time_series_id}/data"
        data = {
            "timestamp": timestamp,
            "value": value,
            "metadata": metadata or {}
        }
        return self.post(endpoint, data)

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
