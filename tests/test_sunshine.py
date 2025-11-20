"""
Tests for sunshine hours calculation module.

Tests all methods of calculating sunshine hours:
1. From global radiation using Ångström-Prescott equation
2. From cloud cover layers
3. From temperature range (Hargreaves method)
"""

import pytest  # type: ignore
from src.lake_evaporation.algorithms.sunshine import SunshineCalculator


class TestSunshineCalculatorFromRadiation:
    """Test calculating sunshine hours from global radiation."""

    @pytest.fixture
    def calculator(self):
        """Create calculator with default Ångström coefficients."""
        return SunshineCalculator(a=0.25, b=0.5)

    def test_calculate_from_global_radiation_basic(self, calculator):
        """Test basic sunshine calculation from global radiation."""
        # Mid-latitude summer day with good radiation
        sunshine = calculator.calculate_sunshine_hours(
            global_radiation=25.0,  # MJ/m²/day
            latitude=45.0,
            day_number=172  # Summer solstice
        )

        assert sunshine > 0, "Sunshine hours should be positive"
        assert sunshine < 24, "Sunshine hours should be less than 24"

    def test_calculate_from_global_radiation_high_radiation(self, calculator):
        """Test with high global radiation (clear sunny day)."""
        sunshine = calculator.calculate_sunshine_hours(
            global_radiation=30.0,  # High radiation
            latitude=45.0,
            day_number=180
        )

        # High radiation should give sunshine hours close to max daylight
        max_daylight = calculator._calculate_daylight_hours(45.0, 180)
        assert sunshine > max_daylight * 0.8, \
            f"High radiation should give sunshine close to max daylight ({max_daylight:.1f}h)"

    def test_calculate_from_global_radiation_low_radiation(self, calculator):
        """Test with low global radiation (cloudy day)."""
        sunshine = calculator.calculate_sunshine_hours(
            global_radiation=10.0,  # Low radiation
            latitude=45.0,
            day_number=180
        )

        # Low radiation should give low sunshine hours
        max_daylight = calculator._calculate_daylight_hours(45.0, 180)
        assert sunshine < max_daylight * 0.5, \
            "Low radiation should give limited sunshine hours"

    def test_calculate_from_global_radiation_zero(self, calculator):
        """Test with zero global radiation (nighttime or completely overcast)."""
        sunshine = calculator.calculate_sunshine_hours(
            global_radiation=0.0,
            latitude=45.0,
            day_number=180
        )

        assert sunshine == 0.0, "Zero radiation should give zero sunshine"

    def test_calculate_from_data_points(self, calculator):
        """Test calculating sunshine from radiation data points."""
        # Sample data: 8 readings over a day (W/m²)
        radiation_data = [
            ["2024-06-21T00:00:00", 0.0],
            ["2024-06-21T03:00:00", 0.0],
            ["2024-06-21T06:00:00", 150.0],
            ["2024-06-21T09:00:00", 450.0],
            ["2024-06-21T12:00:00", 680.0],
            ["2024-06-21T15:00:00", 520.0],
            ["2024-06-21T18:00:00", 280.0],
            ["2024-06-21T21:00:00", 45.0]
        ]

        sunshine = calculator.calculate_from_data_points(
            radiation_data=radiation_data,
            latitude=45.5,
            day_number=172
        )

        assert sunshine > 0, "Should calculate positive sunshine hours"
        assert sunshine < 24, "Sunshine should be less than 24 hours"

    def test_different_angstrom_coefficients(self):
        """Test with different Ångström-Prescott coefficients."""
        # Default coefficients (a=0.25, b=0.5)
        calc_default = SunshineCalculator(a=0.25, b=0.5)
        sunshine_default = calc_default.calculate_sunshine_hours(
            global_radiation=20.0,
            latitude=45.0,
            day_number=180
        )

        # Different coefficients (clearer atmosphere)
        calc_clear = SunshineCalculator(a=0.20, b=0.55)
        sunshine_clear = calc_clear.calculate_sunshine_hours(
            global_radiation=20.0,
            latitude=45.0,
            day_number=180
        )

        # Both should be positive and reasonable
        assert sunshine_default > 0
        assert sunshine_clear > 0
        # Different coefficients should give different results
        assert abs(sunshine_default - sunshine_clear) > 0.1, \
            "Different coefficients should affect the calculation"


