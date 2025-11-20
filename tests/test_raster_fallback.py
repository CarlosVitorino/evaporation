"""
Test raster fallback functionality.

This test demonstrates the raster fallback mechanism for fetching weather data
when timeseries metadata is missing or invalid.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from src.lake_evaporation.core.config import Config
from src.lake_evaporation.services.raster_fetcher import RasterDataFetcher
from src.lake_evaporation.services.data_fetcher import DataFetcher


class TestRasterFallback(unittest.TestCase):
    """Test cases for raster fallback functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_client = Mock()
        self.config = Mock(spec=Config)
        
        self.config.raster_enabled = True
        self.config.raster_use_as_fallback = True
        self.config.raster_datasource_id = 1
        self.config.raster_europe_model = "nwp_obslike/dwd/icon_eu"
        self.config.raster_global_model = "nwp_obslike/noaa/gfs"
        
        self.config.get_raster_parameters_for_model = Mock(side_effect=lambda model: {
            "temperature": "TMP_2M",
            "air_pressure": "PRES",
            "humidity": "RH_2M",
            "wind_speed": "FF_10M",
            "low_clouds": "LCDC",
            "medium_clouds": "MCDC",
            "high_clouds": "HCDC"
        })
        
        self.api_client.get_raster_timeseries_list = Mock(return_value=[])

    def test_location_in_europe(self):
        """Test detection of European locations."""
        fetcher = RasterDataFetcher(self.api_client, self.config)

        self.assertTrue(fetcher.is_location_in_europe(48.1351, 11.5820))
        self.assertFalse(fetcher.is_location_in_europe(40.7128, -74.0060))

    def test_model_selection_europe(self):
        """Test model selection for European locations."""
        fetcher = RasterDataFetcher(self.api_client, self.config)

        primary, fallback = fetcher.get_model_for_location(48.1351, 11.5820)
        self.assertEqual(primary, "nwp_obslike/dwd/icon_eu")
        self.assertEqual(fallback, "nwp_obslike/noaa/gfs")

    def test_model_selection_global(self):
        """Test model selection for non-European locations."""
        fetcher = RasterDataFetcher(self.api_client, self.config)

        primary, fallback = fetcher.get_model_for_location(40.7128, -74.0060)
        self.assertEqual(primary, "nwp_obslike/noaa/gfs")
        self.assertEqual(fallback, "nwp_obslike/noaa/gfs")

    def test_filter_timeseries_by_model(self):
        """Test filtering of raster timeseries by model and parameter."""
        fetcher = RasterDataFetcher(self.api_client, self.config)

        timeseries_list = [
            {
                "timeseriesId": "ts1",
                "path": "/nwp_obslike/noaa/gfs/TMP_2M",
                "name": "TMP_2M"
            },
            {
                "timeseriesId": "ts2",
                "path": "/nwp_obslike/dwd/icon_eu/TMP_2M",
                "name": "TMP_2M"
            },
            {
                "timeseriesId": "ts3",
                "path": "/nwp_obslike/noaa/gfs/PRES",
                "name": "PRES"
            },
            {
                "timeseriesId": "ts4",
                "path": "/other/TMP_2M",
                "name": "TMP_2M"
            }
        ]

        result = fetcher.filter_timeseries_by_model_and_parameter(
            timeseries_list,
            "nwp_obslike/noaa/gfs",
            ["TMP_2M", "PRES"]
        )

        self.assertIn("TMP_2M", result)
        self.assertIn("PRES", result)
        self.assertEqual(result["TMP_2M"]["timeseriesId"], "ts1")
        self.assertEqual(result["PRES"]["timeseriesId"], "ts3")

    def test_parse_raster_response(self):
        """Test parsing of raster API response."""
        fetcher = RasterDataFetcher(self.api_client, self.config)
        
        mock_response = [
            {
                "unitSymbol": "°C",
                "data": [
                    {"time": "2024-01-01T00:00:00Z", "data": 15.2},
                    {"time": "2024-01-01T01:00:00Z", "data": 14.8},
                    {"time": "2024-01-01T02:00:00Z", "data": 14.5}
                ]
            }
        ]
        
        result = fetcher._parse_raster_response(mock_response, "temperature")
        
        self.assertEqual(result["unit"], "°C")
        self.assertEqual(len(result["data"]), 3)
        self.assertEqual(result["data"][0], ["2024-01-01T00:00:00Z", 15.2])
        self.assertEqual(result["data"][1], ["2024-01-01T01:00:00Z", 14.8])

    def test_fetch_raster_data_for_location(self):
        """Test fetching raster data for a location."""
        self.api_client.get_raster_timeseries_list = Mock(return_value=[
            {
                "timeseriesId": "ts_temp",
                "path": "/nwp_obslike/dwd/icon_eu/TMP_2M",
                "name": "TMP_2M",
                "unitSymbol": "°C"
            },
            {
                "timeseriesId": "ts_hum",
                "path": "/nwp_obslike/dwd/icon_eu/RH_2M",
                "name": "RH_2M",
                "unitSymbol": "%"
            }
        ])
        
        self.api_client.get_raster_point_data = Mock(return_value=[
            {
                "unitSymbol": "°C",
                "data": [
                    {"time": "2024-01-01T00:00:00Z", "data": 15.2}
                ]
            }
        ])
        
        fetcher = RasterDataFetcher(self.api_client, self.config)
        
        self.api_client.get_raster_timeseries_list.assert_called_once_with()
        
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        data, units = fetcher.fetch_raster_data_for_location(
            latitude=48.1351,
            longitude=11.5820,
            start_date=start_date,
            end_date=end_date,
            organization_id="org123"
        )
        
        self.assertIn("temperature", data)
        self.assertIn("humidity", data)
        self.assertEqual(units["temperature"], "°C")
        
        self.api_client.get_raster_timeseries_list.assert_called_once()

    def test_raster_timeseries_cached_on_init(self):
        """Test that raster timeseries list is fetched and cached on initialization."""
        mock_timeseries = [
            {
                "timeseriesId": "ts1",
                "path": "/nwp_obslike/dwd/icon_eu/TMP_2M",
                "name": "TMP_2M"
            }
        ]
        
        self.api_client.get_raster_timeseries_list = Mock(return_value=mock_timeseries)
        
        fetcher = RasterDataFetcher(self.api_client, self.config)
        
        self.api_client.get_raster_timeseries_list.assert_called_once_with()
        
        fetcher._get_raster_timeseries_list()
        fetcher._get_raster_timeseries_list()
        
        self.api_client.get_raster_timeseries_list.assert_called_once()

    def test_data_fetcher_with_raster_enabled(self):
        """Test that DataFetcher initializes raster when enabled."""
        data_fetcher = DataFetcher(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )

        self.assertIsNotNone(data_fetcher.raster_fetcher)

    def test_data_fetcher_without_raster(self):
        """Test that DataFetcher works without raster when disabled."""
        self.config.raster_enabled = False

        data_fetcher = DataFetcher(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )

        self.assertIsNone(data_fetcher.raster_fetcher)


