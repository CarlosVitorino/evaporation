"""
Time series discovery module.

Finds time series with lake evaporation tag and extracts metadata.
"""

import logging
from typing import Dict, Any, List, Optional
from .api_client import APIClient


class TimeSeriesDiscovery:
    """Discover and manage time series for lake evaporation."""

    def __init__(
        self,
        api_client: APIClient,
        organization_id: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize discovery service.

        Args:
            api_client: API client instance
            organization_id: Organization ID to work with
            logger: Logger instance
        """
        self.api_client = api_client
        self.organization_id = organization_id
        self.logger = logger or logging.getLogger(__name__)

    def discover_lake_evaporation_series(
        self,
        tag: str = "lakeEvaporation"
    ) -> List[Dict[str, Any]]:
        """
        Discover all time series with lake evaporation tag.

        Args:
            tag: Tag to search for

        Returns:
            List of time series with metadata
        """
        self.logger.info(
            f"Discovering time series with tag '{tag}' in org {self.organization_id}"
        )

        try:
            # Get all locations with the tag
            locations = self.api_client.get_locations(
                organization_id=self.organization_id,
                tags=tag,
                include_geometry=False
            )

            self.logger.info(f"Found {len(locations)} locations with tag '{tag}'")

            # For each location, get the timeseries
            time_series_list = []
            for location in locations:
                location_id = location.get("id")
                if not location_id:
                    continue

                # Get timeseries for this location
                timeseries = self.api_client.get_time_series_list(
                    organization_id=self.organization_id,
                    location=location_id,
                    include_location_data=True,
                    include_coverage=True
                )

                # Add location data to each timeseries
                for ts in timeseries:
                    ts["location"] = location
                    time_series_list.append(ts)

            self.logger.info(f"Found {len(time_series_list)} time series total")
            return time_series_list

        except Exception as e:
            self.logger.error(f"Failed to discover time series: {e}")
            return []

    def extract_metadata(self, time_series: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and parse lake evaporation metadata from time series.

        Expected metadata format in the new API:
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
            time_series: Time series object (OrganizationTimeseriesDTO)

        Returns:
            Parsed metadata dictionary
        """
        # In the new API, metadata is a JsonNode
        metadata = time_series.get("metadata", {})
        lake_evap_metadata = metadata.get("lakeEvaporation", {})

        if not lake_evap_metadata:
            self.logger.warning(
                f"No lakeEvaporation metadata found in time series {time_series.get('id')}"
            )

        # Extract location data (can be from embedded location data or separate location object)
        location = time_series.get("location", {})
        location_data = {
            "id": time_series.get("locationId"),
            "name": time_series.get("locationName") or location.get("name"),
            "latitude": time_series.get("locationLatitude") or location.get("latitude"),
            "longitude": time_series.get("locationLongitude") or location.get("longitude"),
            "elevation": time_series.get("locationElevation") or location.get("elevation"),
            "geometry_type": time_series.get("locationGeometryType") or location.get("geometryType"),
        }

        return {
            "time_series_id": time_series.get("id"),
            "name": time_series.get("name"),
            "location": location_data,
            "temperature_ts": lake_evap_metadata.get("Temps"),
            "humidity_ts": lake_evap_metadata.get("RHTs"),
            "wind_speed_ts": lake_evap_metadata.get("WSpeedTs"),
            "air_pressure_ts": lake_evap_metadata.get("AirPressureTs"),
            "sunshine_hours_ts": lake_evap_metadata.get("hoursOfSunshineTs"),
            "global_radiation_ts": lake_evap_metadata.get("globalRadiationTs"),
        }

    def get_all_evaporation_locations(self) -> List[Dict[str, Any]]:
        """
        Get all lake evaporation locations for the configured organization.

        Returns:
            List of locations with metadata
        """
        self.logger.info(
            f"Discovering all lake evaporation locations in org {self.organization_id}"
        )
        all_locations = []

        try:
            # Find lake evaporation time series
            time_series_list = self.discover_lake_evaporation_series()

            # Extract metadata for each time series
            for ts in time_series_list:
                metadata = self.extract_metadata(ts)
                metadata["organization_id"] = self.organization_id
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
