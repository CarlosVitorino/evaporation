"""
Data writer module for writing evaporation results back to the API.

Handles writing calculated evaporation values to time series.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .api_client import APIClient


class DataWriter:
    """Write evaporation results to time series."""

    def __init__(self, api_client: APIClient, logger: Optional[logging.Logger] = None):
        """
        Initialize data writer.

        Args:
            api_client: API client instance
            logger: Logger instance
        """
        self.api_client = api_client
        self.logger = logger or logging.getLogger(__name__)

    def write_evaporation_value(
        self,
        time_series_id: str,
        date: datetime,
        evaporation: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Write evaporation value to time series.

        The value is written at midnight of the previous day and is valid for
        the whole previous day.

        Args:
            time_series_id: Time series ID to write to
            date: Date the evaporation was calculated for
            evaporation: Evaporation value in mm/day
            metadata: Optional metadata (calculation details, source data, etc.)

        Returns:
            True if successful, False otherwise
        """
        # Set timestamp to midnight of the date
        timestamp = date.replace(hour=0, minute=0, second=0, microsecond=0)

        self.logger.info(
            f"Writing evaporation value {evaporation:.2f} mm for {date.date()} "
            f"to time series {time_series_id}"
        )

        try:
            # Prepare metadata
            write_metadata = metadata or {}
            write_metadata.update({
                "calculation_date": datetime.now().isoformat(),
                "value_unit": "mm",
                "value_type": "daily_evaporation",
                "algorithm": "Shuttleworth"
            })

            # Write to API
            response = self.api_client.write_time_series_value(
                time_series_id=time_series_id,
                timestamp=timestamp.isoformat(),
                value=evaporation,
                metadata=write_metadata
            )

            self.logger.debug(f"Write response: {response}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to write evaporation value: {e}")
            return False

    def write_batch_values(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Write multiple evaporation values in batch.

        Args:
            results: Dictionary mapping time series IDs to result dictionaries
                    containing 'date', 'evaporation', and optional 'metadata'

        Returns:
            Dictionary mapping time series IDs to success status
        """
        self.logger.info(f"Writing {len(results)} evaporation values in batch")
        status = {}

        for ts_id, result in results.items():
            success = self.write_evaporation_value(
                time_series_id=ts_id,
                date=result["date"],
                evaporation=result["evaporation"],
                metadata=result.get("metadata")
            )
            status[ts_id] = success

        successful = sum(1 for s in status.values() if s)
        self.logger.info(f"Batch write complete: {successful}/{len(results)} successful")

        return status

    def create_write_metadata(
        self,
        aggregates: Dict[str, float],
        location_metadata: Dict[str, Any],
        calculation_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create metadata for written values.

        Args:
            aggregates: Input aggregates used in calculation
            location_metadata: Location metadata
            calculation_details: Additional calculation details

        Returns:
            Metadata dictionary
        """
        metadata = {
            "inputs": {
                "t_min": aggregates.get("t_min"),
                "t_max": aggregates.get("t_max"),
                "rh_min": aggregates.get("rh_min"),
                "rh_max": aggregates.get("rh_max"),
                "wind_speed_avg": aggregates.get("wind_speed_avg"),
                "air_pressure_avg": aggregates.get("air_pressure_avg"),
                "sunshine_hours": aggregates.get("sunshine_hours"),
            },
            "location": {
                "name": location_metadata.get("name"),
                "organization": location_metadata.get("organization_name"),
            }
        }

        if calculation_details:
            metadata["calculation"] = calculation_details

        return metadata

    def log_write_summary(
        self,
        status: Dict[str, bool],
        results: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Log summary of write operations.

        Args:
            status: Write status for each time series
            results: Results that were written
        """
        total = len(status)
        successful = sum(1 for s in status.values() if s)
        failed = total - successful

        self.logger.info("=" * 60)
        self.logger.info("Write Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Total locations: {total}")
        self.logger.info(f"Successful writes: {successful}")
        self.logger.info(f"Failed writes: {failed}")

        if failed > 0:
            self.logger.warning("Failed locations:")
            for ts_id, success in status.items():
                if not success:
                    result = results.get(ts_id, {})
                    self.logger.warning(f"  - {result.get('location_name', ts_id)}")

        self.logger.info("=" * 60)
