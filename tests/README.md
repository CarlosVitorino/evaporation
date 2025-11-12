# Tests

Comprehensive test suite for the Lake Evaporation application.

## Test Structure

```
tests/
├── conftest.py                  # Shared fixtures and pytest configuration
├── fixtures/                    # Test data files
│   └── sample_data.json        # Sample sensor data for tests
├── test_algorithms.py          # Unit tests for calculation algorithms
├── test_processing.py          # Unit tests for data processing
├── test_api_connection.py      # Integration tests for API connectivity
└── test_integration.py         # Integration tests for full workflow
```

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
# Test algorithms only
pytest tests/test_algorithms.py -v

# Test processing only
pytest tests/test_processing.py -v

# Test API connection (requires credentials)
pytest tests/test_api_connection.py -v

# Test full integration
pytest tests/test_integration.py -v
```

### Run by Test Type

```bash
# Run only unit tests (no external dependencies)
pytest tests/test_algorithms.py tests/test_processing.py -v

# Run only integration tests (requires API access)
pytest tests/test_api_connection.py -v
```

### Run Specific Test

```bash
# Run single test by name
pytest tests/test_algorithms.py::TestShuttleworthCalculator::test_validation_example -v

# Run all tests in a class
pytest tests/test_integration.py::TestEvaporationPipeline -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src/lake_evaporation --cov-report=html
```

## Test Categories

### Unit Tests (No External Dependencies)

**test_algorithms.py**
- Tests Shuttleworth calculation algorithm
- Tests sunshine hours calculation
- Tests evaporation calculator facade
- Validates against Excel reference example

**test_processing.py**
- Tests data aggregation
- Tests unit conversions
- Tests data validation
- Tests quality checks

### Integration Tests

**test_integration.py**
- Tests complete data pipeline
- Tests workflow from raw data to evaporation result
- Tests handling of missing data
- Tests sunshine calculation from radiation

**test_api_connection.py**
- Tests API authentication
- Tests fetching organizations, locations, and time series
- Tests finding lake evaporation metadata
- **Requires:** Valid API credentials in `.env` or `config.json`

## Prerequisites

### For Unit Tests

```bash
pip install pytest
```

### For Integration Tests (API)

1. Create configuration:
```bash
cp .env.example .env
# Edit .env with your API credentials
```

2. Run API tests:
```bash
pytest tests/test_api_connection.py -v
```

## Test Data

Sample data is stored in `fixtures/sample_data.json` and includes:
- Representative sensor measurements
- Expected aggregation results
- Location metadata
- Time series references

## Writing New Tests

### Unit Test Example

```python
# In test_algorithms.py or test_processing.py
def test_my_feature():
    """Test description."""
    # Arrange
    input_data = {...}

    # Act
    result = my_function(input_data)

    # Assert
    assert result == expected
```

### Integration Test Example

```python
# In test_integration.py
def test_my_workflow(sample_data):
    """Test description using shared fixture."""
    # Use sample_data fixture
    processor = DataProcessor()
    result = processor.process(sample_data)

    assert result is not None
```

### API Test Example

```python
# In test_api_connection.py
def test_my_api_call(api_client):
    """Test description requiring API access."""
    # Use api_client fixture (already authenticated)
    data = api_client.get_something()

    assert data is not None
```

## Continuous Integration

These tests can be run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run unit tests
  run: pytest tests/test_algorithms.py tests/test_processing.py -v

- name: Run integration tests
  run: pytest tests/test_integration.py -v
  env:
    API_USERNAME: ${{ secrets.API_USERNAME }}
    API_PASSWORD: ${{ secrets.API_PASSWORD }}
```

## Troubleshooting

### Import Errors

Make sure you're running from the project root:
```bash
cd /path/to/lake-evaporation
pytest tests/
```

### API Tests Failing

Check your credentials:
```bash
# View current configuration
cat .env | grep API_

# Test API connection separately
python -c "from src.lake_evaporation.core import Config; c = Config(); print(c.api_base_url)"
```

### Fixture Not Found

Make sure `conftest.py` is in the tests directory and `sample_data.json` exists in `fixtures/`.
