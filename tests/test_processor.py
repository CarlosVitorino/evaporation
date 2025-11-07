"""
Tests for data processor module.

Tests aggregation, unit conversion, and validation functionality.
"""

import pytest
from src.lake_evaporation.processor import DataProcessor


class TestDataProcessor:
    """Test cases for DataProcessor."""

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return DataProcessor()

    @pytest.fixture
    def sample_data(self):
        """Sample sensor data for testing."""
        return {
            "temperature": [
                {"timestamp": "2024-01-01T00:00:00", "value": 10.0},
                {"timestamp": "2024-01-01T06:00:00", "value": 15.0},
                {"timestamp": "2024-01-01T12:00:00", "value": 20.0},
                {"timestamp": "2024-01-01T18:00:00", "value": 12.0},
            ],
            "humidity": [
                {"timestamp": "2024-01-01T00:00:00", "value": 80.0},
                {"timestamp": "2024-01-01T06:00:00", "value": 70.0},
                {"timestamp": "2024-01-01T12:00:00", "value": 60.0},
                {"timestamp": "2024-01-01T18:00:00", "value": 75.0},
            ],
            "wind_speed": [
                {"timestamp": "2024-01-01T00:00:00", "value": 10.0},
                {"timestamp": "2024-01-01T06:00:00", "value": 15.0},
                {"timestamp": "2024-01-01T12:00:00", "value": 20.0},
                {"timestamp": "2024-01-01T18:00:00", "value": 12.0},
            ],
            "air_pressure": [
                {"timestamp": "2024-01-01T00:00:00", "value": 101.0},
                {"timestamp": "2024-01-01T06:00:00", "value": 101.2},
                {"timestamp": "2024-01-01T12:00:00", "value": 101.1},
                {"timestamp": "2024-01-01T18:00:00", "value": 101.3},
            ],
        }

    def test_calculate_daily_aggregates(self, processor, sample_data):
        """Test calculation of daily aggregates."""
        aggregates = processor.calculate_daily_aggregates(sample_data)

        assert "t_min" in aggregates
        assert "t_max" in aggregates
        assert "rh_min" in aggregates
        assert "rh_max" in aggregates
        assert "wind_speed_avg" in aggregates
        assert "air_pressure_avg" in aggregates

        assert aggregates["t_min"] == 10.0
        assert aggregates["t_max"] == 20.0
        assert aggregates["rh_min"] == 60.0
        assert aggregates["rh_max"] == 80.0

    def test_temperature_conversion_celsius_to_fahrenheit(self, processor):
        """Test temperature conversion from Celsius to Fahrenheit."""
        celsius = 20.0
        fahrenheit = processor._convert_temperature(celsius, "celsius", "fahrenheit")
        assert abs(fahrenheit - 68.0) < 0.01

    def test_temperature_conversion_fahrenheit_to_celsius(self, processor):
        """Test temperature conversion from Fahrenheit to Celsius."""
        fahrenheit = 68.0
        celsius = processor._convert_temperature(fahrenheit, "fahrenheit", "celsius")
        assert abs(celsius - 20.0) < 0.01

    def test_wind_speed_conversion_kmh_to_ms(self, processor):
        """Test wind speed conversion from km/h to m/s."""
        kmh = 36.0
        ms = processor._convert_wind_speed(kmh, "km/h", "m/s")
        assert abs(ms - 10.0) < 0.01

    def test_pressure_conversion_kpa_to_hpa(self, processor):
        """Test pressure conversion from kPa to hPa."""
        kpa = 101.3
        hpa = processor._convert_pressure(kpa, "kPa", "hPa")
        assert abs(hpa - 1013.0) < 0.1

    def test_validate_aggregates_valid(self, processor):
        """Test validation of valid aggregates."""
        aggregates = {
            "t_min": 10.0,
            "t_max": 20.0,
            "rh_min": 60.0,
            "rh_max": 80.0,
            "wind_speed_avg": 15.0,
            "air_pressure_avg": 101.3,
        }

        is_valid, errors = processor.validate_aggregates(aggregates)
        assert is_valid
        assert len(errors) == 0

    def test_validate_aggregates_missing_field(self, processor):
        """Test validation with missing field."""
        aggregates = {
            "t_min": 10.0,
            "t_max": 20.0,
            # Missing humidity fields
            "wind_speed_avg": 15.0,
            "air_pressure_avg": 101.3,
        }

        is_valid, errors = processor.validate_aggregates(aggregates)
        assert not is_valid
        assert len(errors) > 0

    def test_validate_aggregates_invalid_range(self, processor):
        """Test validation with invalid range."""
        aggregates = {
            "t_min": 20.0,  # Min higher than max
            "t_max": 10.0,
            "rh_min": 60.0,
            "rh_max": 80.0,
            "wind_speed_avg": 15.0,
            "air_pressure_avg": 101.3,
        }

        is_valid, errors = processor.validate_aggregates(aggregates)
        assert not is_valid
        assert any("t_min" in error for error in errors)
