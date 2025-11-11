"""
Organization operations for KISTERS Web Portal API.

Handles retrieval of organizations.
"""

from typing import List, Dict, Any


class OrganizationsAPI:
    """Mixin for organization-related API operations."""

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
