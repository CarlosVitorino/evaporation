"""
Organization operations for KISTERS Web Portal API.

Handles retrieval of organizations.
"""

import logging
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import APIClient


class OrganizationsAPI:
    """Mixin for organization-related API operations."""
    logger: logging.Logger

    def get(self, endpoint: str, params: Any = None) -> Any:
        """Method provided by APIClient base class."""
        ...

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
