# Raster Data Fallback Feature

## Overview

This feature adds a fallback mechanism to the lake evaporation calculation system. When timeseries metadata is missing or invalid, the system automatically fetches weather data from raster sources (GFS and DWD-ICON-EU models).

## Key Features

### 1. Automatic Fallback
- When timeseries references (temperature, humidity, wind speed, air pressure) are missing from metadata
- When timeseries data fetching fails or returns empty results
- Seamlessly switches to raster data sources without user intervention

### 2. Location-Based Model Selection
The system automatically selects the appropriate weather model based on geographic location:

**Europe (35°N - 72°N, 25°W - 45°E):**
- Primary: DWD-ICON-EU (icon_eu)
- Fallback: GFS (gfs)

**Rest of World:**
- Primary: GFS (gfs)
- Fallback: None

### 3. Parameter Mapping
Raster parameter names are automatically mapped to system parameters:

| System Parameter | Raster Parameter |
|-----------------|------------------|
| temperature     | TMP_2M          |
| humidity        | RH_2M           |
| wind_speed      | FF_10M          |
| pressure        | PRMSL           |
| cloud           | TCDC            |

## Configuration

### config.json Example

```json
{
  "raster": {
    "datasource_id": 1,
    "enabled": true,
    "use_as_fallback": true,
    "models": {
      "europe": "icon_eu",
      "global": "gfs"
    },
    "parameters": {
      "temperature": "TMP_2M",
      "pressure": "PRMSL",
      "humidity": "RH_2M",
      "wind_speed": "FF_10M",
      "cloud": "TCDC"
    }
  }
}
```

### Configuration Options

- **`datasource_id`** (int): Raster datasource ID (default: 1)
- **`enabled`** (bool): Enable/disable raster data fetching (default: true)
- **`use_as_fallback`** (bool): Use raster as fallback when timeseries unavailable (default: true)
- **`models.europe`** (string): Model for European locations (default: "icon_eu")
- **`models.global`** (string): Model for non-European locations (default: "gfs")
- **`parameters`** (object): Mapping between system parameters and raster parameter names

## API Endpoints

### 1. Get Raster Timeseries List

**Endpoint:** `GET /raster/datasources/{datasource_id}/timeSeries`

**Query Parameters:**
- `orgId` (optional): Organization ID

**Response:**
```json
[
  {
    "timeseriesId": "5b80141d-5843-445f-9249-66c2c6741052",
    "path": "/gfs/TMP_2M",
    "name": "TMP_2M",
    "unitSymbol": "°C",
    "parameterKey": "Temperature",
    "coverage": { ... },
    "boundingBox": { ... }
  },
  ...
]
```

### 2. Get Raster Point Data (raster2Point)

**Endpoint:** `GET /raster/datasources/{datasource_id}/timeSeries/{timeseriesId}/points`

**Query Parameters:**
- `extractMode`: Extraction mode (default: "strict")
- `points`: JSON array of point coordinates `[{"lat": 45.5, "lon": 10.8}]`
- `allModelMembers`: Include all model members (default: true)
- `from`: Start date (ISO format)
- `until`: End date (ISO format)

**Response:**
```json
{
  "data": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "values": [15.2]
    },
    ...
  ]
}
```

## Implementation Details

### Architecture

```
┌─────────────────┐
│   Main App      │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│   DataFetcher           │
│  - fetch_daily_data()   │
└────────┬───────┬────────┘
         │       │
         │       └──────────────────────┐
         │                              │
         v                              v
┌──────────────────┐      ┌──────────────────────┐
│ TimeSeriesAPI    │      │ RasterDataFetcher    │
│ (Primary)        │      │ (Fallback)           │
└──────────────────┘      └──────────┬───────────┘
                                     │
                                     v
                          ┌──────────────────────┐
                          │     RasterAPI        │
                          │ - get_timeseries()   │
                          │ - get_point_data()   │
                          └──────────────────────┘
```

### Key Components

#### 1. RasterAPI (`api/raster.py`)
- Mixin class for raster-related API operations
- Handles communication with raster endpoints
- Properly encodes query parameters (JSON encoding for complex objects)

#### 2. RasterDataFetcher (`raster_fetcher.py`)
- Main logic for raster data fetching
- Location-based model selection
- Timeseries filtering by model and parameter
- Data parsing and formatting

#### 3. DataFetcher (`data_fetcher.py`)
- Enhanced with fallback logic
- Checks for missing timeseries data
- Automatically triggers raster fallback when needed

#### 4. Config (`core/config.py`)
- Extended with raster-specific configuration properties
- Provides easy access to raster settings

### Workflow

