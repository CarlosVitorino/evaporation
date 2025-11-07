# Lake Evaporation Algorithm Documentation

## Overview

This document describes the algorithms used in the lake evaporation estimation system.

## Shuttleworth Algorithm

The Shuttleworth algorithm is used to calculate daily lake evaporation based on meteorological measurements.

### Required Inputs

| Parameter | Symbol | Unit | Description |
|-----------|--------|------|-------------|
| Minimum Temperature | T_min | °C | Daily minimum air temperature |
| Maximum Temperature | T_max | °C | Daily maximum air temperature |
| Minimum Humidity | RH_min | % | Daily minimum relative humidity |
| Maximum Humidity | RH_max | % | Daily maximum relative humidity |
| Wind Speed | u_10 | km/h | Average wind speed at 10m height |
| Air Pressure | P | kPa | Average air pressure at station height |
| Sunshine Hours | n | hours | Actual sunshine duration |
| Latitude | φ | degrees | Location latitude |
| Altitude | z | meters | Station elevation |
| Day of Year | J | 1-366 | Julian day number |
| Albedo | α | - | Surface albedo (0.23 for water) |

### Algorithm Steps

#### 1. Basic Calculations

**Mean Temperature:**
```
T_mean = (T_min + T_max) / 2
```

**Mean Relative Humidity:**
```
RH_mean = (RH_min + RH_max) / 2
```

#### 2. Vapor Pressure Calculations

**Saturation Vapor Pressure (Tetens formula):**
```
e_s(T) = 0.6108 × exp((17.27 × T) / (T + 237.3))
```

**Mean Saturation Vapor Pressure:**
```
e_s_mean = (e_s(T_min) + e_s(T_max)) / 2
```

**Actual Vapor Pressure:**
```
e_a = (RH_mean / 100) × e_s_mean
```

**Vapor Pressure Deficit:**
```
VPD = e_s_mean - e_a
```

#### 3. Psychrometric Constant

```
γ = 0.000665 × P
```

Where:
- γ = psychrometric constant (kPa/°C)
- P = atmospheric pressure (kPa)

#### 4. Slope of Vapor Pressure Curve

```
Δ = (4098 × e_s_mean) / (T_mean + 237.3)²
```

#### 5. Solar Radiation Calculations

**Solar Declination:**
```
δ = 0.409 × sin((2π/365) × J - 1.39)
```

**Sunset Hour Angle:**
```
ω_s = arccos(-tan(φ_rad) × tan(δ))
```

**Relative Earth-Sun Distance:**
```
d_r = 1 + 0.033 × cos((2π/365) × J)
```

**Extraterrestrial Radiation:**
```
R_a = (24×60/π) × G_sc × d_r × [ω_s × sin(φ_rad) × sin(δ) + cos(φ_rad) × cos(δ) × sin(ω_s)]
```

Where:
- G_sc = solar constant = 0.0820 MJ/m²/min
- φ_rad = latitude in radians
- R_a = extraterrestrial radiation (MJ/m²/day)

**Maximum Daylight Hours:**
```
N = (24/π) × ω_s
```

**Solar Radiation (using Ångström-Prescott equation):**
```
R_s = (a + b × (n/N)) × R_a
```

Where:
- a, b = Ångström-Prescott coefficients (typically a=0.25, b=0.5)
- n = actual sunshine hours
- N = maximum possible sunshine hours

**Net Shortwave Radiation:**
```
R_ns = (1 - α) × R_s
```

**Clear-Sky Radiation:**
```
R_so = (0.75 + 2×10⁻⁵ × z) × R_a
```

**Net Longwave Radiation:**
```
R_nl = σ × [(T_max_K⁴ + T_min_K⁴)/2] × (0.34 - 0.14√e_a) × (1.35 × (R_s/R_so) - 0.35)
```

Where:
- σ = Stefan-Boltzmann constant = 4.903×10⁻⁹ MJ/K⁴/m²/day
- T_K = temperature in Kelvin = T_C + 273.16

**Net Radiation:**
```
R_n = R_ns - R_nl
```

#### 6. Evaporation Calculation

**Penman-Monteith Equation for Open Water:**
```
ET_0 = (0.408 × Δ × R_n + γ × (900/(T_mean + 273)) × u_2 × VPD) / (Δ + γ × (1 + 0.34 × u_2))
```

Where:
- ET_0 = reference evapotranspiration (mm/day)
- u_2 = wind speed at 2m height (m/s)

