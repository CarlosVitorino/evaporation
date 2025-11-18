"""
Application-wide constants for lake evaporation estimation.

This module defines default values and constants used throughout the application.
Physical constants specific to algorithms are defined in their respective modules.
"""

# Data completeness thresholds
# Minimum fraction of expected data points required for valid calculations
MIN_DATA_COMPLETENESS = 0.75  # 75% of data must be present

# Physical Constants
LATENT_HEAT_VAPORIZATION = 2.45  # MJ/kg
SOLAR_CONSTANT = 0.0820  # MJ m⁻² min⁻¹
STEFAN_BOLTZMANN = 4.903e-9  # MJ K⁻⁴ m⁻² day⁻¹

# Vapor Pressure Constants (Tetens formula)
TETENS_A = 0.6108  # kPa
TETENS_B = 17.27
TETENS_C = 237.3  # °C

# Wind Adjustment
WIND_HEIGHT_ADJUSTMENT = 0.748  # 10m to 2m height
AERODYNAMIC_RESISTANCE_COEF = 6.43
WIND_FACTOR = 0.536

# Psychrometric Constant Coefficient
PSYCHROMETRIC_COEF = 0.665e-3  # kPa/°C

# Default Albedo (reflectivity) for water surfaces
# Typical range for water: 0.05-0.30
DEFAULT_ALBEDO = 0.23

# Radiation Constants (Ångström-Prescott)
ANGSTROM_A = 0.25
ANGSTROM_B = 0.5
CLEAR_SKY_COEF = 0.75
ALTITUDE_FACTOR = 2e-5

# Net Longwave Radiation Constants
NLW_CONST_1 = 0.34
NLW_CONST_2 = 0.14
NLW_CONST_3 = 1.35
NLW_CONST_4 = 0.35

# Solar Geometry Constants
EARTH_ORBIT_ECCENTRICITY = 0.033
SOLAR_DECLINATION_AMPLITUDE = 0.409
SOLAR_DECLINATION_PHASE = 1.39  # radians