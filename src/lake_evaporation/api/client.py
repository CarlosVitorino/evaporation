"""
Base API client for KISTERS Web Portal API.

Handles HTTP requests, session management, and error handling.
"""

import logging
from typing import Dict, Any, Optional

import requests  # type: ignore
from requests.adapters import HTTPAdapter  # type: ignore
from urllib3.util.retry import Retry  # type: ignore


class APIClient:
    """Base client for interacting with KISTERS Web Portal API."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        verify_ssl: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            logger: Logger instance
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.verify_ssl = verify_ssl

        # Session state
        self.csrf_token: Optional[str] = None
        self.user_data: Optional[Dict[str, Any]] = None
        self.is_authenticated = False

        # Disable SSL warnings when verify_ssl is False
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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

    def _make_request(
        self,
        method: str,
        endpoint: str,
        skip_auth_check: bool = False,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request to API.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint (without base URL)
            skip_auth_check: Skip authentication check (for auth endpoints)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        # Ensure we're authenticated for non-auth endpoints
        if not skip_auth_check and not endpoint.startswith("/auth") and not self.is_authenticated:
            raise RuntimeError("Not authenticated. Call login() first.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs.setdefault('verify', self.verify_ssl)

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

    def post(self, endpoint: str, data: Dict[str, Any], skip_auth_check: bool = False) -> Dict[str, Any]:
        """
        Make POST request.

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            JSON response as dictionary
        """
        response = self._make_request("POST", endpoint, json=data, skip_auth_check=skip_auth_check)
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

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