**Wind Speed Adjustment (10m to 2m):**
```
u_2 = u_10 × (4.87) / (ln(67.8 × 10 - 5.42))
```

**Lake Evaporation:**
```
E_lake = K_lake × ET_0
```

Where:
- K_lake = lake coefficient (typically 1.05-1.20 depending on water body size)

### Output

The final output is daily lake evaporation in mm/day.

## Ångström-Prescott Method

Used to estimate sunshine hours from global radiation measurements.

### Equation

```
n = N × ((R_s/R_a) - a) / b
```

Where:
- n = actual sunshine hours
- N = maximum possible sunshine hours (daylight hours)
- R_s = measured global radiation (MJ/m²/day)
- R_a = extraterrestrial radiation (MJ/m²/day)
- a, b = empirical coefficients (typically a=0.25, b=0.5)

### Constraints

```
0 ≤ n ≤ N
```

Sunshine hours cannot be negative or exceed the maximum daylight hours.

## Cloud Cover Method (Alternative)

When radiation data is not available, sunshine can be estimated from cloud cover:

```
n = N × (1 - C_total/100)
```

Where:
- C_total = weighted total cloud cover
- C_total = (C_low × 1.0 + C_mid × 0.6 + C_high × 0.3) / 1.9

## Data Processing

### Aggregation

From time series sensor data, the following daily aggregates are calculated:

- **Temperature**: Daily minimum and maximum from all measurements
- **Humidity**: Daily minimum and maximum from all measurements
- **Wind Speed**: Daily arithmetic mean
- **Air Pressure**: Daily arithmetic mean
- **Sunshine**: Daily sum (if measured hourly) or cumulative

### Unit Conversions

The system automatically converts sensor data to required units:

**Temperature:**
- Celsius ↔ Fahrenheit: F = C × 9/5 + 32
- Celsius ↔ Kelvin: K = C + 273.15

**Wind Speed:**
- km/h ↔ m/s: m/s = km/h / 3.6
- mph ↔ m/s: m/s = mph × 0.44704

**Pressure:**
- hPa ↔ kPa: kPa = hPa / 10
- atm ↔ kPa: kPa = atm × 101.325

### Data Validation

Aggregated data is validated against physical constraints:

- Temperature: T_min ≤ T_max
- Humidity: 0% ≤ RH ≤ 100%
- Wind Speed: u ≥ 0
- Pressure: 50 kPa < P < 120 kPa (reasonable atmospheric range)
- Sunshine: 0 ≤ n ≤ N

## Error Handling

### Missing Data

If required sensor data is missing:
1. Log the missing data type and location
2. Skip evaporation calculation for that location/day
3. Do not write a result value

### Invalid Data

If data fails validation:
1. Log the validation error with details
2. Skip evaporation calculation
3. Do not write a result value

### Calculation Failures

If the algorithm fails during calculation:
1. Log the exception with full traceback
2. Skip to next location
3. Do not write a partial result

## Future Enhancements

### Phase 2 Improvements

1. **Raster Data Integration**: Extract missing parameters from gridded NWP data
2. **Quality Control**: Additional data quality checks and outlier detection
3. **Gap Filling**: Interpolation methods for short data gaps
4. **Uncertainty Estimation**: Propagate measurement uncertainty through calculations

### Calibration

The algorithm may be calibrated for specific lakes by:
- Adjusting Ångström-Prescott coefficients (a, b)
- Tuning the lake coefficient (K_lake)
- Validating against direct evaporation measurements

## References

1. Allen, R.G., et al. (1998). "Crop evapotranspiration - Guidelines for computing crop water requirements". FAO Irrigation and drainage paper 56.
2. Shuttleworth, W.J. (1993). "Evaporation". Handbook of Hydrology.
3. Ångström, A. (1924). "Solar and terrestrial radiation". Quarterly Journal of the Royal Meteorological Society, 50: 121-126.

## Excel Implementation

The Excel implementation referenced in the project requirements contains the complete Shuttleworth algorithm with all intermediate calculations. Phase 2 of this project will implement the full algorithm based on the Excel reference, including:

- All intermediate calculations
- Proper handling of edge cases
- Validation of intermediate results
- Comparison with Excel output for verification

## Validation

To validate the implementation:

1. Compare outputs with Excel reference implementation
2. Test with known evaporation measurements
3. Verify physical reasonableness of results
4. Check sensitivity to input parameters

Typical expected ranges:
- Summer lake evaporation: 3-8 mm/day
- Winter lake evaporation: 0-2 mm/day
- Annual average: 2-4 mm/day (mid-latitudes)
