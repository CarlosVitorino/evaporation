"""
Configuration module for lake evaporation estimation system.

Loads configuration from JSON file and environment variables.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Configuration manager for the application."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to configuration JSON file. If None, uses CONFIG_FILE env var
                        or defaults to 'config.json'
        """
        self.config_file = config_file or os.getenv("CONFIG_FILE", "config.json")
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._override_from_env()

    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def _override_from_env(self) -> None:
        """Override configuration with environment variables."""
        # API configuration
        if os.getenv("API_BASE_URL"):
            self.config["api"]["base_url"] = os.getenv("API_BASE_URL")

        # Environment
        if os.getenv("ENVIRONMENT"):
            self.config["environment"] = os.getenv("ENVIRONMENT")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation).

        Args:
            key: Configuration key (e.g., 'api.base_url')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    @property
    def api_base_url(self) -> str:
        """Get API base URL."""
        return self.get("api.base_url", "")

    @property
    def api_timeout(self) -> int:
        """Get API timeout in seconds."""
        return self.get("api.timeout", 30)

    @property
    def api_max_retries(self) -> int:
        """Get maximum API retry attempts."""
        return self.get("api.max_retries", 3)

    @property
    def timezone(self) -> str:
        """Get processing timezone."""
        return self.get("processing.timezone", "UTC")

    @property
    def run_hour(self) -> int:
        """Get scheduled run hour."""
        return self.get("processing.run_hour", 1)

    @property
    def lake_evaporation_tag(self) -> str:
        """Get lake evaporation tag name."""
        return self.get("tags.lake_evaporation", "lakeEvaporation")

    @property
    def albedo(self) -> float:
        """Get albedo constant."""
        return self.get("constants.albedo", 0.23)

    def __repr__(self) -> str:
        """String representation of config."""
        return f"Config(file={self.config_file}, env={self.get('environment')})"
