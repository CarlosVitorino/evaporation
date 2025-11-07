# Lake Evaporation Estimation System

A Python-based system to estimate lake evaporation based on sensor observations using the Shuttleworth algorithm.

## Overview

This system calculates daily lake evaporation for multiple locations by:
1. Fetching sensor data from the datasphere API
2. Aggregating daily min/max temperature and humidity, average wind speed and air pressure
3. Calculating or estimating sunshine hours
4. Applying the Shuttleworth algorithm
5. Writing results back to the datasphere

## Features

- **Automated Daily Calculations**: Runs daily (typically at 1 AM) to process previous day's data
- **Multiple Location Support**: Processes all locations with `lakeEvaporation` tag
- **Flexible Data Sources**:
  - Direct sunshine hours measurement
  - Calculated from global radiation (Ångström-Prescott method)
  - Estimated from cloud cover data
- **Unit Conversion**: Automatic conversion of sensor data to required units
- **Error Handling**: Comprehensive logging and error handling
- **Docker Support**: Containerized for easy deployment

## Project Structure

```
lake-evaporation/
├── src/
│   └── lake_evaporation/
│       ├── main.py               # Main entry point
│       ├── config.py             # Configuration management
│       ├── logger.py             # Logging setup
│       ├── api_client.py         # API client with JWT auth
│       ├── discovery.py          # Time series discovery
│       ├── data_fetcher.py       # Data fetching
│       ├── processor.py          # Data processing & aggregation
│       ├── evaporation.py        # Shuttleworth algorithm
│       ├── sunshine.py           # Ångström-Prescott method
│       └── writer.py             # Result writing
├── tests/                        # Test files
├── logs/                         # Log output directory
├── docs/                         # Documentation
├── config.json.example           # Example configuration
├── .env.example                  # Example environment variables
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
└── README.md                     # This file
```

## Installation

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd lake-evaporation
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
cp config.json.example config.json
# Edit .env and config.json with your settings
```

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t lake-evaporation:latest .
```

2. Run the container:
```bash
docker run -d \
  --name lake-evaporation \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/logs:/app/logs \
  -e API_JWT_TOKEN=your_token_here \
  lake-evaporation:latest
```

## Configuration

### Environment Variables (.env)

```bash
# API Configuration
API_BASE_URL=https://api.datasphere.example.com
API_JWT_TOKEN=your_jwt_token_here

# Configuration
CONFIG_FILE=config.json

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/lake_evaporation.log
```

### Configuration File (config.json)

See `config.json.example` for the complete structure. Key sections:

- **api**: API endpoint configuration
- **processing**: Timezone and scheduling settings
- **constants**: Physical constants (albedo, Ångström-Prescott coefficients)
- **units**: Expected units for sensor data

## Usage

### Command Line

Run for previous day (default):
```bash
python -m src.lake_evaporation.main
```

Run for specific date:
```bash
python -m src.lake_evaporation.main --date 2024-06-21
```

Use custom config file:
```bash
python -m src.lake_evaporation.main --config /path/to/config.json
```

### KiDSM Integration

The system is designed to be scheduled via KiDSM (Kisters Distributed Service Management). Configure KiDSM to run the container daily at the specified hour (default: 1 AM).

## Time Series Metadata Format

Each location's time series should include the following metadata:

```json
{
  "lakeEvaporation": {
    "Temps": "tsId(temperature_series_id)",
    "RHTs": "tsId(humidity_series_id)",
    "WSpeedTs": "tsId(wind_speed_series_id)",
    "AirPressureTs": "tsId(pressure_series_id)",
    "hoursOfSunshineTs": "tsId(sunshine_series_id)",
    "globalRadiationTs": "tsId(radiation_series_id)"
  }
}
```

Supported reference formats:
- `tsId(123)` - Direct time series ID
- `tsPath(/path/to/series)` - Time series path
- `exchangeId(abc123)` - Exchange ID

## Algorithm

The system implements the **Shuttleworth algorithm** for lake evaporation, which requires:

### Required Inputs
- **Tmin, Tmax**: Daily minimum/maximum temperature (°C)
- **RHmin, RHmax**: Daily minimum/maximum relative humidity (%)
- **Wind speed**: Daily average wind speed at 10m (km/h)
- **Air pressure**: Daily average air pressure at station height (kPa)
- **Sunshine hours**: Actual hours of sunshine (hours)

### Location Parameters
- **Latitude**: Location latitude (degrees)
- **Altitude**: Station elevation (meters)
- **Albedo**: Surface albedo (default: 0.23 for water)

### Output
- **Evaporation**: Daily lake evaporation (mm/day)

See `docs/ALGORITHM.md` for detailed algorithm documentation.

## Testing

Run tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src/lake_evaporation tests/
```

## Logging

Logs are written to both console and file (`logs/lake_evaporation.log`).

Log levels:
- **INFO**: Progress and summary information
- **WARNING**: Missing data or validation issues
- **ERROR**: Processing failures
- **DEBUG**: Detailed diagnostic information

## Development Status

### Phase 1 (Current): Project Setup ✓
- Project structure created
- Core modules with skeleton code
- Configuration system
- Docker containerization
- Basic testing framework

### Phase 2 (Next): Algorithm Implementation
- Complete Shuttleworth algorithm implementation
- Excel algorithm integration
- Raster data extraction for missing values
- Comprehensive testing

### Phase 3: Production Deployment
- KiDSM integration
- Production configuration
- Monitoring and alerting
- Documentation

## Error Handling

The system handles various error scenarios:
- **Missing sensor data**: Logged to file, location skipped
- **Invalid data ranges**: Validation errors logged
- **API failures**: Retry logic with exponential backoff
- **Incomplete metadata**: Location skipped with warning

## Contributing

This is an internal company project. For questions or issues, contact the development team.

## License

Internal company use only.

## Support

For issues or questions:
1. Check the logs in `logs/lake_evaporation.log`
2. Review the configuration in `config.json`
3. Contact the development team

## Version History

- **v0.1.0** (Phase 1): Initial project structure and setup