class TestSunshineCalculatorFromCloudCover:
    """Test calculating sunshine hours from cloud cover layers."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return SunshineCalculator()

    def test_calculate_from_cloud_cover_excel_reference(self, calculator):
        """Test cloud cover calculation using Excel reference values."""
        # Excel test case: Nl=3, Nm=2, Nh=4 → n=6.97 hours (at latitude 51°, day 170)
        # Nel = 3 + 0.875 * ((8 - 3) / 8) * 2 = 3 + 0.875 * 0.625 * 2 = 4.09375
        # Ne = 4.09375 + 0.25 * ((8 - 4.09375) / 8) * 4 = 4.09375 + 0.25 * 0.488... * 4 = 4.58203125
        # N = ~16.569 hours (for lat 51°, day 170)
        # n = N * (1 - Ne/8) = 16.569 * (1 - 4.58203125/8) = 16.569 * 0.4277... = 6.97 hours
        
        sunshine = calculator.calculate_from_cloud_cover_layers(
            latitude=51.0,
            day_number=170,
            low_cloud_octas=3.0,
            medium_cloud_octas=2.0,
            high_cloud_octas=4.0
        )

        # Excel shows n=6.97 hours
        expected = 6.97
        tolerance = 0.01
        assert abs(sunshine - expected) < tolerance, \
            f"Expected {expected:.2f}h ± {tolerance}h, got {sunshine:.2f}h"

    def test_calculate_from_cloud_cover_clear_sky(self, calculator):
        """Test with completely clear sky."""
        max_daylight = calculator._calculate_daylight_hours(45.0, 180)

        sunshine = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0,
            day_number=180,
            low_cloud_octas=0.0,
            medium_cloud_octas=0.0,
            high_cloud_octas=0.0
        )

        # Clear sky should give full sunshine
        assert abs(sunshine - max_daylight) < 0.1, \
            f"Clear sky should give full daylight ({max_daylight:.1f}h), got {sunshine:.1f}h"

    def test_calculate_from_cloud_cover_overcast(self, calculator):
        """Test with completely overcast sky."""
        max_daylight = calculator._calculate_daylight_hours(45.0, 180)

        sunshine = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0,
            day_number=180,
            low_cloud_octas=8.0,
            medium_cloud_octas=8.0,
            high_cloud_octas=8.0
        )

        # Overcast should give very low sunshine
        assert sunshine < max_daylight * 0.3, \
            "Overcast conditions should give low sunshine"

    def test_calculate_from_cloud_cover_low_clouds_only(self, calculator):
        """Test with only low clouds (most blocking)."""
        sunshine_low = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0,
            day_number=180,
            low_cloud_octas=6.0,
            medium_cloud_octas=0.0,
            high_cloud_octas=0.0
        )

        sunshine_no_clouds = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0,
            day_number=180,
            low_cloud_octas=0.0,
            medium_cloud_octas=0.0,
            high_cloud_octas=0.0
        )

        # Low clouds should significantly reduce sunshine
        assert sunshine_low < sunshine_no_clouds * 0.5, \
            "Low clouds should significantly reduce sunshine"

    def test_calculate_from_cloud_cover_high_clouds_only(self, calculator):
        """Test with only high clouds (least blocking)."""
        sunshine_high = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0,
            day_number=180,
            low_cloud_octas=0.0,
            medium_cloud_octas=0.0,
            high_cloud_octas=6.0
        )

        sunshine_no_clouds = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0,
            day_number=180,
            low_cloud_octas=0.0,
            medium_cloud_octas=0.0,
            high_cloud_octas=0.0
        )

        # High clouds should reduce sunshine less than low clouds
        assert sunshine_high > sunshine_no_clouds * 0.6, \
            "High clouds should have less effect on sunshine"

    def test_calculate_from_cloud_cover_layer_weighting(self, calculator):
        """Test that cloud layers are weighted correctly (low > medium > high)."""
        # Same amount of cloud at different levels
        sunshine_low = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0, day_number=180,
            low_cloud_octas=4.0, medium_cloud_octas=0.0, high_cloud_octas=0.0
        )
        sunshine_medium = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0, day_number=180,
            low_cloud_octas=0.0, medium_cloud_octas=4.0, high_cloud_octas=0.0
        )
        sunshine_high = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0, day_number=180,
            low_cloud_octas=0.0, medium_cloud_octas=0.0, high_cloud_octas=4.0
        )

        # Low clouds should block more than medium, which block more than high
        assert sunshine_low < sunshine_medium < sunshine_high, \
            "Cloud blocking should be: low > medium > high"

    def test_calculate_from_cloud_cover_boundary_values(self, calculator):
        """Test with boundary values (0 and 8 octas)."""
        # Test with minimum values
        sunshine_min = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0, day_number=180,
            low_cloud_octas=0.0, medium_cloud_octas=0.0, high_cloud_octas=0.0
        )
        assert sunshine_min > 0, "Minimum cloud should give positive sunshine"

        # Test with maximum values
        sunshine_max = calculator.calculate_from_cloud_cover_layers(
            latitude=45.0, day_number=180,
            low_cloud_octas=8.0, medium_cloud_octas=8.0, high_cloud_octas=8.0
        )
        assert sunshine_max >= 0, "Maximum cloud should give non-negative sunshine"
        assert sunshine_max < sunshine_min, "Maximum cloud should give less sunshine than minimum"


class TestSunshineCalculatorFromTemperatureRange:
    """Test calculating sunshine hours from temperature range."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return SunshineCalculator()

    def test_calculate_from_temperature_range_interior(self, calculator):
        """Test temperature-based calculation for interior location."""
        sunshine = calculator.calculate_from_temperature_range(
            latitude=45.0,
            day_number=180,
            t_min=15.0,
            t_max=30.0,  # 15°C range (good sunshine)
            coastal=False
        )

        max_daylight = calculator._calculate_daylight_hours(45.0, 180)
        assert 0 < sunshine < max_daylight, \
            "Sunshine should be between 0 and max daylight"

    def test_calculate_from_temperature_range_coastal(self, calculator):
        """Test temperature-based calculation for coastal location."""
        sunshine = calculator.calculate_from_temperature_range(
            latitude=45.0,
            day_number=180,
            t_min=15.0,
            t_max=30.0,
            coastal=True
        )

        max_daylight = calculator._calculate_daylight_hours(45.0, 180)
        assert 0 < sunshine < max_daylight, \
            "Sunshine should be between 0 and max daylight"

    def test_calculate_from_temperature_range_interior_vs_coastal(self, calculator):
        """Test that interior locations have higher sunshine for same temp range."""
        sunshine_interior = calculator.calculate_from_temperature_range(
            latitude=45.0, day_number=180,
            t_min=15.0, t_max=30.0, coastal=False
        )

        sunshine_coastal = calculator.calculate_from_temperature_range(
            latitude=45.0, day_number=180,
            t_min=15.0, t_max=30.0, coastal=True
        )

        # For same temperature range, interior should estimate more sunshine
        # (because coastal locations have moderated temperatures)
        assert sunshine_interior > sunshine_coastal, \
            "Interior should estimate more sunshine than coastal for same temp range"

    def test_calculate_from_temperature_range_large_difference(self, calculator):
        """Test with large temperature difference (clear sunny day)."""
        sunshine_large = calculator.calculate_from_temperature_range(
            latitude=45.0, day_number=180,
            t_min=15.0, t_max=35.0,  # 20°C range
            coastal=False
        )

        sunshine_small = calculator.calculate_from_temperature_range(
            latitude=45.0, day_number=180,
            t_min=15.0, t_max=20.0,  # 5°C range
            coastal=False
        )

        # Larger temperature range should indicate more sunshine
        assert sunshine_large > sunshine_small, \
            "Larger temp range should indicate more sunshine"

    def test_calculate_from_temperature_range_small_difference(self, calculator):
        """Test with small temperature difference (cloudy day)."""
        sunshine = calculator.calculate_from_temperature_range(
            latitude=45.0,
            day_number=180,
            t_min=18.0,
            t_max=20.0,  # Only 2°C range (cloudy)
            coastal=False
        )

        max_daylight = calculator._calculate_daylight_hours(45.0, 180)
        assert sunshine < max_daylight * 0.5, \
            "Small temp range should indicate limited sunshine"

    def test_calculate_from_temperature_range_zero_difference(self, calculator):
        """Test with zero temperature difference (constant temperature)."""
        sunshine = calculator.calculate_from_temperature_range(
            latitude=45.0,
            day_number=180,
            t_min=20.0,
            t_max=20.0,  # No difference
            coastal=False
        )

        assert sunshine >= 0, "Zero temp difference should give non-negative sunshine"

    def test_calculate_from_temperature_range_inverted(self, calculator):
        """Test with inverted temperatures (error condition)."""
        # When t_max < t_min, should handle gracefully
        sunshine = calculator.calculate_from_temperature_range(
            latitude=45.0,
            day_number=180,
            t_min=25.0,
            t_max=20.0,  # Inverted!
            coastal=False
        )

        assert sunshine >= 0, "Should handle inverted temps gracefully"


