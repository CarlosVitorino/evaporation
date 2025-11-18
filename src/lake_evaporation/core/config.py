"""
Configuration module for lake evaporation estimation system.

Loads configuration from JSON file and environment variables.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

from . import constants


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
        self._validate_config()

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

    def _validate_config(self) -> None:
        """Validate that required configuration keys are present."""
        required_config = {
            "api": ["base_url", "timeout", "max_retries"],
            "authentication": [],  # Either username or email is required, validated below
            "processing": ["timezone", "run_hour"],
        }

        # Validate required sections
        missing_sections = []
        for section in required_config.keys():
            if section not in self.config:
                missing_sections.append(section)

        if missing_sections:
            raise ValueError(
                f"Missing required configuration sections: {', '.join(missing_sections)}"
            )

        # Validate required keys within sections
        missing_keys = []
        for section, keys in required_config.items():
            if section not in self.config:
                continue
            for key in keys:
                if key not in self.config[section]:
                    missing_keys.append(f"{section}.{key}")

        if missing_keys:
            raise ValueError(
                f"Missing required configuration keys: {', '.join(missing_keys)}"
            )

        # Validate authentication: either username or email must be present
        auth = self.config.get("authentication", {})
        if not auth.get("username") and not auth.get("email"):
            raise ValueError(
                "Authentication configuration must include either 'username' or 'email'"
            )

        # Validate that password is present
        if not auth.get("password"):
            raise ValueError("Authentication configuration must include 'password'")

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
    def api_verify_ssl(self) -> bool:
        """Get API SSL verification setting."""
        return self.get("api.verify_ssl", True)

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
        return self.get("constants.albedo", constants.DEFAULT_ALBEDO)

    @property
    def raster_datasource_id(self) -> int:
        """Get raster datasource ID."""
        datasource_id = self.get("raster.datasource_id")
        if datasource_id is None:
            raise ValueError("Missing required configuration: raster.datasource_id")
        return datasource_id

    @property
    def raster_enabled(self) -> bool:
        """Check if raster data fetching is enabled."""
        return self.get("raster.enabled", False)

    @property
    def raster_use_as_fallback(self) -> bool:
        """Check if raster should be used as fallback."""
        return self.get("raster.use_as_fallback", False)

    @property
    def raster_europe_model(self) -> str:
        """Get raster model for Europe."""
        model = self.get("raster.models.europe")
        if model is None:
            raise ValueError("Missing required configuration: raster.models.europe")
        return model

    @property
    def raster_global_model(self) -> str:
        """Get raster model for global/non-Europe."""
        model = self.get("raster.models.global")
        if model is None:
            raise ValueError("Missing required configuration: raster.models.global")
        return model

    @property
    def raster_parameters(self) -> Dict[str, str]:
        """
        Get raster parameter mappings.
        
        Note: This returns a generic mapping. Use get_raster_parameters_for_model()
        to get model-specific mappings.
        """
        params = self.get("raster.parameters")
        if params is None:
            raise ValueError("Missing required configuration: raster.parameters")
        
        # For backward compatibility, if parameters is not model-specific,
        # return it directly
        if not isinstance(params, dict):
            raise ValueError("raster.parameters must be a dictionary")
        
        # Check if it's model-specific (nested dict) or generic
        first_value = next(iter(params.values()), None)
        if isinstance(first_value, dict):
            # Model-specific configuration - return the first model's params as default
            # This is for backward compatibility only
            return next(iter(params.values()))
        
        # Generic configuration
        return params
    
    def get_raster_parameters_for_model(self, model: str) -> Dict[str, str]:
        """
        Get raster parameter mappings for a specific model.
        
        Args:
            model: Model identifier (e.g., "nwp_obslike/dwd/icon_eu")
            
        Returns:
            Dictionary mapping parameter types to parameter names for this model
            
        Raises:
            ValueError: If model parameters are not found
        """
        params = self.get("raster.parameters")
        if params is None:
            raise ValueError("Missing required configuration: raster.parameters")
        
        # Check if configuration is model-specific
        if model in params:
            model_params = params[model]
            if not isinstance(model_params, dict):
                raise ValueError(f"Invalid parameter configuration for model {model}")
            return model_params
        
        # Fallback: check if it's a generic configuration (backward compatibility)
        first_value = next(iter(params.values()), None)
        if not isinstance(first_value, dict):
            return params
        
        raise ValueError(
            f"No raster parameters found for model '{model}'. "
            f"Available models: {', '.join(params.keys())}"
        )

    def __repr__(self) -> str:
        """String representation of config."""
        return f"Config(file={self.config_file}, env={self.get('environment')})"
