"""
API layer for KISTERS Web Portal.

Provides a unified client for authentication, locations, time series operations,
and higher-level services for data fetching, discovery, and writing.
"""

import os
import logging
from typing import Optional

from .client import APIClient
from .auth import AuthAPI
from .locations import LocationsAPI
from .timeseries import TimeSeriesAPI
from . import helpers
from .discovery import TimeSeriesDiscovery
from .data_fetcher import DataFetcher
from .writer import DataWriter


class KistersAPI(AuthAPI, LocationsAPI, TimeSeriesAPI):
    """
    Unified API client for KISTERS Web Portal.

    Combines authentication, location, and time series operations.
    """

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
        Initialize unified API client.

        Args:
            base_url: Base URL for the API
            username: Username for authentication
            email: Email for authentication
            password: Password for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            logger: Logger instance
        """
        super().__init__(
            base_url=base_url,
            username=username,
            email=email,
            password=password,
            timeout=timeout,
            max_retries=max_retries,
            logger=logger
        )


__all__ = [
    "APIClient",
    "AuthAPI",
    "LocationsAPI",
    "TimeSeriesAPI",
    "KistersAPI",
    "TimeSeriesDiscovery",
    "DataFetcher",
    "DataWriter",
    "helpers",
]
