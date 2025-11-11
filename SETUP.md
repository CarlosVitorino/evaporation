# Setup Guide

Quick guide to set up and test the Lake Evaporation application.

## 1. Setup Configuration

### Option A: Using Environment Variables (Recommended for Development)

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

Update the following in `.env`:
```bash
API_USERNAME=your_actual_username
API_PASSWORD=your_actual_password
```

### Option B: Using Configuration File

```bash
# Copy the example file
cp config.json.example config.json

# Edit config.json with your credentials
nano config.json
```

Update the authentication section in `config.json`:
```json
"authentication": {
  "username": "your_actual_username",
  "password": "your_actual_password"
}
```

**Note:** Environment variables in `.env` will override values in `config.json`.

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## 3. Test API Connection

Run the test script to verify your API credentials work:

```bash
python test_api.py
```

This will:
- ✓ Test authentication
- ✓ Fetch organizations
- ✓ Fetch locations
- ✓ Fetch time series
- ✓ Check for lake evaporation metadata

If successful, you'll see:
```
✓ All API tests passed successfully!
```

## 4. Run the Application

### Basic Usage

Calculate evaporation for yesterday (default):
```bash
python -m src.lake_evaporation.main
```

### Calculate for Specific Date

```bash
python -m src.lake_evaporation.main --date 2024-01-15
```

### Use Custom Configuration

```bash
python -m src.lake_evaporation.main --config my_config.json
```

### View Help

```bash
python -m src.lake_evaporation.main --help
```

## 5. Docker Usage (Optional)

Build and run with Docker:

```bash
# Build image
docker build -t lake-evaporation .

# Run container
docker run --rm \
  --env-file .env \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/logs:/app/logs \
  lake-evaporation
```

## Troubleshooting

### Authentication Failed

- Verify your username/password in `.env` or `config.json`
- Check that the API base URL is correct
- Test with the `test_api.py` script

### No Lake Evaporation Locations Found

The application looks for time series with `lakeEvaporation` metadata. Make sure:
- Your time series have the metadata field configured
- The metadata contains the required sensor references
- Run `test_api.py` to see how many time series have the metadata

### Missing Data

Check the logs in `logs/lake_evaporation.log` for detailed information about:
- Which data points are missing
- Unit conversion issues
- Validation errors

## File Structure

```
lake-evaporation/
├── .env                          # Your credentials (DO NOT COMMIT)
├── config.json                   # Your configuration (DO NOT COMMIT)
├── test_api.py                   # API test script
├── logs/                         # Application logs
│   └── lake_evaporation.log
├── src/lake_evaporation/         # Application code
│   └── main.py                   # Main entry point
└── README.md                     # Full documentation
```

## Next Steps

1. **Test the API** - Run `python test_api.py`
2. **Configure metadata** - Ensure time series have `lakeEvaporation` metadata
3. **Run the app** - Execute `python -m src.lake_evaporation.main`
4. **Check logs** - Review `logs/lake_evaporation.log` for details
5. **Verify results** - Check that evaporation values were written back to the API

## Quick Development Test

For a quick test with hardcoded data (no API required):

```bash
# Run the algorithm test
pytest tests/test_evaporation.py -v

# Run the processor test
pytest tests/test_processor.py -v
```

This verifies the calculation algorithms work correctly without needing API access.
