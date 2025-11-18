"""
Date and timezone utilities.

Centralizes all date/time operations with proper timezone handling.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz
from pytz.tzinfo import BaseTzInfo


class DateUtils:
    """Utilities for date and timezone handling."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize date utilities.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    @staticmethod
    def parse_timezone(timezone_str: str) -> BaseTzInfo:
        """
        Parse timezone string to pytz timezone object.

        Args:
            timezone_str: Timezone string (e.g., 'Europe/Berlin', 'UTC')

        Returns:
            pytz timezone object

        Raises:
            ValueError: If timezone is invalid
        """
        try:
            return pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {timezone_str}")

    def get_previous_day_range(
        self,
        timezone_str: str,
        reference_time: Optional[datetime] = None
    ) -> Tuple[datetime, datetime]:
        """
        Get the date range for the previous day in the specified timezone.

        Args:
            timezone_str: Timezone string (e.g., 'Europe/Berlin')
            reference_time: Reference time (defaults to now in UTC)

        Returns:
            Tuple of (start_datetime, end_datetime) for previous day in the timezone
            Both datetimes are timezone-aware

        Example:
            If current time is 2024-01-15 01:00:00 Europe/Berlin,
            returns (2024-01-14 00:00:00+01:00, 2024-01-14 23:59:59+01:00)
        """
        tz = self.parse_timezone(timezone_str)

        # Get reference time in the target timezone
        if reference_time is None:
            reference_time = datetime.now(pytz.UTC)
        elif reference_time.tzinfo is None:
            # Assume UTC if no timezone
            reference_time = pytz.UTC.localize(reference_time)

        # Convert to target timezone
        local_time = reference_time.astimezone(tz)

        self.logger.debug(
            f"Reference time: {reference_time.isoformat()} -> "
            f"Local time: {local_time.isoformat()}"
        )

        # Get previous day in local timezone
        previous_day = local_time.date() - timedelta(days=1)

        # Create start and end times for the previous day
        start_datetime = tz.localize(
            datetime.combine(previous_day, datetime.min.time())
        )
        end_datetime = tz.localize(
            datetime.combine(previous_day, datetime.max.time())
        )

        self.logger.info(
            f"Previous day range in {timezone_str}: "
            f"{start_datetime.isoformat()} to {end_datetime.isoformat()}"
        )

        return start_datetime, end_datetime

    def get_day_range(
        self,
        date: datetime,
        timezone_str: str
    ) -> Tuple[datetime, datetime]:
        """
        Get the full day range for a specific date in the specified timezone.

        Args:
            date: Date (can be naive or aware)
            timezone_str: Timezone string

        Returns:
            Tuple of (start_datetime, end_datetime) for the day
            Both datetimes are timezone-aware
        """
        tz = self.parse_timezone(timezone_str)

        # If date is naive, assume it's in the target timezone
        if date.tzinfo is None:
            date = tz.localize(date)
        else:
            # Convert to target timezone
            date = date.astimezone(tz)

        # Get the date part
        day = date.date()

        # Create start and end times
        start_datetime = tz.localize(
            datetime.combine(day, datetime.min.time())
        )
        end_datetime = tz.localize(
            datetime.combine(day, datetime.max.time())
        )

        return start_datetime, end_datetime

    @staticmethod
    def to_iso_with_timezone(dt: datetime) -> str:
        """
        Convert datetime to ISO format string with timezone.

        Args:
            dt: Datetime object (should be timezone-aware)

        Returns:
            ISO format string with timezone (e.g., '2024-01-15T00:00:00+01:00')

        Raises:
            ValueError: If datetime is not timezone-aware
        """
        if dt.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")

        return dt.isoformat()

    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """
        Convert datetime to UTC.

        Args:
            dt: Datetime object (can be naive or aware)

        Returns:
            Datetime in UTC (timezone-aware)
        """
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            return pytz.UTC.localize(dt)
        return dt.astimezone(pytz.UTC)

    @staticmethod
    def localize_to_timezone(dt: datetime, timezone_str: str) -> datetime:
        """
        Localize a naive datetime to a specific timezone.

        Args:
            dt: Naive datetime
            timezone_str: Timezone string

        Returns:
            Timezone-aware datetime

        Raises:
            ValueError: If datetime is already aware
        """
        if dt.tzinfo is not None:
            raise ValueError("Datetime is already timezone-aware")

        tz = pytz.timezone(timezone_str)
        return tz.localize(dt)

    @staticmethod
    def convert_to_timezone(dt: datetime, timezone_str: str) -> datetime:
        """
        Convert an aware datetime to a different timezone.

        Args:
            dt: Timezone-aware datetime
            timezone_str: Target timezone string

        Returns:
            Datetime in the target timezone

        Raises:
            ValueError: If datetime is naive
        """
        if dt.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")

        tz = pytz.timezone(timezone_str)
        return dt.astimezone(tz)
