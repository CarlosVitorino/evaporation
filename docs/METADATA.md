# Lake Evaporation Time Series Metadata Structure

This document describes the metadata structure for configuring lake evaporation time series in the KISTERS Web Portal.

## Overview

A time series configured for lake evaporation must have a `lakeEvaporation` object in its metadata that references all required sensor time series and calculation parameters.

## Complete Metadata Structure

```json
{
  "metadata": {
    "lakeEvaporation": {
      "// Required sensor time series references": "",
      "Temps": "tsId(12345)",
      "RHTs": "tsId(12346)",
      "WSpeedTs": "tsId(12347)",
      "AirPressureTs": "tsId(12348)",

      "// Optional sensor time series": "",
      "hoursOfSunshineTs": "tsId(12349)",
      "globalRadiationTs": "tsId(12350)",

      "// Location parameters (optional - can be from location data)": "",
      "latitude": 51.0,
      "longitude": 10.0,
      "altitude": 23.0,

      "// Calculation constants (optional - uses defaults if not specified)": "",
      "albedo": 0.23,
      "angstromA": 0.25,
      "angstromB": 0.5,

      "// Metadata for tracking": "",
      "description": "Lake evaporation calculated using Shuttleworth algorithm",
      "algorithm": "Shuttleworth",
      "version": "1.0",
      "calculationUnit": "mm/day"
    }
  }
}
```

## Field Descriptions

### Required Sensor References

| Field | Description | Example |
|-------|-------------|---------|
| `Temps` | Temperature time series | `tsId(12345)` or `tsPath(/sensors/temperature)` |
| `RHTs` | Relative humidity time series | `tsId(12346)` |
| `WSpeedTs` | Wind speed time series (at 10m height) | `tsId(12347)` |
| `AirPressureTs` | Air pressure time series | `tsId(12348)` |

**Expected units:**
- Temperature: °C
- Relative Humidity: %
- Wind Speed: km/h (at 10m height)
- Air Pressure: kPa

### Optional Sensor References

| Field | Description | Notes |
|-------|-------------|-------|
| `hoursOfSunshineTs` | Sunshine hours time series | If not available, calculated from global radiation |
| `globalRadiationTs` | Global radiation time series | Used to calculate sunshine hours via Ångström-Prescott |

**Expected units:**
- Sunshine hours: hours
- Global radiation: W/m²

### Location Parameters

| Field | Description | Default Source |
|-------|-------------|----------------|
| `latitude` | Site latitude in degrees | From location geometry |
| `longitude` | Site longitude in degrees | From location geometry |
| `altitude` | Site elevation in meters | From location geometry |

**Note:** If not specified in metadata, these are taken from the location's geometry data.

### Calculation Constants

| Field | Description | Default Value |
|-------|-------------|---------------|
| `albedo` | Surface albedo (reflectance) for water | 0.23 |
| `angstromA` | Ångström-Prescott coefficient a | 0.25 |
| `angstromB` | Ångström-Prescott coefficient b | 0.5 |

## Time Series Reference Formats

Three formats are supported for referencing time series:

### 1. Time Series ID
```json
"Temps": "tsId(12345)"
```
Direct reference by internal time series ID.

### 2. Time Series Path
```json
"Temps": "tsPath(/organization/location/sensors/temperature)"
```
Reference by hierarchical path.

### 3. Exchange ID
```json
"Temps": "exchangeId(TEMP_SENSOR_01)"
```
Reference by external exchange identifier.

## Minimal Example

Minimum required metadata (uses defaults for everything else):

```json
{
  "metadata": {
    "lakeEvaporation": {
      "Temps": "tsId(12345)",
      "RHTs": "tsId(12346)",
      "WSpeedTs": "tsId(12347)",
      "AirPressureTs": "tsId(12348)"
    }
  }
}
```

The system will:
- Use location geometry for latitude/longitude/altitude
- Use default albedo (0.23)
- Use default Ångström-Prescott coefficients
- Set sunshine hours to 0 if not available

