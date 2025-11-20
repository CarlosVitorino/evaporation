"""
Service layer integration tests.

Tests the services that orchestrate data fetching, aggregation, and calculations.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.lake_evaporation.services.discovery import TimeSeriesDiscovery
from src.lake_evaporation.services.data_fetcher import DataFetcher
from src.lake_evaporation.services.sunshine_service import SunshineService
from src.lake_evaporation.services.writer import DataWriter
from src.lake_evaporation.algorithms import SunshineCalculator
from src.lake_evaporation.core.config import Config


class TestTimeSeriesDiscovery(unittest.TestCase):
    """Test time series discovery service."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_client = Mock()
        self.config = Mock(spec=Config)
        self.config.raster_enabled = True
        self.config.raster_use_as_fallback = True
        
        self.discovery = TimeSeriesDiscovery(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )

    def test_discover_lake_evaporation_series(self):
        """Test discovering time series with lake evaporation metadata."""
        mock_timeseries = [
            {
                "id": "ts1",
                "name": "Lake Como Evaporation",
                "metadata": {
                    "lakeEvaporation": {
                        "Temps": "tsId(100)",
                        "RHTs": "tsId(101)",
                        "WSpeedTs": "tsId(102)",
                        "AirPressureTs": "tsId(103)"
                    }
                },
                "locationId": "loc1",
                "locationName": "Lake Como",
                "locationLatitude": 46.0,
                "locationLongitude": 9.2
            },
            {
                "id": "ts2",
                "name": "Regular Series",
                "metadata": {}
            }
        ]
        
        self.api_client.get_time_series_list = Mock(return_value=mock_timeseries)
        
        result = self.discovery.discover_lake_evaporation_series("org123")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "ts1")
        self.assertIn("lakeEvaporation", result[0]["metadata"])

    def test_extract_metadata(self):
        """Test extracting metadata from time series."""
        time_series = {
            "id": "ts1",
            "name": "Lake Como Evaporation",
            "metadata": {
                "lakeEvaporation": {
                    "Temps": "tsId(100)",
                    "RHTs": "tsId(101)",
                    "WSpeedTs": "tsId(102)",
                    "AirPressureTs": "tsId(103)",
                    "hoursOfSunshineTs": "tsId(104)"
                }
            },
            "locationId": "loc1",
            "locationName": "Lake Como",
            "locationLatitude": 46.0,
            "locationLongitude": 9.2,
            "locationElevation": 198.0
        }
        
        metadata = self.discovery.extract_metadata(time_series)
        
        self.assertEqual(metadata["time_series_id"], "ts1")
        self.assertEqual(metadata["name"], "Lake Como Evaporation")
        self.assertEqual(metadata["temperature_ts"], "tsId(100)")
        self.assertEqual(metadata["humidity_ts"], "tsId(101)")
        self.assertEqual(metadata["location"]["latitude"], 46.0)
        self.assertEqual(metadata["location"]["longitude"], 9.2)

    def test_validate_metadata_with_all_timeseries(self):
        """Test validation passes when all required timeseries exist."""
        metadata = {
            "name": "Test Location",
            "temperature_ts": "tsId(100)",
            "humidity_ts": "tsId(101)",
            "wind_speed_ts": "tsId(102)",
            "air_pressure_ts": "tsId(103)"
        }
        
        is_valid = self.discovery.validate_metadata(metadata)
        self.assertTrue(is_valid)

    def test_validate_metadata_with_missing_timeseries_and_raster(self):
        """Test validation passes when timeseries missing but raster available."""
        metadata = {
            "name": "Test Location",
            "temperature_ts": "tsId(100)",
            "location": {
                "latitude": 46.0,
                "longitude": 9.2
            }
        }
        
        is_valid = self.discovery.validate_metadata(metadata)
        self.assertTrue(is_valid)

    def test_validate_metadata_fails_without_timeseries_or_raster(self):
        """Test validation fails when both timeseries and raster unavailable."""
        self.config.raster_enabled = False
        
        metadata = {
            "name": "Test Location",
            "temperature_ts": "tsId(100)"
        }
        
        is_valid = self.discovery.validate_metadata(metadata)
        self.assertFalse(is_valid)


