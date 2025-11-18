"""
Shuttleworth lake evaporation calculation module.

Implements the complete Shuttleworth algorithm for calculating daily lake evaporation
based on meteorological data. This implementation follows the methodology from the
reference Excel spreadsheet (ShuttleworthLakeEvaporation.xlsm).

The Shuttleworth method combines:
- Aerodynamic component (Ea): Based on wind speed and vapor pressure deficit
- Radiation component (Er): Based on net radiation

Reference:
    Shuttleworth, W.J. (1993). Evaporation. In: Maidment, D.R. (ed.) Handbook of
    Hydrology, McGraw-Hill, New York.
"""

import math
from typing import Dict, Tuple
from dataclasses import dataclass

from ..core import constants

@dataclass
class EvaporationComponents:
    """Container for evaporation calculation components and intermediate values."""

    # Final results
    evaporation_total: float  # mm/day
    aerodynamic_component: float  # mm/day
    radiation_component: float  # mm/day

    # Wind parameters
    u10_ms: float  # m/s
    u2: float  # m/s at 2m height

    # Vapor pressure parameters
    es_tmax: float  # kPa
    es_tmin: float  # kPa
    es: float  # Mean saturation vapor pressure (kPa)
    ea: float  # Actual vapor pressure (kPa)
    vpd: float  # Vapor pressure deficit (kPa)

    # Psychrometric parameters
    tmean: float  # °C
    delta: float  # Slope of vapor pressure curve (kPa/°C)
    gamma: float  # Psychrometric constant (kPa/°C)
    lambda_v_mg: float  # Combined parameter

    # Radiation parameters
    ra: float  # Extraterrestrial radiation (MJ m⁻² day⁻¹)
    rs: float  # Solar radiation (MJ m⁻² day⁻¹)
    rso: float  # Clear sky solar radiation (MJ m⁻² day⁻¹)
    rns: float  # Net shortwave radiation (MJ m⁻² day⁻¹)
    rnl: float  # Net longwave radiation (MJ m⁻² day⁻¹)
    rn: float  # Net radiation (MJ m⁻² day⁻¹)
    n: float  # Daylight hours
    sunshine_ratio: float  # n/N ratio


