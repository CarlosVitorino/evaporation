"""
Time series discovery module.

Finds time series with lake evaporation tag and extracts metadata.
"""

import logging
from typing import Dict, Any, List, Optional
from .api_client import APIClient


class TimeSeriesDiscovery:
    """Discover and manage time series for lake evaporation."""

    def __init__(self, api_client: APIClient, logger: Optional[logging.Logger] = None):
        """
        Initialize discovery service.

        Args:
            api_client: API client instance
            logger: Logger instance
        """
        self.api_client = api_client
        self.logger = logger or logging.getLogger(__name__)

    def discover_lake_evaporation_series(
        self,
        organization_id: str,
        tag: str = "lakeEvaporation"
    ) -> List[Dict[str, Any]]:
        """
        Discover all time series with lake evaporation tag.

        Args:
            organization_id: Organization ID
            tag: Tag to search for

        Returns:
            List of time series with metadata
        """
        self.logger.info(f"Discovering time series with tag '{tag}' in org {organization_id}")

        try:
            time_series_list = self.api_client.get_time_series_by_tag(
                organization_id=organization_id,
                tag=tag
            )

            self.logger.info(f"Found {len(time_series_list)} time series")
            return time_series_list

        except Exception as e:
            self.logger.error(f"Failed to discover time series: {e}")
            return []

    def extract_metadata(self, time_series: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and parse lake evaporation metadata from time series.

        Expected metadata format:
        {
            "lakeEvaporation": {
                "Temps": "tsId(...) or tsPath(...) or exchangeId(...)",
                "RHTs": "...",
                "WSpeedTs": "...",
                "AirPressureTs": "...",
                "hoursOfSunshineTs": "...",
                "globalRadiationTs": "..."
            }
        }

        Args:
            time_series: Time series object

        Returns:
            Parsed metadata dictionary
        """
        metadata = time_series.get("metadata", {})
        lake_evap_metadata = metadata.get("lakeEvaporation", {})

        if not lake_evap_metadata:
            self.logger.warning(
                f"No lakeEvaporation metadata found in time series {time_series.get('id')}"
            )

        return {
            "time_series_id": time_series.get("id"),
            "name": time_series.get("name"),
            "location": time_series.get("location", {}),
            "temperature_ts": lake_evap_metadata.get("Temps"),
            "humidity_ts": lake_evap_metadata.get("RHTs"),
            "wind_speed_ts": lake_evap_metadata.get("WSpeedTs"),
            "air_pressure_ts": lake_evap_metadata.get("AirPressureTs"),
            "sunshine_hours_ts": lake_evap_metadata.get("hoursOfSunshineTs"),
            "global_radiation_ts": lake_evap_metadata.get("globalRadiationTs"),
        }

    def get_all_evaporation_locations(self) -> List[Dict[str, Any]]:
        """
        Get all lake evaporation locations across all organizations.

        Returns:
            List of locations with metadata
        """
        self.logger.info("Discovering all lake evaporation locations")
        all_locations = []

        try:
            # Get all organizations
            organizations = self.api_client.get_organizations()
            self.logger.info(f"Found {len(organizations)} organizations")

            # For each organization, find lake evaporation time series
            for org in organizations:
                org_id = org.get("id")
                if not org_id:
                    self.logger.warning(f"Organization {org.get('name')} has no ID, skipping")
                    continue
                    
                self.logger.info(f"Processing organization: {org.get('name')} ({org_id})")

                time_series_list = self.discover_lake_evaporation_series(org_id)

                # Extract metadata for each time series
                for ts in time_series_list:
                    metadata = self.extract_metadata(ts)
                    metadata["organization_id"] = org_id
                    metadata["organization_name"] = org.get("name")
                    all_locations.append(metadata)

            self.logger.info(f"Total locations discovered: {len(all_locations)}")
            return all_locations

        except Exception as e:
            self.logger.error(f"Failed to discover locations: {e}")
            return []

    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Validate that required time series references are present.

        Args:
            metadata: Metadata dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            "temperature_ts",
            "humidity_ts",
            "wind_speed_ts",
            "air_pressure_ts"
        ]

        missing_fields = []
        for field in required_fields:
            if not metadata.get(field):
                missing_fields.append(field)

        if missing_fields:
            self.logger.warning(
                f"Missing required fields in metadata for {metadata.get('name')}: "
                f"{', '.join(missing_fields)}"
            )
            return False

        return True
