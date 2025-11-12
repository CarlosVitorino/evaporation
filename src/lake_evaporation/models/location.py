"""
Location data models.

Contains DTOs for location-related data structures.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Location:
    """Organization location data."""

    id: str
    name: str
    organization_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    geometry_type: Optional[str] = None
    tags: Optional[list] = None
