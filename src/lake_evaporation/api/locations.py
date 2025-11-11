"""
Location operations for KISTERS Web Portal API.

Handles retrieval of organization locations.
"""

from typing import List, Dict, Any, Optional


class LocationsAPI:
    """Mixin for location-related API operations."""

    def get_organizations(self) -> List[Dict[str, Any]]:
        """
        Get list of all organizations the user has access to.

        Returns:
            List of organization objects
        """
        self.logger.info("Fetching organizations")  # type: ignore
        endpoint = "/organizations"
        result = self.get(endpoint)  # type: ignore

        # API might return a list or dict with organizations
        if isinstance(result, list):
            return result
        return result.get("organizations", [])

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
        self.logger.info(f"Fetching locations for org {organization_id}")  # type: ignore
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

        result = self.get(endpoint, params=params if params else None)  # type: ignore

        # API returns a list or dict with locations
        if isinstance(result, list):
            return result
        return result.get("locations", [])
