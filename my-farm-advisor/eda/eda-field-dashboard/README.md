# Field Dashboard — eda-field-dashboard

## Selected Field

| Property | Value |
|---|---|
| Grower | nebraska-grower |
| Farm | nebraska-farm |
| Field ID | osm-796351098 |
| County | Merrick, Nebraska (FIPS 31-121) |
| Area | 24.4 acres |
| Prototype year | 2022 |
| CDL crop (2022) | Corn |

## Overview

This subskill generates a multi-panel dashboard image for a single field across all available years (2021–2025). The dashboard combines four vertically aligned panels sharing a common day-of-year axis:

1. **NDVI Time Series** — multi-year satellite NDVI with per-year CDL crop labels
2. **Precipitation** — daily bars for prototype year + 7-day rolling average + cumulative mean
3. **Temperature & Extremes** — daily min/max range, 5-year mean, heat waves, frost, and hot-day markers
4. **Cumulative GDD** — multi-year growing degree day accumulation (base 10°C) with yearly totals

## Crop History

| Year | CDL Crop | NDVI Scenes |
|---|---|---|
| 2021 | Corn | 17 |
| 2022 | Corn | 18 |
| 2023 | Soybeans | 18 |
| 2024 | Corn | 18 |
| 2025 | Soybeans | 17 |

The field follows a typical corn-soybean rotation pattern with complete satellite and weather coverage across all five years.

## Usage

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/my-farm-advisor-runtime
python src/generate_field_dashboard.py
```

Output: `growers/nebraska-grower/farms/nebraska-farm/fields/osm-796351098/derived/reports/field_dashboard.png`

## Assignment — Field Dashboard

**Skill / workflow:** `eda/eda-field-dashboard` — generates a 4-panel PNG dashboard
for a single field across all available years (2021–2025).

**Input files (relative to data-pipeline root):**

- `growers/nebraska-grower/farms/nebraska-farm/fields/osm-796351098/weather/daily_weather.csv`
- `growers/.../derived/tables/ndvi_year_crop_join.csv`
- `growers/.../boundary/field_boundary.geojson`
- `growers/.../satellite/{sentinel,landsat}/manifest.json` (lists all NDVI scenes)
- Individual NDVI GeoTIFFs referenced by manifest entries

**Weather metrics calculated:**

- Daily T2M_MAX, T2M_MIN, PRECTOTCORR for each of 5 years
- Growing degree days (base 10°C) from daily mean temperature
- Cumulative precipitation and GDD per year
- Heat waves (≥3 consecutive days T2M_MAX > 35°C)
- Frost days (T2M_MIN < 0°C within growing season DOY 80–300)
- 5-year mean daily temperature

**Dashboard output (relative to data-pipeline):**

`growers/nebraska-grower/farms/nebraska-farm/fields/osm-796351098/derived/reports/field_dashboard.png`

**Rerun:**

```bash
export DATA_PIPELINE_DATA_ROOT=/home/coder/my-farm-advisor-runtime
python src/generate_field_dashboard.py
```

**Known limitations:**

- NDVI data is limited to available scenes (87 valid measurements across 5 years);
  some months have 1 scene instead of 2 (e.g. May 2021), and 2 of 89 scenes were
  dropped for having no valid pixels within the field boundary.
- Weather data is point-based (NASA POWER grid cell center), not field-specific.
- GDD uses a simple base 10°C with no upper cutoff; actual crop-specific thresholds
  (e.g. 30°C cap for corn) are not applied.
