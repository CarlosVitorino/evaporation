"""
Integration tests for the complete evaporation calculation workflow.

Tests the full pipeline from data aggregation to evaporation calculation.
"""

import pytest  # type: ignore
import json
from pathlib import Path
from datetime import datetime

from src.lake_evaporation.processing import DataProcessor
from src.lake_evaporation.algorithms import EvaporationCalculator, SunshineCalculator
from src.lake_evaporation.models import WeatherData, LocationData


@pytest.fixture
def sample_data():
    """Load sample sensor data."""
    data_file = Path(__file__).parent / "fixtures" / "sample_data.json"
    with open(data_file) as f:
        return json.load(f)


class TestDataPipeline:
    """Test complete data processing pipeline."""

    def test_full_aggregation_pipeline(self, sample_data):
        """Test aggregation from raw sensor data to daily values."""
        processor = DataProcessor()

        # Aggregate the data
        aggregates = processor.calculate_daily_aggregates(sample_data["sensor_data"])

        # Verify all required fields are present
        required_fields = ["t_min", "t_max", "rh_min", "rh_max", "wind_speed_avg", "air_pressure_avg"]
        for field in required_fields:
            assert field in aggregates, f"Missing required field: {field}"

        # Check values match expected (from sample_data.json)
        expected = sample_data["expected_aggregates"]
        assert abs(aggregates["t_min"] - expected["t_min"]) < 0.1
        assert abs(aggregates["t_max"] - expected["t_max"]) < 0.1
        assert abs(aggregates["rh_min"] - expected["rh_min"]) < 0.1
        assert abs(aggregates["rh_max"] - expected["rh_max"]) < 0.1

    def test_unit_conversion_pipeline(self, sample_data):
        """Test unit conversion in the pipeline."""
        processor = DataProcessor()

        # Aggregate
        aggregates = processor.calculate_daily_aggregates(sample_data["sensor_data"])

        # Convert units (from Celsius to Fahrenheit, for example)
        source_units = {
            "temperature": "celsius",
            "wind_speed": "km/h",
            "air_pressure": "kPa"
        }
        converted = processor.convert_units(aggregates, source_units)

        # Values should be the same since source and target units match
        assert aggregates["t_min"] == converted["t_min"]
        assert aggregates["wind_speed_avg"] == converted["wind_speed_avg"]

    def test_validation_pipeline(self, sample_data):
        """Test data validation in the pipeline."""
        processor = DataProcessor()

        # Aggregate
        aggregates = processor.calculate_daily_aggregates(sample_data["sensor_data"])

        # Validate
        is_valid, errors = processor.validate_aggregates(aggregates)

        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_data_completeness_check(self, sample_data):
        """Test checking for complete sensor data."""
        processor = DataProcessor()

        # Check with complete data
        is_complete = processor.check_data_completeness(sample_data["sensor_data"])
        assert is_complete

        # Check with incomplete data
        incomplete_data = {
            "temperature": sample_data["sensor_data"]["temperature"],
            "humidity": sample_data["sensor_data"]["humidity"]
            # Missing wind_speed and air_pressure
        }
        is_complete = processor.check_data_completeness(incomplete_data)
        assert not is_complete


class TestEvaporationPipeline:
    """Test complete evaporation calculation pipeline."""

    def test_full_evaporation_calculation(self, sample_data):
        """Test complete workflow from sensor data to evaporation result."""
        processor = DataProcessor()
        calculator = EvaporationCalculator()

        # Step 1: Aggregate data
        aggregates = processor.calculate_daily_aggregates(sample_data["sensor_data"])

        # Step 2: Validate data
        is_valid, errors = processor.validate_aggregates(aggregates)
        assert is_valid, f"Data validation failed: {errors}"

        # Step 3: Calculate evaporation
        location_metadata = sample_data["location_metadata"]
        date = datetime(2024, 6, 21)  # Summer solstice

        evaporation = calculator.calculate_with_metadata(
            aggregates=aggregates,
            location_metadata=location_metadata,
            date=date,
            albedo=0.23
        )

        # Verify result is reasonable
        assert evaporation > 0, "Evaporation should be positive"
        assert evaporation < 20, "Evaporation should be less than 20 mm/day (sanity check)"

    def test_evaporation_with_missing_sunshine(self, sample_data):
        """Test evaporation calculation when sunshine hours are missing."""
        processor = DataProcessor()
        calculator = EvaporationCalculator()

        # Aggregate data
        aggregates = processor.calculate_daily_aggregates(sample_data["sensor_data"])

        # Remove sunshine hours
        aggregates.pop("sunshine_hours", None)

        # Should still work with 0 sunshine hours
        location_metadata = sample_data["location_metadata"]
        date = datetime(2024, 6, 21)

        evaporation = calculator.calculate_with_metadata(
            aggregates={**aggregates, "sunshine_hours": 0},
            location_metadata=location_metadata,
            date=date,
            albedo=0.23
        )

        assert evaporation > 0

    def test_sunshine_calculation_from_radiation(self, sample_data):
        """Test calculating sunshine hours from global radiation."""
        sunshine_calc = SunshineCalculator(a=0.25, b=0.5)

        # Calculate sunshine from radiation data
        radiation_data = sample_data["sensor_data"]["global_radiation"]
        location = sample_data["location_metadata"]["location"]
        day_number = 172  # June 21

        sunshine_hours = sunshine_calc.calculate_from_data_points(
            radiation_data=radiation_data,
            latitude=location["latitude"],
            day_number=day_number
        )

        # Should be a reasonable value
        assert sunshine_hours >= 0
        assert sunshine_hours <= 24


class TestValidationExample:
    """Test against the Excel validation example."""

    def test_validation_example_from_excel(self):
        """
        Test against validation example from ShuttleworthLakeEvaporation.xlsm.

        Input:
            Tmax = 33°C, Tmin = 17°C
            RHmax = 60%, RHmin = 25%
            u10 = 25 km/h, n = 16 hours
            P = 99.9 kPa
            Latitude = 51°, Altitude = 23m
            Day number = 170

        Expected output:
            EVlake ≈ 9.88 mm/day
        """
        calculator = EvaporationCalculator()

        aggregates = {
            "t_min": 17.0,
            "t_max": 33.0,
            "rh_min": 25.0,
            "rh_max": 60.0,
            "wind_speed_avg": 25.0,
            "air_pressure_avg": 99.9,
            "sunshine_hours": 16.0,
        }

        location_metadata = {
            "location": {
                "latitude": 51.0,
                "altitude": 23.0,
            }
        }

        date = datetime(2024, 6, 19)  # Day 170

        evaporation = calculator.calculate_with_metadata(
            aggregates=aggregates,
            location_metadata=location_metadata,
            date=date,
            albedo=0.23
        )

        # Allow 5% tolerance
        expected = 9.88
        tolerance = expected * 0.05
        assert abs(evaporation - expected) < tolerance, \
            f"Expected {expected} ± {tolerance}, got {evaporation:.2f}"
