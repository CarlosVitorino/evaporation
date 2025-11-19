"""
Test raster fallback functionality.

This test demonstrates the raster fallback mechanism for fetching weather data
when timeseries metadata is missing or invalid.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from lake_evaporation.core.config import Config
from lake_evaporation.services.raster_fetcher import RasterDataFetcher
from lake_evaporation.services.data_fetcher import DataFetcher


class TestRasterFallback(unittest.TestCase):
    """Test cases for raster fallback functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_client = Mock()
        self.config = Mock(spec=Config)

        # Configure mock config
        self.config.raster_enabled = True
        self.config.raster_use_as_fallback = True
        self.config.raster_datasource_id = 1
        self.config.raster_europe_model = "icon_eu"
        self.config.raster_global_model = "gfs"
        self.config.raster_parameters = {
            "temperature": "TMP_2M",
            "pressure": "PRMSL",
            "humidity": "RH_2M",
            "wind_speed": "FF_10M",
            "cloud": "TCDC",
            "low_clouds": "LCDC",
            "medium_clouds": "MCDC",
            "high_clouds": "HCDC"
        }

    def test_location_in_europe(self):
        """Test detection of European locations."""
        fetcher = RasterDataFetcher(self.api_client, self.config)

        # Test European location (Munich, Germany)
        self.assertTrue(fetcher.is_location_in_europe(48.1351, 11.5820))

        # Test non-European location (New York, USA)
        self.assertFalse(fetcher.is_location_in_europe(40.7128, -74.0060))

    def test_model_selection_europe(self):
        """Test model selection for European locations."""
        fetcher = RasterDataFetcher(self.api_client, self.config)

        # European location should get icon_eu as primary, gfs as fallback
        primary, fallback = fetcher.get_model_for_location(48.1351, 11.5820)
        self.assertEqual(primary, "icon_eu")
        self.assertEqual(fallback, "gfs")

    def test_model_selection_global(self):
        """Test model selection for non-European locations."""
        fetcher = RasterDataFetcher(self.api_client, self.config)

        # Non-European location should get gfs as primary, no fallback
        primary, fallback = fetcher.get_model_for_location(40.7128, -74.0060)
        self.assertEqual(primary, "gfs")
        self.assertIsNone(fallback)

    def test_filter_timeseries_by_model(self):
        """Test filtering of raster timeseries by model and parameter."""
        fetcher = RasterDataFetcher(self.api_client, self.config)

        # Mock timeseries list
        timeseries_list = [
            {
                "timeseriesId": "ts1",
                "path": "/gfs/TMP_2M",
                "name": "TMP_2M"
            },
            {
                "timeseriesId": "ts2",
                "path": "/icon_eu/TMP_2M",
                "name": "TMP_2M"
            },
            {
                "timeseriesId": "ts3",
                "path": "/gfs/PRMSL",
                "name": "PRMSL"
            },
            {
                "timeseriesId": "ts4",
                "path": "/other/TMP_2M",
                "name": "TMP_2M"
            }
        ]

        # Filter for GFS model and TMP_2M parameter
        result = fetcher.filter_timeseries_by_model_and_parameter(
            timeseries_list,
            "gfs",
            ["TMP_2M", "PRMSL"]
        )

        self.assertIn("TMP_2M", result)
        self.assertIn("PRMSL", result)
        self.assertEqual(result["TMP_2M"]["timeseriesId"], "ts1")
        self.assertEqual(result["PRMSL"]["timeseriesId"], "ts3")

    def test_data_fetcher_with_missing_timeseries(self):
        """Test that DataFetcher uses raster fallback when timeseries are missing."""
        # Create data fetcher with raster enabled
        data_fetcher = DataFetcher(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )

        # Verify raster fetcher was initialized
        self.assertIsNotNone(data_fetcher.raster_fetcher)

    def test_data_fetcher_without_raster(self):
        """Test that DataFetcher works without raster when disabled."""
        # Disable raster in config
        self.config.raster_enabled = False

        data_fetcher = DataFetcher(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )

        # Verify raster fetcher was not initialized
        self.assertIsNone(data_fetcher.raster_fetcher)

    @patch.object(RasterDataFetcher, 'fetch_raster_data_for_location')
    def test_fallback_triggers_on_missing_data(self, mock_fetch_raster):
        """Test that fallback is triggered when timeseries data is missing."""
        mock_fetch_raster.return_value = (
            {
                "temperature": [["2024-01-01T12:00:00Z", 15.2]],
                "humidity": [["2024-01-01T12:00:00Z", 65.0]],
                "wind_speed": [["2024-01-01T12:00:00Z", 12.5]],
                "air_pressure": [["2024-01-01T12:00:00Z", 101.3]],
                "low_clouds": [["2024-01-01T12:00:00Z", 25.0]],
                "medium_clouds": [["2024-01-01T12:00:00Z", 50.0]],
                "high_clouds": [["2024-01-01T12:00:00Z", 75.0]]
            },
            {
                "temperature": "°C",
                "humidity": "%",
                "wind_speed": "km/h",
                "air_pressure": "kPa",
                "low_clouds": "%",
                "medium_clouds": "%",
                "high_clouds": "%"
            }
        )

        # Create data fetcher
        data_fetcher = DataFetcher(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )

        # Mock location metadata WITHOUT timeseries references
        location_metadata = {
            "location": {
                "latitude": 48.1351,
                "longitude": 11.5820,
                "altitude": 519.0
            },
            "organization_id": "org123"
        }

        # Fetch data
        target_date = datetime(2024, 1, 1)
        data = data_fetcher.fetch_daily_data(location_metadata, target_date)

        # Verify raster fetcher was called
        mock_fetch_raster.assert_called_once()

        # Verify data was populated from raster
        self.assertIn("temperature", data)
        self.assertIn("humidity", data)
        self.assertIn("wind_speed", data)
        self.assertIn("air_pressure", data)
        self.assertIn("low_clouds", data)
        self.assertIn("medium_clouds", data)
        self.assertIn("high_clouds", data)


