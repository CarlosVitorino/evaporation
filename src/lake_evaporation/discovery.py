"""
Time series discovery module.

Finds time series with lake evaporation tag and extracts metadata.
"""

import logging
from typing import Dict, Any, List, Optional
from .api import KistersAPI


class TimeSeriesDiscovery:
    """Discover and manage time series for lake evaporation."""

    def __init__(
        self,
        api_client: KistersAPI,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize discovery service.

        Args:
            api_client: API client instance
            logger: Logger instance
        """
        self.api_client = api_client
        self.logger = logger or logging.getLogger(__name__)

        # Cache for all timeseries (populated during discovery)
        self._all_timeseries: List[Dict[str, Any]] = []

    def discover_lake_evaporation_series(
        self,
        organization_id: str,
        store_all_timeseries: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Discover all time series with lake evaporation metadata for a specific organization.

        The logic is:
        1. Get all locations in the organization
        2. For each location, get all timeseries
        3. Filter timeseries that have "lakeEvaporation" in their metadata

        Args:
            organization_id: Organization ID to search in
            store_all_timeseries: If True, stores all fetched timeseries in cache
                                 for later use (e.g., building lookup maps)

        Returns:
            List of time series with lakeEvaporation metadata
        """
        self.logger.info(
            f"Discovering time series with lakeEvaporation metadata in org {organization_id}"
        )

        try:
            # Get all timeseries for this organization (with location data)
            all_timeseries = self.api_client.get_time_series_list(
                organization_id=organization_id,
                include_location_data=True,
                include_coverage=True
            )

            self.logger.info(f"Found {len(all_timeseries)} total timeseries in organization")

            # Store in cache if requested
            if store_all_timeseries:
                # Extend the cache with these timeseries (avoiding duplicates by ID)
                existing_ids = {ts.get("id") for ts in self._all_timeseries if ts.get("id")}
                for ts in all_timeseries:
                    ts_id = ts.get("id")
                    if ts_id and ts_id not in existing_ids:
                        self._all_timeseries.append(ts)
                        existing_ids.add(ts_id)

            # Filter timeseries that have lakeEvaporation metadata
            lake_evap_series = []
            for ts in all_timeseries:
                metadata = ts.get("metadata", {})
                if "lakeEvaporation" in metadata:
                    lake_evap_series.append(ts)

            self.logger.info(
                f"Found {len(lake_evap_series)} timeseries with lakeEvaporation metadata"
            )
            return lake_evap_series

        except Exception as e:
            self.logger.error(f"Failed to discover time series: {e}", exc_info=True)
            return []

    def extract_metadata(self, time_series: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and parse lake evaporation metadata from time series.

        Expected metadata format in OrganizationTimeseriesDTO:
        {
            "metadata": {
                "lakeEvaporation": {
                    "Temps": "tsId(...) or tsPath(...) or exchangeId(...)",
                    "RHTs": "...",
                    "WSpeedTs": "...",
                    "AirPressureTs": "...",
                    "hoursOfSunshineTs": "...",
                    "globalRadiationTs": "..."
                }
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

        # Extract location data from embedded fields (includeLocationData=true)
        location_data = {
            "id": time_series.get("locationId"),
            "name": time_series.get("locationName"),
            "latitude": time_series.get("locationLatitude"),
            "longitude": time_series.get("locationLongitude"),
            "elevation": time_series.get("locationElevation"),
            "geometry_type": time_series.get("locationGeometryType"),
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

    def get_all_evaporation_locations(
        self,
        organization_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all lake evaporation locations across all organizations or a specific one.

        Args:
            organization_id: Optional organization ID to limit search.
                           If None, searches all organizations.

        Returns:
            List of locations with metadata
        """
        all_locations = []

        try:
            # Determine which organizations to search
            if organization_id:
                # Single organization
                self.logger.info(
                    f"Discovering lake evaporation locations in org {organization_id}"
                )
                organizations = [{"id": organization_id}]
            else:
                # All organizations
                self.logger.info("Discovering lake evaporation locations across all organizations")
                organizations = self.api_client.get_organizations()
                self.logger.info(f"Found {len(organizations)} organizations")

            # Process each organization
            for org in organizations:
                org_id = org.get("id")
                org_name = org.get("name", org_id)

                if not org_id:
                    self.logger.warning(f"Organization {org_name} has no ID, skipping")
                    continue

                self.logger.info(f"Processing organization: {org_name} ({org_id})")

                # Find lake evaporation time series in this organization
                time_series_list = self.discover_lake_evaporation_series(org_id)

                # Extract metadata for each time series
                for ts in time_series_list:
                    metadata = self.extract_metadata(ts)
                    metadata["organization_id"] = org_id
                    metadata["organization_name"] = org_name
                    all_locations.append(metadata)

            self.logger.info(f"Total locations discovered: {len(all_locations)}")
            return all_locations

        except Exception as e:
            self.logger.error(f"Failed to discover locations: {e}", exc_info=True)
            return []

    def get_cached_timeseries(self) -> List[Dict[str, Any]]:
        """
        Get the cached timeseries list.

        The timeseries list is populated during discovery (when calling
        get_all_evaporation_locations). This method provides access to the
        cached list for building lookup maps to resolve tsPath and exchangeId
        references to their corresponding tsId values.

        Returns:
            List of all cached timeseries objects
        """
        return self._all_timeseries

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
