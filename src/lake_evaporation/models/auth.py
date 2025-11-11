"""
Authentication data models.

Contains DTOs for authentication-related data structures.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PortalCredentials:
    """Portal login credentials."""

    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


@dataclass
class PortalUser:
    """Portal user data returned from authentication."""

    user_name: str
    email: Optional[str] = None
    user_id: Optional[str] = None
    organization_ids: Optional[list] = None
