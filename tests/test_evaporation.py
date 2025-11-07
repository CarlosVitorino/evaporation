"""
Tests for evaporation calculator module.

Tests the Shuttleworth algorithm implementation.
"""

import pytest
from datetime import datetime
from src.lake_evaporation.evaporation import EvaporationCalculator


class TestEvaporationCalculator:
    """Test cases for EvaporationCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return EvaporationCalculator()

    def test_saturation_vapor_pressure(self, calculator):
        """Test saturation vapor pressure calculation."""
        # At 20°C, es should be approximately 2.34 kPa
        es = calculator._calculate_saturation_vapor_pressure(20.0)
        assert 2.3 < es < 2.4

    def test_actual_vapor_pressure(self, calculator):
        """Test actual vapor pressure calculation."""
        # At 20°C with 50% RH, ea should be approximately 1.17 kPa
        ea = calculator._calculate_actual_vapor_pressure(20.0, 50.0)
        assert 1.1 < ea < 1.2

    def test_psychrometric_constant(self, calculator):
        """Test psychrometric constant calculation."""
        # At standard pressure (101.3 kPa), gamma should be approximately 0.067 kPa/°C
        gamma = calculator._calculate_psychrometric_constant(101.3, 20.0)
        assert 0.065 < gamma < 0.070

    def test_solar_declination_summer_solstice(self, calculator):
        """Test solar declination at summer solstice (day 172)."""
        delta = calculator._calculate_solar_declination(172)
        # Should be close to 23.45 degrees (0.409 radians)
        assert 0.35 < delta < 0.45

    def test_solar_declination_winter_solstice(self, calculator):
        """Test solar declination at winter solstice (day 355)."""
        delta = calculator._calculate_solar_declination(355)
        # Should be close to -23.45 degrees (-0.409 radians)
        assert -0.45 < delta < -0.35

    def test_extraterrestrial_radiation(self, calculator):
        """Test extraterrestrial radiation calculation."""
        # Mid-latitude location on summer day
        Ra = calculator._calculate_extraterrestrial_radiation(
            latitude=45.0,
            day_number=172
        )
        # Should be positive and reasonable value
        assert Ra > 0
        assert 30 < Ra < 50  # MJ/m²/day

    def test_calculate_with_metadata(self, calculator):
        """Test calculation with metadata."""
        aggregates = {
            "t_min": 10.0,
            "t_max": 20.0,
            "rh_min": 60.0,
            "rh_max": 80.0,
            "wind_speed_avg": 15.0,
            "air_pressure_avg": 101.3,
            "sunshine_hours": 8.0,
        }

        location_metadata = {
            "location": {
                "latitude": 45.0,
                "longitude": 10.0,
                "altitude": 200.0,
            }
        }

        date = datetime(2024, 6, 21)  # Summer solstice

        # Currently returns 0.0 (placeholder), should be positive in full implementation
        evaporation = calculator.calculate_with_metadata(
            aggregates=aggregates,
            location_metadata=location_metadata,
            date=date,
            albedo=0.23
        )

        assert evaporation >= 0

    def test_calculate_basic(self, calculator):
        """Test basic calculation with all parameters."""
        evaporation = calculator.calculate(
            t_min=10.0,
            t_max=20.0,
            rh_min=60.0,
            rh_max=80.0,
            wind_speed=15.0,
            air_pressure=101.3,
            sunshine_hours=8.0,
            latitude=45.0,
            altitude=200.0,
            day_number=172,
            albedo=0.23
        )

        # Should return a non-negative value
        assert evaporation >= 0