1. **Location Discovery**: System discovers locations with `lakeEvaporation` metadata
2. **Metadata Extraction**: Extracts timeseries references for weather parameters
3. **Data Fetching**:
   - Attempts to fetch from timeseries (primary source)
   - If data is missing or invalid:
     - Determines location (latitude/longitude)
     - Selects appropriate model (ICON-EU or GFS)
     - Fetches raster timeseries list
     - Filters by model and parameter names
     - Extracts point data for the location
     - Fills in missing parameters
4. **Data Processing**: Continues with normal aggregation and calculation

## Testing

### Unit Tests

Run the test suite:
```bash
PYTHONPATH=/home/user/evaporation/src python -m unittest tests.test_raster_fallback -v
```

### Test Coverage

- ✅ Location detection (Europe vs non-Europe)
- ✅ Model selection based on location
- ✅ Timeseries filtering by model and parameter
- ✅ DataFetcher initialization with/without raster
- ✅ Fallback triggering on missing data
- ✅ API endpoint construction

## Usage Examples

### Example 1: Location with Missing Timeseries

```python
# Location metadata WITHOUT timeseries references
location_metadata = {
    "time_series_id": "lake_001",
    "name": "Lake Como",
    "location": {
        "latitude": 46.0,
        "longitude": 9.2,
        "altitude": 198.0
    },
    "organization_id": "org_123"
    # No temperature_ts, humidity_ts, etc.
}

# DataFetcher will automatically use raster fallback
data = data_fetcher.fetch_daily_data(location_metadata, target_date)

# Result: data contains weather parameters from DWD-ICON-EU (Europe location)
```

### Example 2: Location with Partial Timeseries

```python
# Location with only temperature and humidity, missing wind/pressure
location_metadata = {
    "time_series_id": "lake_002",
    "name": "Lake Geneva",
    "location": {
        "latitude": 46.4,
        "longitude": 6.5,
        "altitude": 372.0
    },
    "temperature_ts": "tsId(12345)",
    "humidity_ts": "tsId(12346)",
    # Missing: wind_speed_ts, air_pressure_ts
    "organization_id": "org_123"
}

# DataFetcher will:
# 1. Fetch temperature and humidity from timeseries
# 2. Use raster fallback for wind_speed and air_pressure
data = data_fetcher.fetch_daily_data(location_metadata, target_date)
```

## Logging

The system provides detailed logging for raster fallback operations:

```
INFO: Missing required parameters: wind_speed, air_pressure. Attempting raster fallback...
INFO: Location (46.4, 6.5): Primary model=icon_eu, Fallback=gfs
INFO: Fetching raster timeseries list
INFO: Found 150 raster timeseries
DEBUG: Found TMP_2M for model icon_eu: 5b80141d-5843-445f-9249-66c2c6741052
DEBUG: Fetching raster data for wind_speed (ts_id_123)
INFO: Fetched 24 data points for wind_speed
INFO:   wind_speed: 24 data points (from raster fallback)
```

## Error Handling

The raster fallback system includes comprehensive error handling:

1. **Missing Location Coordinates**: Logs warning and skips raster fallback
2. **API Errors**: Logs error and continues with available data
3. **Invalid Timeseries**: Gracefully handles missing parameters
4. **Network Issues**: Retries according to API client configuration

## Performance Considerations

- **Caching**: Raster timeseries list is cached to avoid repeated API calls
- **Lazy Loading**: Raster data is only fetched when needed
- **Selective Fetching**: Only missing parameters are fetched from raster
- **Parallel Requests**: Could be enhanced to fetch multiple parameters in parallel

## Future Enhancements

1. **Parallel Data Fetching**: Fetch multiple raster parameters simultaneously
2. **Advanced Caching**: Cache raster point data for frequently accessed locations
3. **Custom Model Selection**: Allow per-location model override in metadata
4. **Data Quality Checks**: Validate raster data quality before using as fallback
5. **Interpolation**: Interpolate raster data to match timeseries temporal resolution

## Troubleshooting

### Fallback Not Triggering

**Issue**: Raster fallback is not being used even when timeseries are missing

**Solutions**:
- Check `config.json`: Ensure `raster.enabled = true` and `raster.use_as_fallback = true`
- Verify location has latitude/longitude in metadata
- Check logs for error messages

### Wrong Model Selected

**Issue**: System uses GFS instead of ICON-EU for European location

**Solutions**:
- Verify location coordinates are within Europe bounds (35°N-72°N, 25°W-45°E)
- Check `config.json` model configuration
- Review `is_location_in_europe()` logic

### No Data From Raster

**Issue**: Raster fallback triggers but returns no data

**Solutions**:
- Verify raster datasource ID is correct in config
- Check if raster timeseries exist for the model and parameters
- Verify date range is within raster data coverage
- Check API authentication and permissions

## References

- Main implementation: `src/lake_evaporation/raster_fetcher.py`
- API client: `src/lake_evaporation/api/raster.py`
- Tests: `tests/test_raster_fallback.py`
- Configuration: `config.json.example`
