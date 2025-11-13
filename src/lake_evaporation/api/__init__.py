"""
API layer for KISTERS Web Portal.

Provides low-level API client for authentication, organizations, locations, and time series operations.
"""

import os
import logging
from typing import Optional

from .client import APIClient
from .auth import AuthAPI
from .organizations import OrganizationsAPI
from .locations import LocationsAPI
from .timeseries import TimeSeriesAPI
from .raster import RasterAPI
from . import helpers


class KistersAPI(AuthAPI, OrganizationsAPI, LocationsAPI, TimeSeriesAPI, RasterAPI):
    """
    Unified API client for KISTERS Web Portal.

    Combines authentication, organization, location, and time series operations.
    """

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
        Initialize unified API client.

        Args:
            base_url: Base URL for the API
            username: Username for authentication
            email: Email for authentication
            password: Password for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            verify_ssl: Whether to verify SSL certificates
            logger: Logger instance
        """
        super().__init__(
            base_url=base_url,
            username=username,
            email=email,
            password=password,
            timeout=timeout,
            max_retries=max_retries,
            verify_ssl=verify_ssl,
            logger=logger
        )


__all__ = [
    "APIClient",
    "AuthAPI",
    "OrganizationsAPI",
    "LocationsAPI",
    "TimeSeriesAPI",
    "RasterAPI",
    "KistersAPI",
]
