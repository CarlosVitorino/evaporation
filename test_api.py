#!/usr/bin/env python3
"""
API Connection Test Script

Quick script to test API connectivity and authentication without running the full application.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lake_evaporation.core import Config, setup_logger
from lake_evaporation.api import KistersAPI


def test_api_connection():
    """Test basic API connection and authentication."""
    print("=" * 60)
    print("Lake Evaporation API Connection Test")
    print("=" * 60)
    print()

    # Load configuration
    try:
        config = Config()
        print(f"✓ Configuration loaded from: {config.config_file}")
        print(f"  API Base URL: {config.api_base_url}")
        print()
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        print("\nMake sure you have:")
        print("  1. Copied .env.example to .env")
        print("  2. Copied config.json.example to config.json")
        print("  3. Updated credentials in .env or config.json")
        return False

    # Setup logger
    logger = setup_logger(log_level="DEBUG")

    # Test API connection
    print("Testing API connection...")
    print("-" * 60)

    try:
        # Create API client
        api = KistersAPI(
            base_url=config.api_base_url,
            username=config.auth_username,
            email=config.auth_email,
            password=config.auth_password,
            timeout=config.api_timeout,
            max_retries=config.api_max_retries,
            logger=logger
        )
        print("✓ API client created")
        print()

        # Test login
        print("Attempting login...")
        user_data = api.login()
        print(f"✓ Login successful!")
        print(f"  User: {user_data.get('userName', 'Unknown')}")
        print(f"  Email: {user_data.get('email', 'N/A')}")
        print()

        # Test getting organizations
        print("Fetching organizations...")
        orgs = api.get_organizations()
        print(f"✓ Found {len(orgs)} organization(s)")
        for i, org in enumerate(orgs, 1):
            print(f"  {i}. {org.get('name', 'Unknown')} (ID: {org.get('id', 'N/A')})")
        print()

        # Test getting locations from first organization
        if orgs:
            org_id = orgs[0].get('id')
            print(f"Fetching locations from organization: {orgs[0].get('name')}...")
            locations = api.get_locations(org_id)
            print(f"✓ Found {len(locations)} location(s)")
            if locations:
                print(f"  Sample locations (showing first 5):")
                for loc in locations[:5]:
                    print(f"    - {loc.get('name', 'Unknown')} (ID: {loc.get('id', 'N/A')})")
            print()

            # Test getting time series
            print(f"Fetching time series from organization: {orgs[0].get('name')}...")
            timeseries = api.get_time_series_list(
                org_id,
                include_location_data=True,
                include_coverage=True
            )
            print(f"✓ Found {len(timeseries)} time series")

            # Check for lake evaporation metadata
            lake_evap_count = 0
            for ts in timeseries:
                metadata = ts.get("metadata", {})
                if "lakeEvaporation" in metadata:
                    lake_evap_count += 1

            print(f"  Time series with lakeEvaporation metadata: {lake_evap_count}")
            print()

        # Logout
        print("Logging out...")
        api.logout()
        print("✓ Logout successful")
        print()

        print("=" * 60)
        print("✓ All API tests passed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ API test failed: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    success = test_api_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