class ShuttleworthCalculator:
    """
    Calculator for lake evaporation using the Shuttleworth algorithm.

    This class encapsulates all calculation logic for the Shuttleworth method,
    keeping the implementation modular and testable.
    """

    @staticmethod
    def calculate_lake_evaporation(
        t_max: float,
        t_min: float,
        rh_max: float,
        rh_min: float,
        u10: float,
        sunshine_hours: float,
        pressure: float,
        latitude: float,
        altitude: float,
        day_number: int,
        albedo: float = constants.DEFAULT_ALBEDO
    ) -> float:
        """
        Calculate daily lake evaporation using the Shuttleworth algorithm.

        Args:
            t_max: Daily maximum temperature (°C)
            t_min: Daily minimum temperature (°C)
            rh_max: Daily maximum relative humidity (%)
            rh_min: Daily minimum relative humidity (%)
            u10: Average wind speed at 10m height (km/h)
            sunshine_hours: Actual hours of sunshine (hours)
            pressure: Atmospheric pressure at station height (kPa)
            latitude: Site latitude (degrees, -90 to 90)
            altitude: Site elevation above sea level (meters)
            day_number: Julian day of the year (1-365/366)
            albedo: Surface albedo/reflectance (dimensionless, typically 0.23 for water)

        Returns:
            Daily lake evaporation (mm/day)
        """
        components = ShuttleworthCalculator.calculate_with_components(
            t_max=t_max,
            t_min=t_min,
            rh_max=rh_max,
            rh_min=rh_min,
            u10=u10,
            sunshine_hours=sunshine_hours,
            pressure=pressure,
            latitude=latitude,
            altitude=altitude,
            day_number=day_number,
            albedo=albedo
        )
        return components.evaporation_total

    @staticmethod
    def calculate_with_components(
        t_max: float,
        t_min: float,
        rh_max: float,
        rh_min: float,
        u10: float,
        sunshine_hours: float,
        pressure: float,
        latitude: float,
        altitude: float,
        day_number: int,
        albedo: float = constants.DEFAULT_ALBEDO
    ) -> EvaporationComponents:
        """
        Calculate lake evaporation with detailed intermediate components.

        This method returns all intermediate calculation values, useful for
        debugging, validation, and detailed analysis.

        Args:
            Same as calculate_lake_evaporation()

        Returns:
            EvaporationComponents object containing all intermediate values
        """
        # SECTION 1: Wind Speed Adjustments
        u10_ms, u2 = ShuttleworthCalculator._adjust_wind_speed(u10)

        # SECTION 2: Vapor Pressure Calculations
        es_tmax, es_tmin, es, ea, vpd = ShuttleworthCalculator._calculate_vapor_pressures(
            t_max, t_min, rh_max, rh_min
        )

        # SECTION 3: Derived Meteorological Parameters
        tmean = (t_max + t_min) / 2
        delta = ShuttleworthCalculator._calculate_slope_vapor_pressure_curve(tmean)
        gamma = ShuttleworthCalculator._calculate_psychrometric_constant(pressure)
        lambda_v_mg = constants.LATENT_HEAT_VAPORIZATION * (delta + gamma)

        # SECTION 4: Solar Radiation Calculations
        ra, n, sunshine_ratio, rs, rso = ShuttleworthCalculator._calculate_solar_radiation(
            latitude, altitude, day_number, sunshine_hours
        )

        # SECTION 5: Net Radiation
        rns, rnl, rn = ShuttleworthCalculator._calculate_net_radiation(
            rs, rso, t_max, t_min, ea, albedo
        )

        # SECTION 6: Evaporation Components
        ea_component = ShuttleworthCalculator._calculate_aerodynamic_component(
            gamma, u2, vpd, lambda_v_mg
        )

        er_component = ShuttleworthCalculator._calculate_radiation_component(
            delta, rn, lambda_v_mg
        )

        # SECTION 7: Final Calculation
        evaporation_total = ea_component + er_component

        return EvaporationComponents(
            evaporation_total=evaporation_total,
            aerodynamic_component=ea_component,
            radiation_component=er_component,
            u10_ms=u10_ms,
            u2=u2,
            es_tmax=es_tmax,
            es_tmin=es_tmin,
            es=es,
            ea=ea,
            vpd=vpd,
            tmean=tmean,
            delta=delta,
            gamma=gamma,
            lambda_v_mg=lambda_v_mg,
            ra=ra,
            rs=rs,
            rso=rso,
            rns=rns,
            rnl=rnl,
            rn=rn,
            n=n,
            sunshine_ratio=sunshine_ratio
        )

    # =========================================================================
    # SECTION 1: Wind Speed Adjustments
    # =========================================================================

    @staticmethod
    def _adjust_wind_speed(u10_kmh: float) -> Tuple[float, float]:
        """
        Convert wind speed from km/h to m/s and adjust from 10m to 2m height.

        Args:
            u10_kmh: Wind speed at 10m height (km/h)

        Returns:
            Tuple of (u10_ms, u2):
                - u10_ms: Wind speed at 10m height (m/s)
                - u2: Wind speed at 2m height (m/s)
        """
        u10_ms = u10_kmh / 3.6  # Convert km/h to m/s
        u2 = constants.WIND_HEIGHT_ADJUSTMENT * u10_ms  # Adjust from 10m to 2m height
        return u10_ms, u2

    # =========================================================================
    # SECTION 2: Vapor Pressure Calculations
    # =========================================================================

    @staticmethod
    def _calculate_saturation_vapor_pressure(temperature: float) -> float:
        """
        Calculate saturation vapor pressure at a given temperature using Tetens formula.

        Args:
            temperature: Temperature (°C)

        Returns:
            Saturation vapor pressure (kPa)
        """
        return constants.TETENS_A * math.exp(
            (constants.TETENS_B * temperature) / (temperature + constants.TETENS_C)
        )

    @staticmethod
    def _calculate_vapor_pressures(
        t_max: float,
        t_min: float,
        rh_max: float,
        rh_min: float
    ) -> Tuple[float, float, float, float, float]:
        """
        Calculate all vapor pressure parameters.

        Args:
            t_max: Maximum temperature (°C)
            t_min: Minimum temperature (°C)
            rh_max: Maximum relative humidity (%)
            rh_min: Minimum relative humidity (%)

        Returns:
            Tuple of (es_tmax, es_tmin, es, ea, vpd):
                - es_tmax: Saturation vapor pressure at Tmax (kPa)
                - es_tmin: Saturation vapor pressure at Tmin (kPa)
                - es: Mean saturation vapor pressure (kPa)
                - ea: Actual vapor pressure (kPa)
                - vpd: Vapor pressure deficit (kPa)
        """
        # Saturation vapor pressures
        es_tmax = ShuttleworthCalculator._calculate_saturation_vapor_pressure(t_max)
        es_tmin = ShuttleworthCalculator._calculate_saturation_vapor_pressure(t_min)

        # Mean saturation vapor pressure
        es = (es_tmax + es_tmin) / 2

        # Actual vapor pressure (calculated from RH at Tmax and Tmin)
        ea = (es_tmax * rh_max / 100 + es_tmin * rh_min / 100) / 2

        # Vapor pressure deficit
        vpd = es - ea

        return es_tmax, es_tmin, es, ea, vpd

    # =========================================================================
    # SECTION 3: Psychrometric Parameters
    # =========================================================================

    @staticmethod
    def _calculate_slope_vapor_pressure_curve(t_mean: float) -> float:
        """
        Calculate the slope of saturation vapor pressure curve at mean temperature.

        Args:
            t_mean: Mean temperature (°C)

        Returns:
            Slope of vapor pressure curve (kPa/°C)
        """
        # Calculate saturation vapor pressure at mean temperature
        es_tmean = ShuttleworthCalculator._calculate_saturation_vapor_pressure(t_mean)

        # Slope calculation: delta = 4096 * [0.6108 * exp(...)] / (Tmean + 237.3)²
        delta = (4096 * es_tmean) / ((t_mean + constants.TETENS_C) ** 2)

        return delta

    @staticmethod
    def _calculate_psychrometric_constant(pressure: float) -> float:
        """
        Calculate psychrometric constant.

        Args:
            pressure: Atmospheric pressure (kPa)

        Returns:
            Psychrometric constant (kPa/°C)
        """
        return constants.PSYCHROMETRIC_COEF * pressure

    # =========================================================================
    # SECTION 4: Solar Radiation Calculations
    # =========================================================================

    @staticmethod
    def _calculate_solar_declination(day_number: int) -> float:
        """
        Calculate solar declination for a given day of the year.

        Args:
            day_number: Julian day of the year (1-365/366)

        Returns:
            Solar declination (radians)
        """
        return constants.SOLAR_DECLINATION_AMPLITUDE * math.sin(
            (2 * math.pi / 365) * day_number - constants.SOLAR_DECLINATION_PHASE
        )

    @staticmethod
    def _calculate_extraterrestrial_radiation(
        latitude: float,
        day_number: int
    ) -> Tuple[float, float, float]:
        """
        Calculate extraterrestrial radiation and related parameters.

        Args:
            latitude: Latitude (degrees)
            day_number: Julian day of the year (1-365/366)

        Returns:
            Tuple of (Ra, N, omega_s):
                - Ra: Extraterrestrial radiation (MJ m⁻² day⁻¹)
                - N: Daylight hours (hours)
                - omega_s: Sunset hour angle (radians)
        """
        # Convert latitude to radians
        phi = math.radians(latitude)

        # Solar declination
        solar_decl = ShuttleworthCalculator._calculate_solar_declination(day_number)

        # Inverse relative distance Earth-Sun
        dr = 1 + constants.EARTH_ORBIT_ECCENTRICITY * math.cos(2 * math.pi * day_number / 365)

        # Sunset hour angle
        omega_s = math.acos(-math.tan(phi) * math.tan(solar_decl))

        # Extraterrestrial radiation
        ra = (24 * 60 / math.pi) * constants.SOLAR_CONSTANT * dr * (
            omega_s * math.sin(phi) * math.sin(solar_decl) +
            math.cos(phi) * math.cos(solar_decl) * math.sin(omega_s)
        )

        # Daylight hours
        n_max = (24 / math.pi) * omega_s

        return ra, n_max, omega_s

    @staticmethod
    def _calculate_solar_radiation(
        latitude: float,
        altitude: float,
        day_number: int,
        sunshine_hours: float
    ) -> Tuple[float, float, float, float, float]:
        """
        Calculate solar radiation parameters using Ångström-Prescott equation.

        Args:
            latitude: Latitude (degrees)
            altitude: Altitude (meters)
            day_number: Julian day of the year (1-365/366)
            sunshine_hours: Actual sunshine hours (hours)

        Returns:
            Tuple of (Ra, N, n_N, Rs, Rso):
                - Ra: Extraterrestrial radiation (MJ m⁻² day⁻¹)
                - N: Maximum daylight hours (hours)
                - n_N: Sunshine ratio (dimensionless)
                - Rs: Solar radiation (MJ m⁻² day⁻¹)
                - Rso: Clear sky solar radiation (MJ m⁻² day⁻¹)
        """
        # Extraterrestrial radiation and daylight hours
        ra, n_max, _ = ShuttleworthCalculator._calculate_extraterrestrial_radiation(
            latitude, day_number
        )

        # Sunshine ratio
        n_n = sunshine_hours / n_max if n_max > 0 else 0

        # Solar radiation (Ångström-Prescott equation)
        rs = (constants.ANGSTROM_A + constants.ANGSTROM_B * n_n) * ra

        # Clear sky solar radiation
        rso = (constants.CLEAR_SKY_COEF + constants.ALTITUDE_FACTOR * altitude) * ra

        return ra, n_max, n_n, rs, rso

    # =========================================================================
    # SECTION 5: Net Radiation
    # =========================================================================

    @staticmethod
    def _calculate_net_radiation(
        rs: float,
        rso: float,
        t_max: float,
        t_min: float,
        ea: float,
        albedo: float
    ) -> Tuple[float, float, float]:
        """
        Calculate net radiation components.

        Args:
            rs: Solar radiation (MJ m⁻² day⁻¹)
            rso: Clear sky solar radiation (MJ m⁻² day⁻¹)
            t_max: Maximum temperature (°C)
            t_min: Minimum temperature (°C)
            ea: Actual vapor pressure (kPa)
            albedo: Surface albedo (dimensionless)

        Returns:
            Tuple of (Rns, Rnl, Rn):
                - Rns: Net shortwave radiation (MJ m⁻² day⁻¹)
                - Rnl: Net longwave radiation (MJ m⁻² day⁻¹)
                - Rn: Net radiation (MJ m⁻² day⁻¹)
        """
        # Net shortwave radiation
        rns = (1 - albedo) * rs

        # Rs/Rso ratio for cloud factor
        rs_rso = rs / rso if rso > 0 else 0

        # Net longwave radiation (Stefan-Boltzmann)
        tmax_k4 = (t_max + 273.16) ** 4
        tmin_k4 = (t_min + 273.16) ** 4

        rnl = (
            constants.STEFAN_BOLTZMANN * (tmax_k4 + tmin_k4) / 2 *
            (constants.NLW_CONST_1 - constants.NLW_CONST_2 * math.sqrt(ea)) *
            (constants.NLW_CONST_3 * rs_rso - constants.NLW_CONST_4)
        )

        # Net radiation
        rn = rns - rnl

        return rns, rnl, rn

    # =========================================================================
    # SECTION 6: Evaporation Components
    # =========================================================================

    @staticmethod
    def _calculate_aerodynamic_component(
        gamma: float,
        u2: float,
        vpd: float,
        lambda_v_mg: float
    ) -> float:
        """
        Calculate aerodynamic component of evaporation.

        Args:
            gamma: Psychrometric constant (kPa/°C)
            u2: Wind speed at 2m height (m/s)
            vpd: Vapor pressure deficit (kPa)
            lambda_v_mg: Combined parameter λ(Δ+γ) (MJ/kg)

        Returns:
            Aerodynamic component (mm/day)
        """
        ea = (gamma * constants.AERODYNAMIC_RESISTANCE_COEF *
              (1 + constants.WIND_FACTOR * u2) * vpd) / lambda_v_mg

        return ea

    @staticmethod
    def _calculate_radiation_component(
        delta: float,
        rn: float,
        lambda_v_mg: float
    ) -> float:
        """
        Calculate radiation component of evaporation.

        Args:
            delta: Slope of vapor pressure curve (kPa/°C)
            rn: Net radiation (MJ m⁻² day⁻¹)
            lambda_v_mg: Combined parameter λ(Δ+γ) (MJ/kg)

        Returns:
            Radiation component (mm/day)
        """
        er = (delta * rn) / lambda_v_mg

        return er
