"""
Time series discovery service.

Finds time series with lake evaporation tag and extracts metadata.
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..api import KistersAPI
    from ..core.config import Config



class TimeSeriesDiscovery:
    """Discover and manage time series for lake evaporation."""

    def __init__(
        self,
        api_client: "KistersAPI",
        config: Optional["Config"] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize discovery service.

        Args:
            api_client: API client instance
            config: Configuration object (for raster fallback capability check)
            logger: Logger instance
        """
        self.api_client = api_client
        self.config = config
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
            all_timeseries = self.api_client.get_time_series_list(
                organization_id=organization_id,
                include_location_data=True,
                include_coverage=True
            )

            self.logger.info(f"Found {len(all_timeseries)} total timeseries in organization")

            if store_all_timeseries:
                existing_ids = {ts.get("id") for ts in self._all_timeseries if ts.get("id")}
                for ts in all_timeseries:
                    ts_id = ts.get("id")
                    if ts_id and ts_id not in existing_ids:
                        self._all_timeseries.append(ts)
                        existing_ids.add(ts_id)

            lake_evap_series = []
            for ts in all_timeseries:
                metadata = ts.get("metadata") or {}
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
        metadata = time_series.get("metadata") or {}  # Handle None metadata
        lake_evap_metadata = metadata.get("lakeEvaporation") or {}  # Handle None

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

    def get_all_evaporation_timeseries(self) -> List[Dict[str, Any]]:
        """
        Get all lake evaporation time series across all organizations.

        Always fetches from all organizations that the user has access to.

        Returns:
            List of time series with metadata (including organization timezone)
        """
        lake_evap_series = []

        try:
            # Fetch all organizations
            self.logger.info("Discovering lake evaporation locations across all organizations")
            organizations = self.api_client.get_organizations()
            self.logger.info(f"Found {len(organizations)} organizations")

            # Process each organization
            for org in organizations:
                org_id = org.get("id")
                org_name = org.get("name", org_id)
                org_timezone = org.get("timeZone", "UTC")  # Default to UTC if not specified

                if not org_id:
                    self.logger.warning(f"Organization {org_name} has no ID, skipping")
                    continue

                self.logger.info(
                    f"Processing organization: {org_name} ({org_id}) - Timezone: {org_timezone}"
                )

                # Find lake evaporation time series in this organization
                lake_evap_series_raw_list = self.discover_lake_evaporation_series(org_id)

                # Extract metadata for each time series
                for ts in lake_evap_series_raw_list:
                    metadata = self.extract_metadata(ts)
                    metadata["organization_id"] = org_id
                    metadata["organization_name"] = org_name
                    metadata["organization_timezone"] = org_timezone 
                    lake_evap_series.append(metadata)

            self.logger.info(f"Total time series discovered: {len(lake_evap_series)}")
            return lake_evap_series

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
        Validate that required data sources are available.

        With raster fallback enabled, validation is more flexible:
        - If timeseries references exist for required fields, they must be valid
        - If timeseries are missing BUT raster fallback is enabled AND location has coordinates,
          validation still passes (raster will provide the data)
        - If neither timeseries nor raster fallback is available, validation fails

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

        # Check which required fields are missing
        missing_fields = [field for field in required_fields if not metadata.get(field)]

        if not missing_fields:
            # All timeseries are present - validation passes
            return True

        # Some timeseries are missing - check if raster fallback can cover them
        if self._can_use_raster_fallback(metadata):
            self.logger.info(
                f"Location {metadata.get('name')}: Missing timeseries {', '.join(missing_fields)}, "
                f"but raster fallback is available"
            )
            return True

        # No timeseries and no raster fallback - validation fails
        self.logger.warning(
            f"Missing required fields in metadata for {metadata.get('name')}: "
            f"{', '.join(missing_fields)} (and raster fallback not available)"
        )
        return False

    def _can_use_raster_fallback(self, metadata: Dict[str, Any]) -> bool:
        """
        Check if raster fallback can be used for this location.

        Raster fallback requires:
        1. Raster to be enabled in configuration
        2. Raster to be configured for use as fallback
        3. Location to have valid coordinates (latitude/longitude)

        Args:
            metadata: Location metadata

        Returns:
            True if raster fallback is available
        """
        # Check if raster is enabled and configured as fallback
        if not self.config:
            return False

        if not self.config.raster_enabled or not self.config.raster_use_as_fallback:
            return False

        # Check if location has valid coordinates
        location = metadata.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is None or longitude is None:
            self.logger.warning(
                f"Location {metadata.get('name')} has no coordinates, "
                f"cannot use raster fallback"
            )
            return False

        # Validate coordinate ranges
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            self.logger.warning(
                f"Location {metadata.get('name')} has invalid coordinates "
                f"(lat={latitude}, lon={longitude}), cannot use raster fallback"
            )
            return False

        return True
