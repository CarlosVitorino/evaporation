"""
Application-wide constants for lake evaporation estimation.

This module defines default values and constants used throughout the application.
Physical constants specific to algorithms are defined in their respective modules.
"""

# Default Albedo (reflectivity) for water surfaces
# Typical range for water: 0.05-0.30
DEFAULT_ALBEDO = 0.23

# Default Ångström-Prescott coefficients for sunshine-based solar radiation estimation
# These represent the relationship between sunshine duration and solar radiation
# a: fraction of extraterrestrial radiation on overcast days
# b: additional fraction with maximum sunshine
DEFAULT_ANGSTROM_A = 0.25
DEFAULT_ANGSTROM_B = 0.5

# Data completeness thresholds
# Minimum fraction of expected data points required for valid calculations
MIN_DATA_COMPLETENESS = 0.75  # 75% of data must be present
