"""
API connection integration tests.

Tests authentication and basic API operations with the KISTERS Web Portal.
These tests require valid credentials in .env or config.json.
"""

import pytest  # type: ignore
import os

from src.lake_evaporation.core import Config
from src.lake_evaporation.api import KistersAPI


@pytest.fixture(scope="module")
def config():
    """Load configuration for API tests."""
    print("\n=== CONFIG FIXTURE CALLED ===")  # Debug print
    try:
        cfg = Config()
        print(f"Config loaded: {cfg}")
        return cfg
    except FileNotFoundError as e:
        print(f"Config file not found: {e}")
        pytest.skip("Configuration file not found. Create config.json or .env with API credentials.")

@pytest.fixture(scope="module")
def api_client(config):
    """Create authenticated API client."""
    print("\n=== API CLIENT FIXTURE CALLED ===")  # Debug print
    print(f"Config: {config}")
    
    client = KistersAPI(
        base_url=config.api_base_url,
        username=config.auth_username,
        email=config.auth_email,
        password=config.auth_password,
        timeout=config.api_timeout,
        max_retries=config.api_max_retries,
        verify_ssl=config.api_verify_ssl,
    )

    try:
        print("Attempting login...")
        client.login()
        print("Login successful!")
        yield client
        print("Logging out...")
        client.logout()
    except Exception as e:
        print(f"API authentication failed: {e}")
        import traceback
        traceback.print_exc()
        #pytest.skip(f"API authentication failed: {e}")


class TestAPIConnection:
    """Test API connectivity and basic operations."""

    def test_authentication(self, api_client):
        """Test that authentication works."""
        print("\n=== TEST AUTHENTICATION CALLED ===")  # Add breakpoint here
        assert api_client.is_authenticated
        assert api_client.user_data is not None
        assert "userName" in api_client.user_data

    def test_get_organizations(self, api_client):
        """Test fetching organizations."""
        print("\n=== TEST GET ORGANIZATIONS CALLED ===")  # Add breakpoint here
        orgs = api_client.get_organizations()
        assert isinstance(orgs, list)
        # User should have access to at least one organization
        assert len(orgs) > 0

        # Check organization structure
        first_org = orgs[0]
        assert "id" in first_org
        assert "name" in first_org

    def test_get_locations(self, api_client):
        """Test fetching locations from an organization."""
        orgs = api_client.get_organizations()
        if not orgs:
            pytest.skip("No organizations available")

        org_id = orgs[0]["id"]
        locations = api_client.get_locations(org_id)

        assert isinstance(locations, list)
        # May or may not have locations, so just check type

    def test_get_time_series_list(self, api_client):
        """Test fetching time series from an organization."""
        orgs = api_client.get_organizations()
        if not orgs:
            pytest.skip("No organizations available")

        org_id = orgs[0]["id"]
        timeseries = api_client.get_time_series_list(
            org_id,
            include_location_data=True,
            include_coverage=True
        )

        assert isinstance(timeseries, list)

    def test_lake_evaporation_metadata(self, api_client):
        """Test finding time series with lake evaporation metadata."""
        orgs = api_client.get_organizations()
        if not orgs:
            pytest.skip("No organizations available")

        # Check all organizations for lake evaporation time series
        total_lake_evap = 0
        for org in orgs:
            org_id = org["id"]
            timeseries = api_client.get_time_series_list(org_id)

            for ts in timeseries:
                metadata = ts.get("metadata") or {}  # Handle None metadata
                if "lakeEvaporation" in metadata:
                    total_lake_evap += 1

        # Just log the count, don't fail if none found
        print(f"\nFound {total_lake_evap} time series with lakeEvaporation metadata")
