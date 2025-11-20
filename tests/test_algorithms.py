"""
Tests for evaporation calculator module.

Tests the Shuttleworth algorithm implementation using the Excel reference file
(docs/ShuttleworthLakeEvaporation.xlsm) as the source of truth.
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
        assert evaporation > 0, "Evaporation should be positive"
        assert evaporation < 20, "Evaporation should be reasonable (< 20 mm/day)"

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
        assert evaporation > 0, "Evaporation should be positive"
        assert evaporation < 20, "Evaporation should be reasonable (< 20 mm/day)"

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
        assert components.evaporation_total > 0, "Total evaporation should be positive"
        assert components.aerodynamic_component > 0, "Aerodynamic component should be positive"
        assert components.radiation_component > 0, "Radiation component should be positive"
        assert abs(components.evaporation_total -
                   (components.aerodynamic_component + components.radiation_component)) < 0.0001, \
            "Total should equal sum of components"


class TestShuttleworthCalculatorBasicComponents:
    """Test cases for basic calculation components."""

    def test_saturation_vapor_pressure(self):
        """Test saturation vapor pressure calculation using Excel reference values."""
        # At 33°C (from Excel test case)
        es_33 = ShuttleworthCalculator._calculate_saturation_vapor_pressure(33.0)
        assert abs(es_33 - 5.030148) < 0.000001, \
            f"es(33°C) should be 5.030148 kPa, got {es_33:.6f}"

        # At 17°C (from Excel test case)
        es_17 = ShuttleworthCalculator._calculate_saturation_vapor_pressure(17.0)
        assert abs(es_17 - 1.937729) < 0.000001, \
            f"es(17°C) should be 1.937729 kPa, got {es_17:.6f}"

        # At 20°C (sanity check)
        es_20 = ShuttleworthCalculator._calculate_saturation_vapor_pressure(20.0)
        assert 2.3 < es_20 < 2.4, f"es(20°C) should be ~2.34 kPa, got {es_20:.2f}"

    def test_vapor_pressures(self):
        """Test vapor pressure calculations using Excel reference values."""
        es_tmax, es_tmin, es, ea, vpd = ShuttleworthCalculator._calculate_vapor_pressures(
            t_max=33.0,
            t_min=17.0,
            rh_max=60.0,
            rh_min=25.0
        )

        # Validate against Excel values
        assert abs(es_tmax - 5.030148) < 0.000001, f"es(Tmax) mismatch: expected 5.030148, got {es_tmax:.6f}"
        assert abs(es_tmin - 1.937729) < 0.000001, f"es(Tmin) mismatch: expected 1.937729, got {es_tmin:.6f}"
        assert abs(es - 3.483939) < 0.000001, f"es (mean) mismatch: expected 3.483939, got {es:.6f}"
        assert abs(ea - 1.751261) < 0.000001, f"ea mismatch: expected 1.751261, got {ea:.6f}"
        assert abs(vpd - 1.732678) < 0.000001, f"VPD mismatch: expected 1.732678, got {vpd:.6f}"

        # Sanity checks
        assert es_tmax > es_tmin, "Saturation pressure at Tmax should be greater than at Tmin"
        assert es_tmin < es < es_tmax, "Mean saturation should be between min and max"
        assert abs(vpd - (es - ea)) < 0.000001, "VPD should equal es - ea"

    def test_psychrometric_constant(self):
        """Test psychrometric constant calculation using Excel reference."""
        # Excel test case: P = 99.9 kPa, γ = 0.066434 kPa/°C
        gamma = ShuttleworthCalculator._calculate_psychrometric_constant(99.9)
        assert abs(gamma - 0.066434) < 0.000001, \
            f"Psychrometric constant mismatch: expected 0.066434, got {gamma:.6f}"

    def test_slope_vapor_pressure_curve(self):
        """Test slope of vapor pressure curve using Excel reference."""
        # Excel test case: Tmean = 25°C, Δ = 0.18859 kPa/°C
        delta = ShuttleworthCalculator._calculate_slope_vapor_pressure_curve(25.0)
        assert abs(delta - 0.18859) < 0.00001, \
            f"Slope mismatch: expected 0.18859, got {delta:.5f}"

    def test_wind_speed_adjustment(self):
        """Test wind speed adjustment using Excel reference values."""
        # Excel test case: u10 = 25 km/h → 6.944444 m/s → u2 = 5.194444 m/s
        u10_ms, u2 = ShuttleworthCalculator._adjust_wind_speed(25.0)

        assert abs(u10_ms - 6.944444) < 0.000001, \
            f"u10 (m/s) mismatch: expected 6.944444, got {u10_ms:.6f}"
        assert abs(u2 - 5.194444) < 0.000001, \
            f"u2 mismatch: expected 5.194444, got {u2:.6f}"

        # Sanity check: u2 should be less than u10 (wind is slower closer to surface)
        assert u2 < u10_ms, "Wind speed at 2m should be less than at 10m"


class TestShuttleworthCalculatorSolarRadiation:
    """Test cases for solar radiation calculations."""

    def test_solar_declination_excel_reference(self):
        """Test solar declination using Excel reference value."""
        # Excel test case: day 170, δ = 0.408758 radians
        delta = ShuttleworthCalculator._calculate_solar_declination(170)
        assert abs(delta - 0.408758) < 0.000001, \
            f"Solar declination mismatch: expected 0.408758, got {delta:.6f}"

    def test_solar_declination_summer_solstice(self):
        """Test solar declination at summer solstice (day 172)."""
        delta = ShuttleworthCalculator._calculate_solar_declination(172)
        # Should be close to 23.45 degrees (0.409 radians)
        assert 0.35 < delta < 0.45, f"Summer solstice declination should be ~0.409 rad, got {delta:.3f}"

    def test_solar_declination_winter_solstice(self):
        """Test solar declination at winter solstice (day 355)."""
        delta = ShuttleworthCalculator._calculate_solar_declination(355)
        # Should be close to -23.45 degrees (-0.409 radians)
        assert -0.45 < delta < -0.35, f"Winter solstice declination should be ~-0.409 rad, got {delta:.3f}"

    def test_extraterrestrial_radiation_excel_reference(self):
        """Test extraterrestrial radiation using Excel reference values."""
        # Excel test case: latitude 51°, day 170
        # Expected: Ra = 41.738019 MJ/m²/day, N = 16.311642 hours, ωs = 2.135189 rad
        ra, n_max, omega_s = ShuttleworthCalculator._calculate_extraterrestrial_radiation(
            latitude=51.0,
            day_number=170
        )

        assert abs(ra - 41.738019) < 0.000001, \
            f"Ra mismatch: expected 41.738019, got {ra:.6f}"
        assert abs(n_max - 16.311642) < 0.000001, \
            f"N mismatch: expected 16.311642, got {n_max:.6f}"
        assert abs(omega_s - 2.135189) < 0.000001, \
            f"ωs mismatch: expected 2.135189, got {omega_s:.6f}"

    def test_extraterrestrial_radiation_sanity_checks(self):
        """Test extraterrestrial radiation with sanity checks."""
        # Mid-latitude location on summer day
        ra, n_max, omega_s = ShuttleworthCalculator._calculate_extraterrestrial_radiation(
            latitude=45.0,
            day_number=172
        )

        # Ra should be positive and reasonable
        assert ra > 0, "Ra should be positive"
        assert 30 < ra < 50, f"Ra should be 30-50 MJ/m²/day for summer mid-latitude, got {ra:.1f}"

        # Day length should be positive and less than 24 hours
        assert 0 < n_max < 24, f"Daylight hours should be 0-24, got {n_max:.1f}"

        # Sunset hour angle should be positive
        assert omega_s > 0, "Sunset hour angle should be positive"

    def test_solar_radiation_excel_reference(self):
        """Test solar radiation calculations using Excel reference values."""
        # Excel test case: latitude 51°, altitude 23m, day 170, n = 16 hours
        # Expected: Rs = 30.904801 MJ/m²/day, Rso = 31.322714 MJ/m²/day
        ra, n_max, n_n, rs, rso = ShuttleworthCalculator._calculate_solar_radiation(
            latitude=51.0,
            altitude=23.0,
            day_number=170,
            sunshine_hours=16.0
        )

        assert abs(ra - 41.738019) < 0.000001, f"Ra mismatch: expected 41.738019, got {ra:.6f}"
        assert abs(n_max - 16.311642) < 0.000001, f"N mismatch: expected 16.311642, got {n_max:.6f}"
        assert abs(n_n - 0.980894) < 0.000001, f"n/N mismatch: expected 0.980894, got {n_n:.6f}"
        assert abs(rs - 30.904801) < 0.000001, f"Rs mismatch: expected 30.904801, got {rs:.6f}"
        assert abs(rso - 31.322714) < 0.000001, f"Rso mismatch: expected 31.322714, got {rso:.6f}"

        # Sanity checks
        assert 0 <= n_n <= 1, f"Sunshine ratio should be 0-1, got {n_n:.3f}"
        assert rs <= ra, "Solar radiation should be less than extraterrestrial"


class TestShuttleworthCalculatorNetRadiation:
    """Test cases for net radiation calculations."""

    def test_net_radiation_excel_reference(self):
        """Test net radiation calculations using Excel reference values."""
        # Excel test case values
        # Expected: Rns = 23.796697, Rnl = 5.913087, Rn = 17.88361 MJ/m²/day
        rns, rnl, rn = ShuttleworthCalculator._calculate_net_radiation(
            rs=30.904801,
            rso=31.322714,
            t_max=33.0,
            t_min=17.0,
            ea=1.751261,
            albedo=0.23
        )

        assert abs(rns - 23.796697) < 0.000001, f"Rns mismatch: expected 23.796697, got {rns:.6f}"
        assert abs(rnl - 5.913087) < 0.000001, f"Rnl mismatch: expected 5.913087, got {rnl:.6f}"
        assert abs(rn - 17.88361) < 0.00001, f"Rn mismatch: expected 17.88361, got {rn:.5f}"

        # Sanity checks
        assert rns > 0, "Net shortwave radiation should be positive"
        assert rnl > 0, "Net longwave radiation should be positive (outgoing)"
        assert rn > 0, "Net radiation should be positive during day"
        assert abs(rn - (rns - rnl)) < 0.000001, "Net radiation should equal shortwave minus longwave"

    def test_net_radiation_components(self):
        """Test net radiation calculation logic."""
        rns, rnl, rn = ShuttleworthCalculator._calculate_net_radiation(
            rs=30.0,
            rso=35.0,
            t_max=33.0,
            t_min=17.0,
            ea=1.75,
            albedo=0.23
        )

        # Net shortwave should be positive
        assert rns > 0, "Net shortwave should be positive"

        # Net longwave should be positive (outgoing)
        assert rnl > 0, "Net longwave should be positive"

        # Net radiation should be positive during day
        assert rn > 0, "Net radiation should be positive"

        # Net radiation should equal shortwave minus longwave
        assert abs(rn - (rns - rnl)) < 0.000001, "Rn should equal Rns - Rnl"


class TestShuttleworthCalculatorEvaporationComponents:
    """Test cases for evaporation component calculations."""

    def test_aerodynamic_component_excel_reference(self):
        """Test aerodynamic component using Excel reference values."""
        # Excel test case: Ea = 4.482773 mm/day
        # Intermediate: aerodynamic term = 2.800868
        # Inputs: γ=0.066434, u2=5.194444, VPD=1.732678, λv(Δ+γ)=0.624807
        ea = ShuttleworthCalculator._calculate_aerodynamic_component(
            gamma=0.066434,
            u2=5.194444,
            vpd=1.732678,
            lambda_v_mg=0.624807
        )

        # Tolerance slightly higher due to accumulated rounding in Excel intermediate values
        assert abs(ea - 4.482773) < 0.0001, \
            f"Ea mismatch: expected 4.482773, got {ea:.6f}"
        assert ea > 0, "Aerodynamic component should be positive"

    def test_radiation_component_excel_reference(self):
        """Test radiation component using Excel reference values."""
        # Excel test case: Er = 5.397932 mm/day
        # Inputs: Δ=0.18859, Rn=17.88361, λv(Δ+γ)=0.624807
        er = ShuttleworthCalculator._calculate_radiation_component(
            delta=0.18859,
            rn=17.88361,
            lambda_v_mg=0.624807
        )

        # Tolerance slightly higher due to accumulated rounding in Excel intermediate values
        assert abs(er - 5.397932) < 0.00001, \
            f"Er mismatch: expected 5.397932, got {er:.6f}"
        assert er > 0, "Radiation component should be positive"


class TestShuttleworthCalculatorExcelValidation:
    """
    Complete validation tests against the Excel reference file.

    These tests verify that the implementation matches EXACTLY the Excel file
    (docs/ShuttleworthLakeEvaporation.xlsm) which is the source of truth.
    """

    def test_excel_validation_complete_with_all_intermediates(self):
        """
        Comprehensive validation test with ALL intermediate values from Excel.

        Test scenario from Excel file (docs/ShuttleworthLakeEvaporation.xlsm):

        Input parameters:
            Tmax = 33°C, Tmin = 17°C
            RHmax = 60%, RHmin = 25%
            u10 = 25 km/h, n = 16 hours
            P = 99.9 kPa
            Latitude = 51°, Altitude = 23m
            Day number = 170, Albedo = 0.23

        Expected outputs (from Excel):
            EVlake = 9.880705 mm/day
            Ea = 4.482773 mm/day
            Er = 5.397932 mm/day
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

        # Tolerance: ±0.000001 for exact match
        tolerance = 0.000001

        # --- STEP 1: Wind Speed ---
        assert abs(components.u10_ms - 6.944444) < tolerance, \
            f"u10 (m/s) mismatch: expected 6.944444, got {components.u10_ms:.6f}"
        assert abs(components.u2 - 5.194444) < tolerance, \
            f"u2 mismatch: expected 5.194444, got {components.u2:.6f}"

        # --- STEP 2: Vapor Pressures ---
        assert abs(components.es_tmax - 5.030148) < tolerance, \
            f"es(Tmax) mismatch: expected 5.030148, got {components.es_tmax:.6f}"
        assert abs(components.es_tmin - 1.937729) < tolerance, \
            f"es(Tmin) mismatch: expected 1.937729, got {components.es_tmin:.6f}"
        assert abs(components.es - 3.483939) < tolerance, \
            f"es mismatch: expected 3.483939, got {components.es:.6f}"
        assert abs(components.ea - 1.751261) < tolerance, \
            f"ea mismatch: expected 1.751261, got {components.ea:.6f}"
        assert abs(components.vpd - 1.732678) < tolerance, \
            f"VPD mismatch: expected 1.732678, got {components.vpd:.6f}"

        # --- STEP 3: Psychrometric Parameters ---
        assert abs(components.tmean - 25.0) < tolerance, \
            f"Tmean mismatch: expected 25.0, got {components.tmean:.6f}"
        assert abs(components.delta - 0.18859) < 0.00001, \
            f"Δ mismatch: expected 0.18859, got {components.delta:.5f}"
        assert abs(components.gamma - 0.066434) < tolerance, \
            f"γ mismatch: expected 0.066434, got {components.gamma:.6f}"
        assert abs(components.lambda_v_mg - 0.624807) < 0.000001, \
            f"λv(Δ+γ) mismatch: expected 0.624807, got {components.lambda_v_mg:.6f}"

        # --- STEP 4: Solar Radiation ---
        assert abs(components.ra - 41.738019) < tolerance, \
            f"Ra mismatch: expected 41.738019, got {components.ra:.6f}"
        assert abs(components.n - 16.311642) < tolerance, \
            f"N mismatch: expected 16.311642, got {components.n:.6f}"
        assert abs(components.sunshine_ratio - 0.980894) < tolerance, \
            f"n/N mismatch: expected 0.980894, got {components.sunshine_ratio:.6f}"
        assert abs(components.rs - 30.904801) < tolerance, \
            f"Rs mismatch: expected 30.904801, got {components.rs:.6f}"
        assert abs(components.rso - 31.322714) < tolerance, \
            f"Rso mismatch: expected 31.322714, got {components.rso:.6f}"

        # --- STEP 5: Net Radiation ---
        assert abs(components.rns - 23.796697) < tolerance, \
            f"Rns mismatch: expected 23.796697, got {components.rns:.6f}"
        assert abs(components.rnl - 5.913087) < tolerance, \
            f"Rnl mismatch: expected 5.913087, got {components.rnl:.6f}"
        assert abs(components.rn - 17.88361) < 0.00001, \
            f"Rn mismatch: expected 17.88361, got {components.rn:.5f}"

        # --- STEP 6: Evaporation Components ---
        assert abs(components.aerodynamic_component - 4.482773) < tolerance, \
            f"Ea mismatch: expected 4.482773, got {components.aerodynamic_component:.6f}"
        assert abs(components.radiation_component - 5.397932) < tolerance, \
            f"Er mismatch: expected 5.397932, got {components.radiation_component:.6f}"

        # --- STEP 7: Final Result ---
        assert abs(components.evaporation_total - 9.880705) < tolerance, \
            f"EVlake mismatch: expected 9.880705, got {components.evaporation_total:.6f}"

        # Verify sum (components should add up to total)
        calculated_sum = components.aerodynamic_component + components.radiation_component
        assert abs(components.evaporation_total - calculated_sum) < 0.0001, \
            f"Component sum mismatch! Ea + Er = {calculated_sum:.6f}, but EVlake = {components.evaporation_total:.6f}"

    def test_excel_validation_simple(self):
        """
        Simplified validation test for quick verification.

        Tests only the final evaporation output against Excel reference.
        """
        evaporation = ShuttleworthCalculator.calculate_lake_evaporation(
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

        # Expected: 9.880705 mm/day
        assert abs(evaporation - 9.880705) < 0.000001, \
            f"Evaporation mismatch: expected 9.880705, got {evaporation:.6f}"


class TestShuttleworthCalculatorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_sunshine_hours(self):
        """Test calculation with zero sunshine hours (nighttime/cloudy)."""
        components = ShuttleworthCalculator.calculate_with_components(
            t_max=25.0,
            t_min=15.0,
            rh_max=80.0,
            rh_min=50.0,
            u10=15.0,
            sunshine_hours=0.0,  # Zero sunshine
            pressure=101.3,
            latitude=45.0,
            altitude=200.0,
            day_number=180,
            albedo=0.23
        )

        # Should still calculate, but with lower evaporation
        assert components.evaporation_total > 0, "Evaporation should be positive even with zero sunshine"
        assert components.aerodynamic_component > 0, "Aerodynamic component should still be positive"
        assert components.radiation_component >= 0, "Radiation component should be non-negative"

    def test_high_wind_speed(self):
        """Test calculation with high wind speed."""
        components = ShuttleworthCalculator.calculate_with_components(
            t_max=25.0,
            t_min=15.0,
            rh_max=70.0,
            rh_min=40.0,
            u10=50.0,  # High wind (50 km/h)
            sunshine_hours=10.0,
            pressure=101.3,
            latitude=45.0,
            altitude=200.0,
            day_number=180,
            albedo=0.23
        )

        # Higher wind should increase aerodynamic component
        assert components.aerodynamic_component > 3.0, \
            "High wind should produce significant aerodynamic component"

    def test_extreme_hot_dry_conditions(self):
        """Test calculation with extreme hot and dry conditions."""
        components = ShuttleworthCalculator.calculate_with_components(
            t_max=45.0,  # Very hot
            t_min=30.0,
            rh_max=30.0,  # Very dry
            rh_min=10.0,
            u10=30.0,
            sunshine_hours=14.0,
            pressure=101.3,
            latitude=30.0,  # Desert latitude
            altitude=0.0,
            day_number=180,
            albedo=0.23
        )

        # Extreme conditions should produce high evaporation
        assert components.evaporation_total > 10.0, \
            f"Extreme conditions should produce high evaporation, got {components.evaporation_total:.2f}"
        assert components.vpd > 3.0, "VPD should be very high in dry conditions"

    def test_cold_humid_conditions(self):
        """Test calculation with cold and humid conditions."""
        components = ShuttleworthCalculator.calculate_with_components(
            t_max=10.0,  # Cold
            t_min=2.0,
            rh_max=95.0,  # Very humid
            rh_min=70.0,
            u10=10.0,
            sunshine_hours=4.0,
            pressure=101.3,
            latitude=55.0,  # Northern latitude
            altitude=50.0,
            day_number=350,  # Winter
            albedo=0.23
        )

        # Cold humid conditions should produce low evaporation
        assert components.evaporation_total < 3.0, \
            f"Cold humid conditions should produce low evaporation, got {components.evaporation_total:.2f}"
        assert components.vpd < 1.0, "VPD should be low in humid conditions"

    def test_equator_location(self):
        """Test calculation at equator (latitude 0)."""
        evaporation = ShuttleworthCalculator.calculate_lake_evaporation(
            t_max=30.0,
            t_min=25.0,
            rh_max=80.0,
            rh_min=60.0,
            u10=15.0,
            sunshine_hours=12.0,
            pressure=101.3,
            latitude=0.0,  # Equator
            altitude=0.0,
            day_number=80,  # Equinox
            albedo=0.23
        )

        assert evaporation > 0, "Evaporation at equator should be positive"
        assert evaporation < 20, "Evaporation should be reasonable"

    def test_high_latitude_summer(self):
        """Test calculation at high latitude in summer (long days)."""
        components = ShuttleworthCalculator.calculate_with_components(
            t_max=20.0,
            t_min=10.0,
            rh_max=70.0,
            rh_min=50.0,
            u10=20.0,
            sunshine_hours=20.0,  # Very long summer day
            pressure=101.3,
            latitude=65.0,  # High latitude
            altitude=0.0,
            day_number=172,  # Summer solstice
            albedo=0.23
        )

        # Long day should provide good radiation component
        assert components.radiation_component > 3.0, \
            "Long summer day should produce significant radiation component"
        assert components.n > 18.0, "Daylight hours should be very long at high latitude in summer"

    def test_high_altitude(self):
        """Test calculation at high altitude."""
        evaporation_high = ShuttleworthCalculator.calculate_lake_evaporation(
            t_max=20.0,
            t_min=10.0,
            rh_max=70.0,
            rh_min=50.0,
            u10=15.0,
            sunshine_hours=10.0,
            pressure=80.0,  # Low pressure (high altitude, ~2000m)
            latitude=45.0,
            altitude=2000.0,
            day_number=180,
            albedo=0.23
        )

        evaporation_sea = ShuttleworthCalculator.calculate_lake_evaporation(
            t_max=20.0,
            t_min=10.0,
            rh_max=70.0,
            rh_min=50.0,
            u10=15.0,
            sunshine_hours=10.0,
            pressure=101.3,  # Normal pressure (sea level)
            latitude=45.0,
            altitude=0.0,
            day_number=180,
            albedo=0.23
        )

        # High altitude should affect calculations (through pressure and clear sky radiation)
        assert evaporation_high > 0, "High altitude evaporation should be positive"
        assert evaporation_sea > 0, "Sea level evaporation should be positive"
        # The difference should be reasonable (not exactly equal)
        assert abs(evaporation_high - evaporation_sea) > 0.1, \
            "High altitude should affect evaporation calculations"

    def test_different_albedo_values(self):
        """Test calculation with different albedo values."""
        # Water surface (low albedo)
        evap_water = ShuttleworthCalculator.calculate_lake_evaporation(
            t_max=25.0, t_min=15.0, rh_max=70.0, rh_min=50.0,
            u10=15.0, sunshine_hours=10.0, pressure=101.3,
            latitude=45.0, altitude=200.0, day_number=180,
            albedo=0.08  # Dark water
        )

        # Normal water surface
        evap_normal = ShuttleworthCalculator.calculate_lake_evaporation(
            t_max=25.0, t_min=15.0, rh_max=70.0, rh_min=50.0,
            u10=15.0, sunshine_hours=10.0, pressure=101.3,
            latitude=45.0, altitude=200.0, day_number=180,
            albedo=0.23  # Standard water
        )

        # Ice/snow surface (high albedo)
        evap_ice = ShuttleworthCalculator.calculate_lake_evaporation(
            t_max=25.0, t_min=15.0, rh_max=70.0, rh_min=50.0,
            u10=15.0, sunshine_hours=10.0, pressure=101.3,
            latitude=45.0, altitude=200.0, day_number=180,
            albedo=0.60  # Ice/snow
        )

        # Lower albedo should absorb more radiation → higher evaporation
        assert evap_water > evap_normal > evap_ice, \
            "Lower albedo should result in higher evaporation"

    def test_seasonal_variation(self):
        """Test calculation across different seasons."""
        # Summer (day 172)
        evap_summer = ShuttleworthCalculator.calculate_lake_evaporation(
            t_max=30.0, t_min=20.0, rh_max=70.0, rh_min=40.0,
            u10=15.0, sunshine_hours=14.0, pressure=101.3,
            latitude=45.0, altitude=200.0, day_number=172,
            albedo=0.23
        )

        # Winter (day 355)
        evap_winter = ShuttleworthCalculator.calculate_lake_evaporation(
            t_max=10.0, t_min=2.0, rh_max=80.0, rh_min=60.0,
            u10=15.0, sunshine_hours=4.0, pressure=101.3,
            latitude=45.0, altitude=200.0, day_number=355,
            albedo=0.23
        )

        # Summer should have higher evaporation
        assert evap_summer > evap_winter, \
            f"Summer evaporation ({evap_summer:.2f}) should be higher than winter ({evap_winter:.2f})"