class TestRasterAPI(unittest.TestCase):
    """Test cases for raster API client."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_client = Mock()
        self.api_client.logger = Mock()

    def test_get_raster_timeseries_list_endpoint(self):
        """Test that get_raster_timeseries_list builds correct endpoint."""
        from lake_evaporation.api.raster import RasterAPI

        # Create a mock class that includes RasterAPI
        class MockAPI(RasterAPI):
            def __init__(self):
                self.logger = Mock()

            def get(self, endpoint, params=None):
                self.last_endpoint = endpoint
                return []

        api = MockAPI()
        api.get_raster_timeseries_list(datasource_id=1, organization_id="org123")

        # Verify endpoint format
        self.assertIn("/raster/datasources/1/timeSeries", api.last_endpoint)
        self.assertIn("orgId=org123", api.last_endpoint)

    def test_get_raster_point_data_endpoint(self):
        """Test that get_raster_point_data builds correct endpoint."""
        from lake_evaporation.api.raster import RasterAPI

        class MockAPI(RasterAPI):
            def __init__(self):
                self.logger = Mock()

            def get(self, endpoint, params=None):
                self.last_endpoint = endpoint
                return {}

        api = MockAPI()
        points = [{"lat": 48.1351, "lon": 11.5820}]
        api.get_raster_point_data(
            datasource_id=1,
            timeseries_id="ts123",
            points=points,
            start_date="2024-01-01T00:00:00Z",
            end_date="2024-01-02T00:00:00Z"
        )

        # Verify endpoint contains required components
        self.assertIn("/raster/datasources/1/timeSeries/ts123/points", api.last_endpoint)
        self.assertIn("extractMode=", api.last_endpoint)
        self.assertIn("from=", api.last_endpoint)
        self.assertIn("until=", api.last_endpoint)
        self.assertIn("points=", api.last_endpoint)


if __name__ == "__main__":
    unittest.main()
