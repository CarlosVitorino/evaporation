"""
Pytest configuration and shared fixtures for all tests.
"""

import sys
from pathlib import Path

import pytest
import json

# Add the project root to sys.path so we can import from src
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def fixtures_dir():
    """Get the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_data(fixtures_dir):
    """Load sample sensor data from fixtures."""
    data_file = fixtures_dir / "sample_data.json"
    with open(data_file) as f:
        return json.load(f)


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring API access"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )
