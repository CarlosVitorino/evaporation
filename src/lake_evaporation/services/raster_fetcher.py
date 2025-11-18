"""
Raster data fetcher for weather parameters.

Provides fallback data fetching from raster sources when timeseries are unavailable.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta

from ..core import DateUtils

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
        self.date_utils = DateUtils(logger)
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
            # Get parameter mappings for the primary model to return correct keys
            try:
                param_mappings = self.config.get_raster_parameters_for_model(primary_model)
                return {key: None for key in param_mappings.keys()}
            except Exception:
                return {}

        # Try primary model first with model-specific parameters
        result = self._find_timeseries_for_model_with_params(
            timeseries_list,
            primary_model
        )

        # If any parameters are missing and we have a fallback model, try it
        if fallback_model and primary_model != fallback_model:
            missing_params = [k for k, v in result.items() if v is None]
            if missing_params:
                self.logger.info(
                    f"Trying fallback model {fallback_model} for missing parameters: {missing_params}"
                )
                fallback_result = self._find_timeseries_for_model_with_params(
                    timeseries_list,
                    fallback_model,
                    only_params=missing_params
                )
                # Update result with fallback values
                for k, v in fallback_result.items():
                    if v is not None:
                        result[k] = v

        return result

    def _find_timeseries_for_model_with_params(
        self,
        timeseries_list: List[Dict[str, Any]],
        model: str,
        only_params: Optional[List[str]] = None
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Find timeseries for a specific model using model-specific parameter mappings.

        Args:
            timeseries_list: List of all raster timeseries
            model: Model identifier
            only_params: If provided, only search for these parameter types

        Returns:
            Dictionary mapping parameter type to timeseries (or None if not found)
        """
        # Get model-specific parameter mappings
        try:
            param_mappings = self.config.get_raster_parameters_for_model(model)
        except ValueError as e:
            self.logger.error(f"Failed to get parameters for model {model}: {e}")
            return {}

        # Filter to only requested parameters if specified
        if only_params:
            param_mappings = {
                k: v for k, v in param_mappings.items() 
                if k in only_params
            }

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
    ) -> Tuple[Dict[str, List[List[Any]]], Dict[str, str]]:
        """
        Fetch raster weather data for a specific location and date range.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            start_date: Start date (timezone-aware)
            end_date: End date (timezone-aware)
            organization_id: Optional organization ID

        Returns:
            Tuple of (data, units) where:
            - data: Dictionary mapping parameter type to list of data points
              {
                  "temperature": [[timestamp, value], ...],
                  "humidity": [[timestamp, value], ...],
                  ...
              }
            - units: Dictionary mapping parameter type to unit symbol
              {
                  "temperature": "°C",
                  "humidity": "%",
                  ...
              }
        """
        # Find appropriate raster timeseries
        timeseries_map = self.find_raster_timeseries_for_weather_data(
            latitude, longitude, organization_id
        )

        # Prepare point for extraction
        points = [{"lat": latitude, "lon": longitude}]

        # Ensure dates are timezone-aware and convert to ISO format
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError("start_date and end_date must be timezone-aware")

        start_iso = self.date_utils.to_iso_with_timezone(start_date)
        end_iso = self.date_utils.to_iso_with_timezone(end_date)

        # Fetch data for each parameter
        data: Dict[str, List[List[Any]]] = {}
        units: Dict[str, str] = {}
        datasource_id = self.config.raster_datasource_id

        # Get models for potential fallback
        primary_model, fallback_model = self.get_model_for_location(latitude, longitude)
        needs_fallback = primary_model != fallback_model

        for param_type, timeseries in timeseries_map.items():
            if timeseries is None:
                self.logger.warning(f"No raster timeseries found for {param_type}")
                data[param_type] = []
                continue

            product_name = timeseries.get("name")
            timeseries_id = timeseries.get("timeseriesId")
            if not timeseries_id:
                self.logger.warning(f"Missing timeseriesId for {param_type}")
                data[param_type] = []
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
                parsed_result = self._parse_raster_response(raster_data, param_type)
                
                # If data is empty and we have a fallback model, try it
                if not parsed_result["data"] and needs_fallback:
                    self.logger.info(
                        f"No data for {param_type} from primary model, trying fallback model {fallback_model}"
                    )
                    fallback_ts = self._get_fallback_timeseries(
                        param_type, fallback_model, organization_id
                    )
                    
                    if fallback_ts:
                        product_name = fallback_ts.get("name")
                        fallback_id = fallback_ts.get("timeseriesId")
                        if fallback_id:
                            raster_data = self.api.get_raster_point_data(
                                datasource_id=datasource_id,
                                timeseries_id=fallback_id,
                                points=points,
                                start_date=start_iso,
                                end_date=end_iso
                            )
                            parsed_result = self._parse_raster_response(raster_data, param_type)
                
                # Store data and unit separately
                data[param_type] = parsed_result["data"]
                if parsed_result["unit"]:
                    units[param_type] = parsed_result["unit"]
                
                self.logger.info(
                    f"Fetched {len(parsed_result['data'])} data points for {param_type}"
                    f"(model: {product_name} unit: {parsed_result['unit']})"
                )

            except Exception as e:
                self.logger.error(f"Failed to fetch raster data for {param_type}: {e}")
                data[param_type] = []

        return data, units

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
            
            # Get model-specific parameter mappings
            param_mappings = self.config.get_raster_parameters_for_model(fallback_model)
            
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
    ) -> Dict[str, Any]:
        """
        Parse raster API response into standardized format.

        Args:
            raster_response: Raw response from raster API (list of timeseries objects)
            parameter_type: Type of parameter (for logging)

        Returns:
            Dictionary with data points and metadata:
            {
                "data": [[timestamp, value], ...],
                "unit": "unit symbol"
            }
        """
        result = {
            "data": [],
            "unit": None
        }

        # Response should be a list of timeseries objects
        if not isinstance(raster_response, list):
            self.logger.warning(
                f"Unexpected raster response format for {parameter_type}: expected list, got {type(raster_response)}"
            )
            return result

        if not raster_response:
            self.logger.warning(f"Empty raster response for {parameter_type}")
            return result

        # Take the first timeseries object (we only requested one point)
        timeseries_obj = raster_response[0]

        if not isinstance(timeseries_obj, dict):
            self.logger.warning(f"Unexpected timeseries object format for {parameter_type}")
            return result

        # Extract unit symbol
        result["unit"] = timeseries_obj.get("unitSymbol")

        # Extract the data array
        raw_data = timeseries_obj.get("data", [])

        if not raw_data:
            self.logger.warning(f"No data in raster response for {parameter_type}")
            return result

        # Parse data array - each item is {"time": ..., "data": ...}
        for item in raw_data:
            timestamp = item.get("time")
            value = item.get("data")

            if timestamp is not None and value is not None:
                result["data"].append([timestamp, value])

        return result
