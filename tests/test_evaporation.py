"""
Tests for evaporation calculator module.

Tests the Shuttleworth algorithm implementation.
"""

import pytest  # type: ignore
from datetime import datetime
from src.lake_evaporation.algorithms import EvaporationCalculator, ShuttleworthCalculator


class TestEvaporationCalculator:
    """Test cases for EvaporationCalculator facade."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return EvaporationCalculator()

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

        evaporation = calculator.calculate_with_metadata(
            aggregates=aggregates,
            location_metadata=location_metadata,
            date=date,
            albedo=0.23
        )

        # Should return a positive value
        assert evaporation > 0

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

        # Should return a positive value
        assert evaporation > 0

    def test_calculate_with_components(self, calculator):
        """Test calculation with components returns detailed results."""
        components = calculator.calculate_with_components(
            t_min=17.0,
            t_max=33.0,
            rh_min=25.0,
            rh_max=60.0,
            wind_speed=25.0,
            air_pressure=99.9,
            sunshine_hours=16.0,
            latitude=51.0,
            altitude=23.0,
            day_number=170,
            albedo=0.23
        )

        # Verify components are present
        assert components.evaporation_total > 0
        assert components.aerodynamic_component > 0
        assert components.radiation_component > 0
        assert components.evaporation_total == (
            components.aerodynamic_component + components.radiation_component
        )


class TestShuttleworthCalculator:
    """Test cases for ShuttleworthCalculator core calculation engine."""

    def test_saturation_vapor_pressure(self):
        """Test saturation vapor pressure calculation."""
        # At 20°C, es should be approximately 2.34 kPa
        es = ShuttleworthCalculator._calculate_saturation_vapor_pressure(20.0)
        assert 2.3 < es < 2.4

    def test_vapor_pressures(self):
        """Test vapor pressure calculations."""
        es_tmax, es_tmin, es, ea, vpd = ShuttleworthCalculator._calculate_vapor_pressures(
            t_max=33.0,
            t_min=17.0,
            rh_max=60.0,
            rh_min=25.0
        )

        # All values should be positive
        assert es_tmax > 0
        assert es_tmin > 0
        assert es > 0
        assert ea > 0
        assert vpd > 0

        # Saturation at Tmax should be greater than at Tmin
        assert es_tmax > es_tmin

        # Mean saturation should be between min and max
        assert es_tmin < es < es_tmax

        # VPD should be es - ea
        assert abs(vpd - (es - ea)) < 0.01

    def test_psychrometric_constant(self):
        """Test psychrometric constant calculation."""
        # At pressure 99.9 kPa
        gamma = ShuttleworthCalculator._calculate_psychrometric_constant(99.9)
        assert 0.065 < gamma < 0.070

    def test_slope_vapor_pressure_curve(self):
        """Test slope of vapor pressure curve."""
        # At 25°C mean temperature
        delta = ShuttleworthCalculator._calculate_slope_vapor_pressure_curve(25.0)
        # Should be positive and reasonable
        assert 0.1 < delta < 0.3

    def test_wind_speed_adjustment(self):
        """Test wind speed adjustment from 10m to 2m height."""
        u10_ms, u2 = ShuttleworthCalculator._adjust_wind_speed(25.0)  # km/h

        # u10_ms should be ~6.94 m/s
        assert 6.8 < u10_ms < 7.0

        # u2 should be less than u10_ms (wind is slower closer to surface)
        assert u2 < u10_ms
        assert 5.0 < u2 < 5.3

    def test_solar_declination_summer_solstice(self):
        """Test solar declination at summer solstice (day 172)."""
        delta = ShuttleworthCalculator._calculate_solar_declination(172)
        # Should be close to 23.45 degrees (0.409 radians)
        assert 0.35 < delta < 0.45

    def test_solar_declination_winter_solstice(self):
        """Test solar declination at winter solstice (day 355)."""
        delta = ShuttleworthCalculator._calculate_solar_declination(355)
        # Should be close to -23.45 degrees (-0.409 radians)
        assert -0.45 < delta < -0.35

    def test_extraterrestrial_radiation(self):
        """Test extraterrestrial radiation calculation."""
        # Mid-latitude location on summer day
        ra, n_max, omega_s = ShuttleworthCalculator._calculate_extraterrestrial_radiation(
            latitude=45.0,
            day_number=172
        )

        # Ra should be positive and reasonable
        assert ra > 0
        assert 30 < ra < 50  # MJ/m²/day

        # Day length should be positive and less than 24 hours
        assert 0 < n_max < 24

        # Sunset hour angle should be positive
        assert omega_s > 0

    def test_solar_radiation(self):
        """Test solar radiation calculations."""
        ra, n_max, n_n, rs, rso = ShuttleworthCalculator._calculate_solar_radiation(
            latitude=51.0,
            altitude=23.0,
            day_number=170,
            sunshine_hours=16.0
        )

        # All values should be positive
        assert ra > 0
        assert n_max > 0
        assert rs > 0
        assert rso > 0

        # Sunshine ratio should be between 0 and 1
        assert 0 <= n_n <= 1

        # Solar radiation should be less than extraterrestrial
        assert rs <= ra

    def test_net_radiation(self):
        """Test net radiation calculations."""
        rns, rnl, rn = ShuttleworthCalculator._calculate_net_radiation(
            rs=30.0,
            rso=35.0,
            t_max=33.0,
            t_min=17.0,
            ea=1.75,
            albedo=0.23
        )

        # Net shortwave should be positive
        assert rns > 0

        # Net longwave should be positive (outgoing)
        assert rnl > 0

        # Net radiation should be positive during day
        assert rn > 0

        # Net radiation should equal shortwave minus longwave
        assert abs(rn - (rns - rnl)) < 0.01

    def test_evaporation_components(self):
        """Test evaporation component calculations."""
        # Aerodynamic component
        ea = ShuttleworthCalculator._calculate_aerodynamic_component(
            gamma=0.066,
            u2=5.19,
            vpd=1.73,
            lambda_v_mg=0.625
        )
        assert ea > 0

        # Radiation component
        er = ShuttleworthCalculator._calculate_radiation_component(
            delta=0.189,
            rn=17.88,
            lambda_v_mg=0.625
        )
        assert er > 0

    def test_validation_example(self):
        """
        Test against validation example from Excel file.

        Input:
            Tmax = 33°C, Tmin = 17°C
            RHmax = 60%, RHmin = 25%
            u10 = 25 km/h, n = 16 hours
            P = 99.9 kPa
            Latitude = 51°, Altitude = 23m
            Day number = 170, Albedo = 0.23

        Expected output:
            EVlake ≈ 9.88 mm/day
            Ea ≈ 4.48 mm/day (aerodynamic)
            Er ≈ 5.40 mm/day (radiation)
        """
        components = ShuttleworthCalculator.calculate_with_components(
            t_max=33.0,
            t_min=17.0,
            rh_max=60.0,
            rh_min=25.0,
            u10=25.0,
            sunshine_hours=16.0,
            pressure=99.9,
            latitude=51.0,
            altitude=23.0,
            day_number=170,
            albedo=0.23
        )

        # Test total evaporation (allow 5% tolerance)
        assert 9.4 < components.evaporation_total < 10.4, \
            f"Expected ~9.88 mm/day, got {components.evaporation_total:.2f}"

        # Test aerodynamic component (allow 10% tolerance)
        assert 4.0 < components.aerodynamic_component < 5.0, \
            f"Expected ~4.48 mm/day, got {components.aerodynamic_component:.2f}"

        # Test radiation component (allow 10% tolerance)
        assert 4.9 < components.radiation_component < 5.9, \
            f"Expected ~5.40 mm/day, got {components.radiation_component:.2f}"

        # Verify sum
        assert abs(components.evaporation_total -
                   (components.aerodynamic_component + components.radiation_component)) < 0.01