class TestDataFetcher(unittest.TestCase):
    """Test data fetcher service."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_client = Mock()
        self.config = Mock(spec=Config)
        self.config.raster_enabled = False
        self.config.raster_use_as_fallback = False
        
        self.data_fetcher = DataFetcher(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )

    def test_parse_time_series_reference_tsid(self):
        """Test parsing tsId reference."""
        result = self.data_fetcher._parse_time_series_reference("tsId(12345)")
        self.assertEqual(result, "12345")

    def test_parse_time_series_reference_tspath(self):
        """Test parsing tsPath reference."""
        self.data_fetcher._path_to_id_map = {
            "/org/location/temperature": "12345"
        }
        
        result = self.data_fetcher._parse_time_series_reference(
            "tsPath(/org/location/temperature)"
        )
        self.assertEqual(result, "12345")

    def test_parse_time_series_reference_exchangeid(self):
        """Test parsing exchangeId reference."""
        self.data_fetcher._exchange_id_to_id_map = {
            "TEMP_001": "12345"
        }
        
        result = self.data_fetcher._parse_time_series_reference(
            "exchangeId(TEMP_001)"
        )
        self.assertEqual(result, "12345")

    def test_set_timeseries_list(self):
        """Test building lookup maps from timeseries list."""
        timeseries_list = [
            {
                "id": "ts1",
                "path": "/org/loc/temp",
                "exchangeId": "TEMP_001",
                "unit": "°C"
            },
            {
                "id": "ts2",
                "path": "/org/loc/humidity",
                "exchangeId": "HUM_001",
                "unit": "%"
            }
        ]
        
        self.data_fetcher.set_timeseries_list(timeseries_list)
        
        self.assertEqual(len(self.data_fetcher._path_to_id_map), 2)
        self.assertEqual(len(self.data_fetcher._exchange_id_to_id_map), 2)
        self.assertEqual(self.data_fetcher._path_to_id_map["/org/loc/temp"], "ts1")
        self.assertEqual(self.data_fetcher._exchange_id_to_id_map["TEMP_001"], "ts1")

    def test_check_data_completeness_complete(self):
        """Test completeness check with all required data."""
        data = {
            "temperature": [[datetime.now(), 20.0]],
            "humidity": [[datetime.now(), 65.0]],
            "wind_speed": [[datetime.now(), 10.0]],
            "air_pressure": [[datetime.now(), 101.3]]
        }
        
        is_complete = self.data_fetcher.check_data_completeness(data)
        self.assertTrue(is_complete)

    def test_check_data_completeness_incomplete(self):
        """Test completeness check with missing data."""
        data = {
            "temperature": [[datetime.now(), 20.0]],
            "humidity": [[datetime.now(), 65.0]]
        }
        
        is_complete = self.data_fetcher.check_data_completeness(data)
        self.assertFalse(is_complete)


class TestSunshineService(unittest.TestCase):
    """Test sunshine calculation service."""

    def setUp(self):
        """Set up test fixtures."""
        self.sunshine_calc = SunshineCalculator(a=0.25, b=0.5, logger=Mock())
        self.sunshine_service = SunshineService(
            sunshine_calc=self.sunshine_calc,
            logger=Mock()
        )

    def test_calculate_from_direct_measurement(self):
        """Test using directly measured sunshine hours."""
        data = {}
        aggregates = {"sunshine_hours": 10.5}
        
        result = self.sunshine_service.calculate_sunshine_hours(
            data=data,
            aggregates=aggregates,
            latitude=46.0,
            day_number=172
        )
        
        self.assertEqual(result, 10.5)

    def test_calculate_from_global_radiation(self):
        """Test calculating from global radiation data."""
        data = {
            "global_radiation": [
                [datetime.now(), 500],
                [datetime.now(), 600],
                [datetime.now(), 550]
            ]
        }
        aggregates = {}
        
        result = self.sunshine_service.calculate_sunshine_hours(
            data=data,
            aggregates=aggregates,
            latitude=46.0,
            day_number=172
        )
        
        self.assertGreater(result, 0)
        self.assertLess(result, 24)

    def test_calculate_from_cloud_layers(self):
        """Test calculating from cloud layer data."""
        data = {}
        aggregates = {
            "low_cloud_octas": 2.0,
            "medium_cloud_octas": 3.0,
            "high_cloud_octas": 1.0
        }
        
        result = self.sunshine_service.calculate_sunshine_hours(
            data=data,
            aggregates=aggregates,
            latitude=46.0,
            day_number=172
        )
        
        self.assertGreater(result, 0)
        self.assertLess(result, 24)

    def test_fallback_to_zero_no_data(self):
        """Test fallback returns zero when no data available."""
        data = {}
        aggregates = {}
        
        result = self.sunshine_service.calculate_sunshine_hours(
            data=data,
            aggregates=aggregates,
            latitude=46.0,
            day_number=172
        )
        
        self.assertEqual(result, 0.0)


class TestDataWriter(unittest.TestCase):
    """Test data writer service."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_client = Mock()
        self.writer = DataWriter(
            api_client=self.api_client,
            logger=Mock()
        )

    def test_write_evaporation_value(self):
        """Test writing single evaporation value."""
        self.api_client.write_time_series_value = Mock(return_value={"status": "success"})
        
        result = self.writer.write_evaporation_value(
            time_series_id="ts123",
            date=datetime(2024, 6, 21, tzinfo=timezone.utc),
            evaporation=5.5,
            organization_id="org123"
        )
        
        self.assertTrue(result)
        self.api_client.write_time_series_value.assert_called_once()

    def test_write_batch_values(self):
        """Test writing batch of values."""
        self.api_client.write_time_series_value = Mock(return_value={"status": "success"})
        
        results = {
            "ts1": {
                "date": datetime(2024, 6, 21, tzinfo=timezone.utc),
                "evaporation": 5.5,
                "organization_id": "org123"
            },
            "ts2": {
                "date": datetime(2024, 6, 21, tzinfo=timezone.utc),
                "evaporation": 6.2,
                "organization_id": "org123"
            }
        }
        
        status = self.writer.write_batch_values(results)
        
        self.assertEqual(len(status), 2)
        self.assertTrue(all(status.values()))
        self.assertEqual(self.api_client.write_time_series_value.call_count, 2)

    def test_create_write_metadata(self):
        """Test creating write metadata."""
        aggregates = {
            "t_min": 15.0,
            "t_max": 28.0,
            "rh_min": 40.0,
            "rh_max": 80.0,
            "wind_speed_avg": 12.5,
            "air_pressure_avg": 101.3,
            "sunshine_hours": 10.5
        }
        
        location_metadata = {
            "name": "Lake Como",
            "organization_name": "Test Org"
        }
        
        metadata = self.writer.create_write_metadata(aggregates, location_metadata)
        
        self.assertIn("inputs", metadata)
        self.assertIn("location", metadata)
        self.assertEqual(metadata["inputs"]["t_min"], 15.0)
        self.assertEqual(metadata["location"]["name"], "Lake Como")