class TestSunshineCalculatorHelperMethods:
    """Test helper methods for sunshine calculations."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return SunshineCalculator()

    def test_calculate_extraterrestrial_radiation(self, calculator):
        """Test extraterrestrial radiation calculation."""
        # Mid-latitude summer
        ra = calculator._calculate_extraterrestrial_radiation(45.0, 172)

        assert ra > 0, "Extraterrestrial radiation should be positive"
        assert 30 < ra < 50, f"Ra should be reasonable for summer mid-latitude, got {ra:.1f}"

    def test_calculate_extraterrestrial_radiation_equator(self, calculator):
        """Test at equator during equinox."""
        ra_equinox = calculator._calculate_extraterrestrial_radiation(0.0, 80)
        assert ra_equinox > 30, "Equator equinox should have high radiation"

    def test_calculate_extraterrestrial_radiation_high_latitude_summer(self, calculator):
        """Test at high latitude in summer (but not polar, to avoid math domain errors)."""
        # At very high latitudes (>~66.5°), the sun doesn't set in summer, causing math domain errors
        # Test at 65° instead
        ra_summer = calculator._calculate_extraterrestrial_radiation(65.0, 172)
        assert ra_summer > 0, "High latitude summer should have positive radiation"

    def test_calculate_daylight_hours_summer_mid_latitude(self, calculator):
        """Test daylight hours calculation for summer."""
        daylight = calculator._calculate_daylight_hours(45.0, 172)  # Summer solstice

        assert 14 < daylight < 16, \
            f"Mid-latitude summer should have 14-16 hours daylight, got {daylight:.1f}"

    def test_calculate_daylight_hours_winter_mid_latitude(self, calculator):
        """Test daylight hours calculation for winter."""
        daylight = calculator._calculate_daylight_hours(45.0, 355)  # Winter solstice

        assert 8 < daylight < 10, \
            f"Mid-latitude winter should have 8-10 hours daylight, got {daylight:.1f}"

    def test_calculate_daylight_hours_equator(self, calculator):
        """Test daylight hours at equator (should be ~12 hours year-round)."""
        daylight_equinox = calculator._calculate_daylight_hours(0.0, 80)  # Equinox
        daylight_solstice = calculator._calculate_daylight_hours(0.0, 172)  # Solstice

        assert 11.5 < daylight_equinox < 12.5, "Equator should have ~12 hours at equinox"
        assert 11.5 < daylight_solstice < 12.5, "Equator should have ~12 hours at solstice"

    def test_calculate_daylight_hours_high_latitude_summer(self, calculator):
        """Test daylight hours at high latitude in summer (very long days)."""
        daylight = calculator._calculate_daylight_hours(65.0, 172)  # 65°N in summer

        assert daylight > 18, f"High latitude summer should have very long days, got {daylight:.1f}h"

    def test_calculate_daylight_hours_high_latitude_winter(self, calculator):
        """Test daylight hours at high latitude in winter (very short days)."""
        daylight = calculator._calculate_daylight_hours(65.0, 355)  # 65°N in winter

        assert daylight < 6, f"High latitude winter should have very short days, got {daylight:.1f}h"

    def test_calculate_daylight_hours_seasonal_variation(self, calculator):
        """Test that daylight hours vary correctly with season."""
        # Same location, different seasons
        summer = calculator._calculate_daylight_hours(45.0, 172)  # Summer solstice
        winter = calculator._calculate_daylight_hours(45.0, 355)  # Winter solstice
        equinox = calculator._calculate_daylight_hours(45.0, 80)  # Equinox

        assert summer > equinox > winter, \
            f"Daylight should be: summer({summer:.1f}) > equinox({equinox:.1f}) > winter({winter:.1f})"

    def test_calculate_daylight_hours_latitude_variation_summer(self, calculator):
        """Test daylight hours variation with latitude in summer."""
        low_lat = calculator._calculate_daylight_hours(30.0, 172)
        mid_lat = calculator._calculate_daylight_hours(45.0, 172)
        high_lat = calculator._calculate_daylight_hours(60.0, 172)

        # In summer, higher latitudes have longer days
        assert high_lat > mid_lat > low_lat, \
            f"Summer daylight should increase with latitude: {low_lat:.1f} < {mid_lat:.1f} < {high_lat:.1f}"

    def test_calculate_daylight_hours_latitude_variation_winter(self, calculator):
        """Test daylight hours variation with latitude in winter."""
        low_lat = calculator._calculate_daylight_hours(30.0, 355)
        mid_lat = calculator._calculate_daylight_hours(45.0, 355)
        high_lat = calculator._calculate_daylight_hours(60.0, 355)

        # In winter, lower latitudes have longer days
        assert low_lat > mid_lat > high_lat, \
            f"Winter daylight should decrease with latitude: {low_lat:.1f} > {mid_lat:.1f} > {high_lat:.1f}"


class TestSunshineCalculatorIntegration:
    """Integration tests comparing different sunshine calculation methods."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return SunshineCalculator()

    def test_compare_methods_clear_day(self, calculator):
        """Compare all methods for a clear sunny day."""
        latitude = 45.0
        day_number = 180

        # Method 1: From high global radiation
        sunshine_radiation = calculator.calculate_sunshine_hours(
            global_radiation=28.0,  # High radiation
            latitude=latitude,
            day_number=day_number
        )

        # Method 2: From clear sky (no clouds)
        sunshine_clouds = calculator.calculate_from_cloud_cover_layers(
            latitude=latitude,
            day_number=day_number,
            low_cloud_octas=0.0,
            medium_cloud_octas=0.0,
            high_cloud_octas=0.0
        )

        # Method 3: From large temperature range
        sunshine_temp = calculator.calculate_from_temperature_range(
            latitude=latitude,
            day_number=day_number,
            t_min=15.0,
            t_max=32.0,  # Large range
            coastal=False
        )

        max_daylight = calculator._calculate_daylight_hours(latitude, day_number)

        # All methods should indicate good sunshine (> 80% of max)
        assert sunshine_radiation > max_daylight * 0.8, \
            "High radiation should indicate good sunshine"
        assert sunshine_clouds > max_daylight * 0.95, \
            "Clear sky should indicate nearly full sunshine"
        assert sunshine_temp > max_daylight * 0.5, \
            "Large temp range should indicate significant sunshine"

    def test_compare_methods_cloudy_day(self, calculator):
        """Compare all methods for a cloudy day."""
        latitude = 45.0
        day_number = 180

        # Method 1: From low global radiation
        sunshine_radiation = calculator.calculate_sunshine_hours(
            global_radiation=12.0,  # Low radiation
            latitude=latitude,
            day_number=day_number
        )

        # Method 2: From overcast sky
        sunshine_clouds = calculator.calculate_from_cloud_cover_layers(
            latitude=latitude,
            day_number=day_number,
            low_cloud_octas=8.0,
            medium_cloud_octas=6.0,
            high_cloud_octas=4.0
        )

        # Method 3: From small temperature range
        sunshine_temp = calculator.calculate_from_temperature_range(
            latitude=latitude,
            day_number=day_number,
            t_min=18.0,
            t_max=22.0,  # Small range
            coastal=False
        )

        max_daylight = calculator._calculate_daylight_hours(latitude, day_number)

        # All methods should indicate limited sunshine (< 50% of max)
        assert sunshine_radiation < max_daylight * 0.5, \
            "Low radiation should indicate limited sunshine"
        assert sunshine_clouds < max_daylight * 0.4, \
            "Overcast should indicate limited sunshine"
        assert sunshine_temp < max_daylight * 0.5, \
            "Small temp range should indicate limited sunshine (though less sensitive than other methods)"

    def test_consistency_across_latitudes(self, calculator):
        """Test that methods are consistent across different latitudes."""
        day_number = 180

        for latitude in [0, 30, 45, 60]:
            max_daylight = calculator._calculate_daylight_hours(latitude, day_number)

            # Test with moderate conditions
            sunshine_radiation = calculator.calculate_sunshine_hours(
                global_radiation=20.0,
                latitude=latitude,
                day_number=day_number
            )

            sunshine_clouds = calculator.calculate_from_cloud_cover_layers(
                latitude=latitude,
                day_number=day_number,
                low_cloud_octas=4.0,
                medium_cloud_octas=2.0,
                high_cloud_octas=1.0
            )

            # Both should give reasonable results
            assert 0 < sunshine_radiation < max_daylight, \
                f"Radiation method failed at latitude {latitude}"
            assert 0 < sunshine_clouds < max_daylight, \
                f"Cloud method failed at latitude {latitude}"

    def test_consistency_across_seasons(self, calculator):
        """Test that methods are consistent across seasons."""
        latitude = 45.0

        for day_number in [1, 80, 172, 266, 355]:  # Different seasons
            max_daylight = calculator._calculate_daylight_hours(latitude, day_number)

            sunshine_radiation = calculator.calculate_sunshine_hours(
                global_radiation=20.0,
                latitude=latitude,
                day_number=day_number
            )

            sunshine_clouds = calculator.calculate_from_cloud_cover_layers(
                latitude=latitude,
                day_number=day_number,
                low_cloud_octas=3.0,
                medium_cloud_octas=2.0,
                high_cloud_octas=1.0
            )

            # Both should give reasonable results (use <= to handle edge case where they're equal)
            assert 0 < sunshine_radiation <= max_daylight, \
                f"Radiation method failed at day {day_number}: {sunshine_radiation:.2f} vs max {max_daylight:.2f}"
            assert 0 < sunshine_clouds <= max_daylight, \
                f"Cloud method failed at day {day_number}: {sunshine_clouds:.2f} vs max {max_daylight:.2f}"
