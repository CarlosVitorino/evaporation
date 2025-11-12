"""
Organization data models.

Contains DTOs for organization-related data structures.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Organization:
    """Organization data from the KISTERS Web Portal."""

    id: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None