## Complete Example

Full metadata with all optional parameters:

```json
{
  "metadata": {
    "lakeEvaporation": {
      "Temps": "tsId(12345)",
      "RHTs": "tsId(12346)",
      "WSpeedTs": "tsId(12347)",
      "AirPressureTs": "tsId(12348)",
      "hoursOfSunshineTs": "tsId(12349)",
      "globalRadiationTs": "tsId(12350)",
      "latitude": 51.0,
      "longitude": 10.0,
      "altitude": 23.0,
      "albedo": 0.23,
      "angstromA": 0.25,
      "angstromB": 0.5,
      "description": "Lake Brandenburg evaporation monitoring",
      "algorithm": "Shuttleworth",
      "version": "1.0",
      "calculationUnit": "mm/day",
      "notes": "Uses nearby meteorological station sensors"
    }
  }
}
```

## How to Configure

### Using the Web Portal UI

1. Navigate to the time series that will store evaporation results
2. Edit the time series metadata
3. Add the `lakeEvaporation` object with required sensor references
4. Save the time series

### Using the API

```python
from lake_evaporation.api import KistersAPI

# Login
api = KistersAPI(base_url="...", username="...", password="...")
api.login()

# Get existing time series
ts = api.get_time_series(
    organization_id="org_123",
    timeseries_id="evap_ts_001"
)

# Update metadata
ts["metadata"]["lakeEvaporation"] = {
    "Temps": "tsId(12345)",
    "RHTs": "tsId(12346)",
    "WSpeedTs": "tsId(12347)",
    "AirPressureTs": "tsId(12348)",
    "hoursOfSunshineTs": "tsId(12349)"
}

# Save
api.update_time_series(
    organization_id="org_123",
    timeseries_id="evap_ts_001",
    timeseries_data=ts
)
```

## Validation

The system validates that:
- ✓ All required sensor references are present
- ✓ Referenced time series exist and are accessible
- ✓ Sensor data is available for the calculation period
- ✓ Data values are within reasonable ranges

Missing or invalid metadata will be logged as warnings, and those locations will be skipped.

## Data Flow

```
Input Time Series          Lake Evaporation TS
    (sensors)          →      (metadata)
┌─────────────────┐     ┌──────────────────────┐
│ Temperature     │ ───→│ lakeEvaporation {    │
│ Humidity        │ ───→│   Temps: "tsId(...)" │
│ Wind Speed      │ ───→│   RHTs: "tsId(...)"  │
│ Air Pressure    │ ───→│   ...                │
│ Sunshine Hours  │ ───→│ }                    │
└─────────────────┘     └──────────────────────┘
                               │
                               ↓
                        [Calculation Engine]
                               │
                               ↓
                        Evaporation Value
                        (mm/day) written back
```

## Best Practices

1. **Use consistent reference format** - Pick one format (tsId, tsPath, or exchangeId) and use it consistently
2. **Include optional sensors** - Sunshine hours or global radiation improve accuracy
3. **Verify sensor locations** - All sensors should be from the same location or nearby
4. **Check sensor units** - Ensure sensors provide data in expected units
5. **Add descriptive metadata** - Include description, notes for documentation
6. **Test with historical data** - Verify calculations work before production use

## Troubleshooting

### "Missing required field" error
Ensure all four required sensor references (Temps, RHTs, WSpeedTs, AirPressureTs) are present.

### "No data available" warning
Check that the referenced time series have data for your calculation period.

### "Invalid range" errors
Verify sensor data is in correct units (e.g., temperature in °C, not Kelvin).

### Time series not discovered
Ensure the `lakeEvaporation` object is directly under `metadata`, not nested deeper.

## Related Configuration

See also:
- `config.json` - System-wide constants and defaults
- `SETUP.md` - Initial system configuration
- API documentation - Time series metadata endpoints