class TestServiceIntegration(unittest.TestCase):
    """Test integration between multiple services."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_client = Mock()
        self.config = Mock(spec=Config)
        self.config.raster_enabled = False

    def test_discovery_to_fetcher_workflow(self):
        """Test workflow from discovery to data fetching."""
        discovery = TimeSeriesDiscovery(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )
        
        fetcher = DataFetcher(
            api_client=self.api_client,
            config=self.config,
            logger=Mock()
        )
        
        mock_timeseries = [
            {
                "id": "ts1",
                "path": "/org/loc/temp",
                "unit": "°C"
            }
        ]
        
        self.api_client.get_time_series_list = Mock(return_value=mock_timeseries)
        
        discovery.discover_lake_evaporation_series("org123")
        cached = discovery.get_cached_timeseries()
        
        fetcher.set_timeseries_list(cached)
        
        resolved = fetcher._parse_time_series_reference("tsPath(/org/loc/temp)")
        self.assertEqual(resolved, "ts1")

    def test_fetcher_to_sunshine_workflow(self):
        """Test workflow from data fetching to sunshine calculation."""
        sunshine_calc = SunshineCalculator(a=0.25, b=0.5, logger=Mock())
        sunshine_service = SunshineService(
            sunshine_calc=sunshine_calc,
            logger=Mock()
        )
        
        mock_data = {
            "global_radiation": [
                [datetime.now(), 500],
                [datetime.now(), 600]
            ]
        }
        
        aggregates = {}
        
        sunshine_hours = sunshine_service.calculate_sunshine_hours(
            data=mock_data,
            aggregates=aggregates,
            latitude=46.0,
            day_number=172
        )
        
        self.assertGreater(sunshine_hours, 0)
        self.assertLess(sunshine_hours, 24)


if __name__ == "__main__":
    unittest.main()
