"""
Raster data fetcher for weather parameters.

Provides fallback data fetching from raster sources when timeseries are unavailable.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from ..api import KistersAPI
    from ..core.config import Config


class RasterDataFetcher:
    """
    Fetches weather data from raster sources.

    This class provides fallback data fetching when timeseries metadata
    is missing or invalid.
    """

    # Europe bounding box (approximate)
    EUROPE_BOUNDS = {
        "min_lat": 35.0,
        "max_lat": 72.0,
        "min_lon": -25.0,
        "max_lon": 45.0
    }

    def __init__(
        self,
        api_client: "KistersAPI",
        config: "Config",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize raster data fetcher.

        Args:
            api_client: API client with raster capabilities
            config: Configuration object
            logger: Optional logger instance
        """
        self.api = api_client
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._cached_timeseries_list: Optional[List[Dict[str, Any]]] = None

    def is_location_in_europe(self, latitude: float, longitude: float) -> bool:
        """
        Determine if a location is in Europe.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            True if location is in Europe
        """
        return (
            self.EUROPE_BOUNDS["min_lat"] <= latitude <= self.EUROPE_BOUNDS["max_lat"] and
            self.EUROPE_BOUNDS["min_lon"] <= longitude <= self.EUROPE_BOUNDS["max_lon"]
        )

    def get_model_for_location(self, latitude: float, longitude: float) -> Tuple[str, str]:
        """
        Determine the appropriate weather model for a location.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Tuple of (primary_model_path, fallback_model_path)
            e.g., ("icon_eu", "gfs") for Europe or ("gfs", None) for global
        """
        if self.is_location_in_europe(latitude, longitude):
            # Europe: try DWD-ICON-EU first, fallback to GFS
            return (self.config.raster_europe_model, self.config.raster_global_model)
        else:
            # Rest of world: use GFS
            return (self.config.raster_global_model, self.config.raster_global_model)

    def _get_raster_timeseries_list(
        self,
        organization_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get list of available raster timeseries.

        Args:
            organization_id: Optional organization ID
            force_refresh: Force refresh of cached list

        Returns:
            List of raster timeseries
        """
        if self._cached_timeseries_list is not None and not force_refresh:
            return self._cached_timeseries_list

        self.logger.info("Fetching raster timeseries list")
        datasource_id = self.config.raster_datasource_id

        try:
            self._cached_timeseries_list = self.api.get_raster_timeseries_list(
                datasource_id=datasource_id,
                organization_id=organization_id
            )
            self.logger.info(f"Found {len(self._cached_timeseries_list)} raster timeseries")
            return self._cached_timeseries_list
        except Exception as e:
            self.logger.error(f"Failed to fetch raster timeseries list: {e}")
            return []

    def filter_timeseries_by_model_and_parameter(
        self,
        timeseries_list: List[Dict[str, Any]],
        model: str,
        parameter_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Filter raster timeseries by model and parameter names.

        Args:
            timeseries_list: List of raster timeseries
            model: Model identifier to filter by (e.g., "gfs", "icon_eu")
            parameter_names: List of parameter names to look for (e.g., ["TMP_2M", "PRMSL"])

        Returns:
            Dictionary mapping parameter name to timeseries object
            e.g., {"TMP_2M": {...}, "PRMSL": {...}}
        """
        filtered = {}

        for ts in timeseries_list:
            if not ts or not ts.get("name") or not ts.get("path"):
                continue

            parameter_name = ts.get("name")
            path = ts.get("path")

            # Check if this parameter is in our list
            if parameter_name in parameter_names:
                # Check if the model matches (path should contain model identifier)
                if path and f"/{model}/" in path.lower():
                    filtered[parameter_name] = ts
                    self.logger.debug(
                        f"Found {parameter_name} for model {model}: {ts.get('timeseriesId')}"
                    )

        return filtered

    def find_raster_timeseries_for_weather_data(
        self,
        latitude: float,
        longitude: float,
        organization_id: Optional[str] = None
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Find appropriate raster timeseries for weather parameters based on location.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            organization_id: Optional organization ID

        Returns:
            Dictionary mapping weather parameter type to raster timeseries:
            {
                "temperature": {...},
                "humidity": {...},
                "wind_speed": {...},
                "pressure": {...},
                "cloud": {...}
            }
        """
        # Get parameter name mappings from config
        param_mappings = self.config.raster_parameters

        # Determine model based on location
        primary_model, fallback_model = self.get_model_for_location(latitude, longitude)

        self.logger.info(
            f"Location ({latitude}, {longitude}): "
            f"Primary model={primary_model}, Fallback={fallback_model}"
        )

        # Get available raster timeseries
        timeseries_list = self._get_raster_timeseries_list(organization_id)

        if not timeseries_list:
            self.logger.warning("No raster timeseries available")
            return {key: None for key in param_mappings.keys()}

        # Try primary model first
        result = self._find_timeseries_for_model(
            timeseries_list,
            primary_model,
            param_mappings
        )

        # If any parameters are missing and we have a fallback model, try it
        if fallback_model:
            missing_params = [k for k, v in result.items() if v is None]
            if missing_params:
                self.logger.info(
                    f"Trying fallback model {fallback_model} for missing parameters: {missing_params}"
                )
                fallback_result = self._find_timeseries_for_model(
                    timeseries_list,
                    fallback_model,
                    {k: v for k, v in param_mappings.items() if k in missing_params}
                )
                # Update result with fallback values
                for k, v in fallback_result.items():
                    if v is not None:
                        result[k] = v

        return result

    def _find_timeseries_for_model(
        self,
        timeseries_list: List[Dict[str, Any]],
        model: str,
        param_mappings: Dict[str, str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Find timeseries for a specific model.

        Args:
            timeseries_list: List of all raster timeseries
            model: Model identifier
            param_mappings: Parameter name mappings (e.g., {"temperature": "TMP_2M"})

        Returns:
            Dictionary mapping parameter type to timeseries (or None if not found)
        """
        # Get list of raster parameter names we're looking for
        raster_param_names = list(param_mappings.values())

        # Filter timeseries by model and parameter names
        filtered = self.filter_timeseries_by_model_and_parameter(
            timeseries_list,
            model,
            raster_param_names
        )

        # Map back to our parameter types
        result = {}
        for param_type, raster_name in param_mappings.items():
            result[param_type] = filtered.get(raster_name)

        return result

    def fetch_raster_data_for_location(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
        organization_id: Optional[str] = None
    ) -> Dict[str, List[List[Any]]]:
        """
        Fetch raster weather data for a specific location and date range.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            start_date: Start date
            end_date: End date
            organization_id: Optional organization ID

        Returns:
            Dictionary mapping parameter type to list of data points:
            {
                "temperature": [{"timestamp": "...", "value": 15.2}, ...],
                "humidity": [...],
                "wind_speed": [...],
                "pressure": [...],
                "cloud": [...]
            }
        """
        # Find appropriate raster timeseries
        timeseries_map = self.find_raster_timeseries_for_weather_data(
            latitude, longitude, organization_id
        )

        # Prepare point for extraction
        points = [{"lat": latitude, "lon": longitude}]

        # Convert dates to ISO format with timezone
        # If datetime is naive (no timezone), assume UTC
        if start_date.tzinfo is None:
            from datetime import timezone
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            from datetime import timezone
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        # Fetch data for each parameter
        result = {}
        datasource_id = self.config.raster_datasource_id

        # Get models for potential fallback
        primary_model, fallback_model = self.get_model_for_location(latitude, longitude)
        needs_fallback = primary_model != fallback_model

        for param_type, timeseries in timeseries_map.items():
            if timeseries is None:
                self.logger.warning(f"No raster timeseries found for {param_type}")
                result[param_type] = []
                continue

            timeseries_id = timeseries.get("timeseriesId")
            if not timeseries_id:
                self.logger.warning(f"Missing timeseriesId for {param_type}")
                result[param_type] = []
                continue

            try:
                self.logger.debug(f"Fetching raster data for {param_type} ({timeseries_id})")
                raster_data = self.api.get_raster_point_data(
                    datasource_id=datasource_id,
                    timeseries_id=timeseries_id,
                    points=points,
                    start_date=start_iso,
                    end_date=end_iso
                )

                # Parse and format the data
                parsed_data = self._parse_raster_response(raster_data, param_type)
                
                # If data is empty and we have a fallback model, try it
                if not parsed_data and needs_fallback:
                    self.logger.info(
                        f"No data for {param_type} from primary model, trying fallback model {fallback_model}"
                    )
                    fallback_ts = self._get_fallback_timeseries(
                        param_type, fallback_model, organization_id
                    )
                    
                    if fallback_ts:
                        fallback_id = fallback_ts.get("timeseriesId")
                        if fallback_id:
                            raster_data = self.api.get_raster_point_data(
                                datasource_id=datasource_id,
                                timeseries_id=fallback_id,
                                points=points,
                                start_date=start_iso,
                                end_date=end_iso
                            )
                            parsed_data = self._parse_raster_response(raster_data, param_type)
                
                result[param_type] = parsed_data
                self.logger.info(f"Fetched {len(parsed_data)} data points for {param_type}")

            except Exception as e:
                self.logger.error(f"Failed to fetch raster data for {param_type}: {e}")
                result[param_type] = []

        return result

    def _get_fallback_timeseries(
        self,
        param_type: str,
        fallback_model: str,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get fallback timeseries for a parameter type.

        Args:
            param_type: Parameter type (e.g., "temperature")
            fallback_model: Fallback model identifier
            organization_id: Optional organization ID

        Returns:
            Fallback timeseries object or None
        """
        try:
            timeseries_list = self._get_raster_timeseries_list(organization_id)
            param_mappings = self.config.raster_parameters
            
            if param_type not in param_mappings:
                return None
            
            raster_name = param_mappings[param_type]
            filtered = self.filter_timeseries_by_model_and_parameter(
                timeseries_list,
                fallback_model,
                [raster_name]
            )
            
            return filtered.get(raster_name)
        except Exception as e:
            self.logger.error(f"Failed to get fallback timeseries for {param_type}: {e}")
            return None

    def _parse_raster_response(
        self,
        raster_response: Any,
        parameter_type: str
    ) -> List[Dict[str, Any]]:
        """
        Parse raster API response into standardized format.

        Args:
            raster_response: Raw response from raster API (list of timeseries objects)
            parameter_type: Type of parameter (for logging)

        Returns:
           Map Object with a List of data points in format [{"time": "...", "data": ...}, ...]

        
        """
        data_points = []

        # Response should be a list of timeseries objects
        if not isinstance(raster_response, list):
            self.logger.warning(
                f"Unexpected raster response format for {parameter_type}: expected list, got {type(raster_response)}"
            )
            return data_points

        if not raster_response:
            self.logger.warning(f"Empty raster response for {parameter_type}")
            return data_points

        # Take the first timeseries object (we only requested one point)
        timeseries_obj = raster_response[0]

        if not isinstance(timeseries_obj, dict):
            self.logger.warning(f"Unexpected timeseries object format for {parameter_type}")
            return data_points

        # Extract the data array
        raw_data = timeseries_obj.get("data", [])

        if not raw_data:
            self.logger.warning(f"No data in raster response for {parameter_type}")
            return data_points

        # Parse data array - each item is [timestamp, value]
        for item in raw_data:

            timestamp = item.get("time")
            value = item.get("data")

            if timestamp is not None and value is not None:
                data_points.append({
                    "timestamp": timestamp,
                    "value": value
                })

        self.logger.debug(
            f"Parsed {len(data_points)} data points for {parameter_type} "
            f"(unit: {timeseries_obj.get('unitSymbol', 'unknown')})"
        )

        return data_points
