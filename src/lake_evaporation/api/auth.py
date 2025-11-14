"""
Authentication operations for KISTERS Web Portal API.

Handles login, logout, and session management.
"""

import os
import logging
from typing import Dict, Any, Optional

import requests  # type: ignore

from .client import APIClient


class AuthAPI(APIClient):
    """API client with authentication capabilities."""
   
    logger: logging.Logger

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        verify_ssl: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize API client with authentication.

        Args:
            base_url: Base URL for the API
            username: Username for authentication (alternative to email)
            email: Email for authentication (alternative to username)
            password: Password for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            verify_ssl: Whether to verify SSL certificates
            logger: Logger instance
        """
        super().__init__(base_url, timeout, max_retries, verify_ssl, logger)

        self.username = username or os.getenv("API_USERNAME")
        self.email = email or os.getenv("API_EMAIL")
        self.password = password or os.getenv("API_PASSWORD")

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
        elif self.email:
            credentials["email"] = self.email
        else:
            raise ValueError("Either username or email must be provided for authentication")

        try:
            response = self._make_request(
                "POST",
                "/auth/login",
                skip_auth_check=True,
                json=credentials
            )

            # Extract CSRF token from response headers
            self.csrf_token = response.headers.get("x-csrf-token")
            if not self.csrf_token:
                self.logger.warning("No x-csrf-token received in login response")

            # Store user data
            self.user_data = response.json()
            self.is_authenticated = True

            # Update headers with new CSRF token
            self._update_headers()
            if self.user_data is None:
                self.logger.error("No user data received in login response")
                raise ValueError("No user data received in login response")

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
            # Use internal method for logout (already authenticated)
            self._make_request("POST", "/auth/logout")

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
            # Use internal method for refresh (already authenticated)
            response = self._make_request("POST", "/auth/refresh")

            # Update user data
            self.user_data = response.json()

            # Update CSRF token if provided
            new_token = response.headers.get("x-csrf-token")
            if new_token:
                self.csrf_token = new_token
                self._update_headers()

            if self.user_data is None:
                self.logger.error("No user data received in login response")
                raise ValueError("No user data received in login response")

            self.logger.debug("Session refreshed successfully")
            return self.user_data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Session refresh failed: {e}")
            self.is_authenticated = False
            raise

    def close(self) -> None:
        """Close the session and logout if authenticated."""
        if self.is_authenticated:
            try:
                self.logout()
            except Exception as e:
                self.logger.warning(f"Error during logout: {e}", exc_info=True)
        super().close()
