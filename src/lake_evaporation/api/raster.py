"""
Raster time series operations for KISTERS Web Portal API.

Handles retrieval of raster timeseries metadata and point data extraction.
"""

import json
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from urllib.parse import urlencode, quote

if TYPE_CHECKING:
    from .client import APIClient


class RasterAPI:
    """Mixin for raster time series-related API operations."""

    # Type hints for attributes provided by APIClient base class
    logger: logging.Logger

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Method provided by APIClient base class."""
        ...

    def get_raster_timeseries_list(
        self,
        datasource_id: int,
        organization_id: Optional[str] = None,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Get list of available raster timeseries for a datasource.

        Args:
            datasource_id: Raster datasource ID
            organization_id: Organization ID (optional)
            **kwargs: Additional query parameters

        Returns:
            List of raster timeseries objects with metadata

        Example response item:
            {
                "timeseriesId": "5b80141d-5843-445f-9249-66c2c6741052",
                "path": "/gfs/PRMSL",
                "name": "PRMSL",
                "unitSymbol": "Pa",
                "parameterKey": "Pressure",
                "coverage": {...},
                "boundingBox": {...},
                ...
            }
        """
        self.logger.info(f"Fetching raster timeseries list for datasource {datasource_id}")  # type: ignore

        params = {}
        if organization_id:
            params["orgId"] = organization_id

        # Add any additional query parameters
        params.update(kwargs)

        # Build endpoint with query string
        endpoint = f"/raster/datasources/{datasource_id}/timeSeries"
        if params:
            query_string = urlencode(params)
            endpoint = f"{endpoint}?{query_string}"

        result = self.get(endpoint, params=None)  # type: ignore

        # API returns a list
        if isinstance(result, list):
            return result
        return []

    def get_raster_point_data(
        self,
        datasource_id: int,
        timeseries_id: str,
        points: List[Dict[str, float]],
        start_date: str,
        end_date: str,
        extract_mode: str = "strict",
        all_model_members: bool = True,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Extract raster data at specific geographic points (raster2Point).

        Args:
            datasource_id: Raster datasource ID
            timeseries_id: Raster timeseries ID
            points: List of point coordinates, e.g., [{"lat": 45.5, "lon": 10.8}]
            start_date: Start date in ISO format with timezone (e.g., "2024-01-01T00:00:00.000Z")
            end_date: End date in ISO format with timezone (e.g., "2024-01-02T23:59:59.999Z")
            extract_mode: Extraction mode (default: "strict")
            all_model_members: Include all model members (default: True)
            **kwargs: Additional query parameters

        Returns:
            Raster point data response

        Example:
            points = [{"lat": 45.5, "lon": 10.8}]
            data = api.get_raster_point_data(
                datasource_id=1,
                timeseries_id="5b80141d-5843-445f-9249-66c2c6741052",
                points=points,
                start_date="2024-01-01T00:00:00.000Z",
                end_date="2024-01-02T23:59:59.999Z"
            )
        """
        self.logger.debug(
            f"Fetching raster point data for timeseries {timeseries_id} at {len(points)} point(s)"
        )  # type: ignore

        # Validate that dates include timezone information
        if not (start_date.endswith('Z') or '+' in start_date or start_date.count('-') > 2):
            raise ValueError(
                f"start_date must include timezone information (e.g., '2024-01-01T00:00:00.000Z'). "
                f"Got: {start_date}"
            )
        if not (end_date.endswith('Z') or '+' in end_date or end_date.count('-') > 2):
            raise ValueError(
                f"end_date must include timezone information (e.g., '2024-01-02T23:59:59.999Z'). "
                f"Got: {end_date}"
            )

        # Format points as comma-separated lon,lat pairs
        # Note: API expects lon,lat order (not lat,lon)
        points_str = ",".join([f"{p['lon']},{p['lat']}" for p in points])

        # Build query parameters
        params_dict = {
            #"extractMode": extract_mode,
            "points": points_str,
            #"allModelMembers": str(all_model_members).lower(),
            "from": start_date,
            "until": end_date,
        }

        # Add any additional query parameters
        params_dict.update(kwargs)

        # Build endpoint with query string
        endpoint = f"/raster/datasources/{datasource_id}/timeSeries/{timeseries_id}/points"
        query_string = urlencode(params_dict)
        endpoint = f"{endpoint}?{query_string}"

        return self.get(endpoint, params=None)  # type: ignore