class TestRasterAPI(unittest.TestCase):
    """Test cases for raster API client."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_client = Mock()
        self.api_client.logger = Mock()

    def test_get_raster_timeseries_list_endpoint(self):
        """Test that get_raster_timeseries_list builds correct endpoint."""
        from src.lake_evaporation.api.raster import RasterAPI

        class MockAPI(RasterAPI):
            def __init__(self):
                self.logger = Mock()

            def get(self, endpoint, params=None):
                self.last_endpoint = endpoint
                return []

        api = MockAPI()
        api.get_raster_timeseries_list()

        self.assertEqual(api.last_endpoint, "/raster/timeSeries")

    def test_get_raster_timeseries_list_no_org_param(self):
        """Test that get_raster_timeseries_list does not include datasource_id or organization_id."""
        from src.lake_evaporation.api.raster import RasterAPI

        class MockAPI(RasterAPI):
            def __init__(self):
                self.logger = Mock()

            def get(self, endpoint, params=None):
                self.last_endpoint = endpoint
                return []

        api = MockAPI()
        api.get_raster_timeseries_list()

        self.assertEqual(api.last_endpoint, "/raster/timeSeries")
        self.assertNotIn("datasource", api.last_endpoint)
        self.assertNotIn("org", api.last_endpoint.lower())

    def test_get_raster_point_data_endpoint(self):
        """Test that get_raster_point_data builds correct endpoint."""
        from src.lake_evaporation.api.raster import RasterAPI

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

        self.assertIn("/raster/datasources/1/timeSeries/ts123/points", api.last_endpoint)
        self.assertIn("from=", api.last_endpoint)
        self.assertIn("until=", api.last_endpoint)
        self.assertIn("points=", api.last_endpoint)


if __name__ == "__main__":
    unittest.main()
