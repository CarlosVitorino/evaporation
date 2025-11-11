"""
Helper functions for API operations.

Provides utility functions for parsing metadata and resolving references.
"""

from typing import Dict, Any


def parse_time_series_reference(reference: str) -> str:
    """
    Parse time series reference to extract ID.

    Supports formats:
    - tsId(123)
    - tsPath(/path/to/series)
    - exchangeId(abc123)
    - Direct ID: 123

    Args:
        reference: Time series reference string

    Returns:
        Extracted time series ID

    Raises:
        ValueError: If reference is empty
    """
    if not reference:
        raise ValueError("Empty time series reference")

    # Check for function-style references
    if "(" in reference and ")" in reference:
        # Extract content between parentheses
        start = reference.index("(") + 1
        end = reference.index(")")
        return reference[start:end]

    # Assume it's a direct ID
    return reference


def extract_location_metadata(time_series: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and parse lake evaporation metadata from time series.

    Expected metadata format in time series:
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
        time_series: Time series object

    Returns:
        Parsed metadata dictionary with location and sensor references
    """
    metadata = time_series.get("metadata", {})
    lake_evap_metadata = metadata.get("lakeEvaporation", {})

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


def validate_location_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Validate that required time series references are present in metadata.

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

    return len(missing_fields) == 0
