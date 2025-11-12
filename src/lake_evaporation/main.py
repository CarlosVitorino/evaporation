"""
Main entry point for lake evaporation estimation system.

Orchestrates the daily evaporation calculation workflow.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .core import Config, setup_logger, LoggerContext, constants
from .api import KistersAPI
from .services import TimeSeriesDiscovery, DataFetcher, DataWriter
from .processing import DataProcessor
from .algorithms import EvaporationCalculator, SunshineCalculator


class LakeEvaporationApp:
    """Main application for lake evaporation estimation."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize application.

        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_file)

        # Setup logger
        self.logger = setup_logger()
        self.logger.info("=" * 60)
        self.logger.info("Lake Evaporation Estimation System")
        self.logger.info("=" * 60)
        self.logger.info(f"Configuration: {self.config}")

        # Initialize components (will be set in initialize_components)
        self.api_client: Optional[KistersAPI] = None
        self.discovery: Optional[TimeSeriesDiscovery] = None
        self.data_fetcher: Optional[DataFetcher] = None
        self.processor: Optional[DataProcessor] = None
        self.evaporation_calc: Optional[EvaporationCalculator] = None
        self.sunshine_calc: Optional[SunshineCalculator] = None
        self.writer: Optional[DataWriter] = None

    def initialize_components(self) -> None:
        """Initialize all application components."""
        self.logger.info("Initializing components...")

        # API Client with new authentication
        self.api_client = KistersAPI(
            base_url=self.config.api_base_url,
            username=self.config.auth_username,
            email=self.config.auth_email,
            password=self.config.auth_password,
            timeout=self.config.api_timeout,
            max_retries=self.config.api_max_retries,
            verify_ssl=self.config.api_verify_ssl,
            logger=self.logger
        )

        # Login to the portal
        self.logger.info("Logging in to KISTERS Web Portal...")
        self.api_client.login()

        # Discovery (works across all organizations)
        self.discovery = TimeSeriesDiscovery(
            api_client=self.api_client,
            logger=self.logger
        )

        # Data Fetcher
        self.data_fetcher = DataFetcher(
            api_client=self.api_client,
            logger=self.logger
        )

        # Processor
        self.processor = DataProcessor(logger=self.logger)

        # Evaporation Calculator
        self.evaporation_calc = EvaporationCalculator(logger=self.logger)

        # Sunshine Calculator
        angstrom = self.config.get("constants.angstrom_prescott", {})
        self.sunshine_calc = SunshineCalculator(
            a=angstrom.get("a", constants.DEFAULT_ANGSTROM_A),
            b=angstrom.get("b", constants.DEFAULT_ANGSTROM_B),
            logger=self.logger
        )

        # Writer
        self.writer = DataWriter(
            api_client=self.api_client,
            logger=self.logger
        )

        self.logger.info("All components initialized successfully")

    def run(self, target_date: Optional[datetime] = None) -> None:
        """
        Run the evaporation calculation for a specific date.

        Args:
            target_date: Date to calculate evaporation for. If None, uses previous day.
        """
        try:
            # Initialize components
            self.initialize_components()
            
            # Type narrowing: assert components are initialized
            assert self.discovery is not None, "Discovery service not initialized"
            assert self.data_fetcher is not None, "Data fetcher not initialized"
            assert self.processor is not None, "Processor not initialized"
            assert self.evaporation_calc is not None, "Evaporation calculator not initialized"
            assert self.sunshine_calc is not None, "Sunshine calculator not initialized"
            assert self.writer is not None, "Writer not initialized"

            # Determine target date (previous day if not specified)
            if target_date is None:
                target_date = datetime.now() - timedelta(days=1)

            target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            self.logger.info(f"Calculating evaporation for: {target_date.date()}")

            # Discover all lake evaporation time series across all organizations and cache all timeseries
            with LoggerContext(self.logger, "time series discovery"):
                time_series_list = self.discovery.get_all_evaporation_timeseries()

            if not time_series_list:
                self.logger.warning("No lake evaporation time series found")
                return

            self.logger.info(f"Processing {len(time_series_list)} time series")

            # Get cached timeseries for lookup (to resolve tsPath and exchangeId)
            with LoggerContext(self.logger, "timeseries lookup initialization"):
                cached_timeseries = self.discovery.get_cached_timeseries()
                self.data_fetcher.set_timeseries_list(cached_timeseries)

            # Process each location
            results = {}
            for time_series in time_series_list:
                try:
                    result = self.process_location(time_series, target_date)
                    if result:
                        results[time_series["time_series_id"]] = result
                except Exception as e:
                    self.logger.error(
                        f"Failed to process time series {time_series.get('name')}: {e}",
                        exc_info=True
                    )

            # Write results
            if results:
                self.logger.info(f"Writing {len(results)} results")
                status = self.writer.write_batch_values(results)
                self.writer.log_write_summary(status, results)
            else:
                self.logger.warning("No results to write")

            self.logger.info("Processing complete")

        except Exception as e:
            self.logger.error(f"Application error: {e}", exc_info=True)
            raise

        finally:
            if self.api_client:
                self.api_client.close()

    def process_location(
        self,
        location: dict,
        target_date: datetime
    ) -> Optional[dict]:
        """
        Process a single location.

        Args:
            location: Location metadata
            target_date: Date to calculate for

        Returns:
            Result dictionary or None if processing failed
        """
        # Type narrowing: assert components are initialized
        assert self.discovery is not None, "Discovery service not initialized"
        assert self.data_fetcher is not None, "Data fetcher not initialized"
        assert self.processor is not None, "Processor not initialized"
        assert self.evaporation_calc is not None, "Evaporation calculator not initialized"
        assert self.sunshine_calc is not None, "Sunshine calculator not initialized"
        assert self.writer is not None, "Writer not initialized"

        location_name = location.get("name", "Unknown")
        self.logger.info(f"Processing location: {location_name}")

        # Validate metadata
        if not self.discovery.validate_metadata(location):
            self.logger.error(f"Invalid metadata for {location_name}")
            return None

        # Fetch daily data
        with LoggerContext(self.logger, f"data fetch for {location_name}"):
            data, actual_units = self.data_fetcher.fetch_daily_data(location, target_date)

        # Check data completeness
        if not self.data_fetcher.check_data_completeness(data):
            self.logger.error(f"Incomplete data for {location_name}")
            return None

        # Calculate daily aggregates (min, max, mean)
        with LoggerContext(self.logger, f"aggregation for {location_name}"):
            aggregates = self.processor.calculate_daily_aggregates(data)

        # Convert units (use actual units from timeseries, fall back to config)
        source_units = self.config.get("units", {})
        aggregates = self.processor.convert_units(aggregates, source_units, actual_units)

        # Validate aggregates
        is_valid, errors = self.processor.validate_aggregates(aggregates)
        if not is_valid:
            self.logger.error(f"Invalid aggregates for {location_name}: {errors}")
            return None

        # Calculate sunshine hours if not directly measured
        if "sunshine_hours" not in aggregates:
            if "global_radiation" in data and data["global_radiation"]:
                self.logger.info("Calculating sunshine hours from global radiation")
                location_info = location.get("location", {})
                latitude = location_info.get("latitude", 0)
                day_number = target_date.timetuple().tm_yday

                sunshine = self.sunshine_calc.calculate_from_data_points(
                    radiation_data=data["global_radiation"],
                    latitude=latitude,
                    day_number=day_number
                )
                aggregates["sunshine_hours"] = sunshine
            else:
                self.logger.warning("No sunshine hours or global radiation data available")
                aggregates["sunshine_hours"] = 0

        # Calculate evaporation
        with LoggerContext(self.logger, f"evaporation calculation for {location_name}"):
            evaporation = self.evaporation_calc.calculate_with_metadata(
                aggregates=aggregates,
                location_metadata=location,
                date=target_date,
                albedo=self.config.albedo
            )

        self.logger.info(f"Calculated evaporation: {evaporation:.2f} mm/day")

        # Prepare result
        result = {
            "date": target_date,
            "evaporation": evaporation,
            "location_name": location_name,
            "organization_id": location.get("organization_id"),
            "metadata": self.writer.create_write_metadata(aggregates, location)
        }

        return result


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lake Evaporation Estimation System"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date (YYYY-MM-DD). Default: yesterday"
    )

    args = parser.parse_args()

    # Parse target date
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            sys.exit(1)

    # Run application
    try:
        app = LakeEvaporationApp(config_file=args.config)
        app.run(target_date=target_date)
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
