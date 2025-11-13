"""
Raster time series operations for KISTERS Web Portal API.

Handles retrieval of raster timeseries metadata and point data extraction.
"""

import json
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, quote


class RasterAPI:
    """Mixin for raster time series-related API operations."""

    def get_raster_timeseries_list(
        self,
        datasource_id: int,
        organization_id: Optional[str] = None,
        **kwargs
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
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract raster data at specific geographic points (raster2Point).

        Args:
            datasource_id: Raster datasource ID
            timeseries_id: Raster timeseries ID
            points: List of point coordinates, e.g., [{"lat": 45.5, "lon": 10.8}]
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
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
                start_date="2024-01-01T00:00:00Z",
                end_date="2024-01-02T00:00:00Z"
            )
        """
        self.logger.debug(
            f"Fetching raster point data for timeseries {timeseries_id} at {len(points)} point(s)"
        )  # type: ignore

        # Build query parameters
        # Note: points needs to be JSON-encoded
        params_dict = {
            "extractMode": extract_mode,
            "allModelMembers": str(all_model_members).lower(),
            "from": start_date,
            "until": end_date,
        }

        # Add any additional query parameters
        params_dict.update(kwargs)

        # Encode simple parameters
        query_parts = [f"{k}={quote(str(v))}" for k, v in params_dict.items()]

        # Add points as JSON
        points_json = json.dumps(points)
        query_parts.append(f"points={quote(points_json)}")

        # Build endpoint with query string
        endpoint = f"/raster/datasources/{datasource_id}/timeSeries/{timeseries_id}/points"
        query_string = "&".join(query_parts)
        endpoint = f"{endpoint}?{query_string}"

        return self.get(endpoint, params=None)  # type: ignore
