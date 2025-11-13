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

        if os.getenv("API_ORGANIZATION_ID"):
            self.config["api"]["organization_id"] = os.getenv("API_ORGANIZATION_ID")

        # Authentication
        if os.getenv("API_USERNAME"):
            if "authentication" not in self.config:
                self.config["authentication"] = {}
            self.config["authentication"]["username"] = os.getenv("API_USERNAME")

        if os.getenv("API_EMAIL"):
            if "authentication" not in self.config:
                self.config["authentication"] = {}
            self.config["authentication"]["email"] = os.getenv("API_EMAIL")

        if os.getenv("API_PASSWORD"):
            if "authentication" not in self.config:
                self.config["authentication"] = {}
            self.config["authentication"]["password"] = os.getenv("API_PASSWORD")

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
    def api_organization_id(self) -> Optional[str]:
        """
        Get API organization ID (optional).

        If not specified, the system will discover locations across all
        organizations that the user has access to.
        """
        return self.get("api.organization_id")

    @property
    def api_timeout(self) -> int:
        """Get API timeout in seconds."""
        return self.get("api.timeout", 30)

    @property
    def api_max_retries(self) -> int:
        """Get maximum API retry attempts."""
        return self.get("api.max_retries", 3)

    @property
    def auth_username(self) -> Optional[str]:
        """Get authentication username."""
        return self.get("authentication.username")

    @property
    def auth_email(self) -> Optional[str]:
        """Get authentication email."""
        return self.get("authentication.email")

    @property
    def auth_password(self) -> Optional[str]:
        """Get authentication password."""
        return self.get("authentication.password")

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

    @property
    def raster_datasource_id(self) -> int:
        """Get raster datasource ID."""
        return self.get("raster.datasource_id", 1)

    @property
    def raster_enabled(self) -> bool:
        """Check if raster data fetching is enabled."""
        return self.get("raster.enabled", True)

    @property
    def raster_use_as_fallback(self) -> bool:
        """Check if raster should be used as fallback."""
        return self.get("raster.use_as_fallback", True)

    @property
    def raster_europe_model(self) -> str:
        """Get raster model for Europe."""
        return self.get("raster.models.europe", "icon_eu")

    @property
    def raster_global_model(self) -> str:
        """Get raster model for global/non-Europe."""
        return self.get("raster.models.global", "gfs")

    @property
    def raster_parameters(self) -> Dict[str, str]:
        """Get raster parameter mappings."""
        return self.get("raster.parameters", {
            "temperature": "TMP_2M",
            "pressure": "PRMSL",
            "humidity": "RH_2M",
            "wind_speed": "FF_10M",
            "cloud": "TCDC"
        })

    def __repr__(self) -> str:
        """String representation of config."""
        return f"Config(file={self.config_file}, env={self.get('environment')})"
