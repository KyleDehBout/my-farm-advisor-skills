---
name: eda-field-dashboard
description: Generate a per-field multi-year dashboard combining NDVI, weather, and CDL crop data. Produces a single summary image for all years of a selected field.
version: 1.0.0
author: Boreal Bytes
tags: [dashboard, ndvi, weather, cdl, visualization, field]
---

# Workflow: eda-field-dashboard

## Description

Generates a multi-panel dashboard image for a single field across all available years. The dashboard combines:
- **NDVI time series** — mean NDVI extracted from per-scene satellite imagery across each growing season
- **Daily weather** — temperature (max/min) and precipitation from NASA POWER
- **CDL crop labels** — dominant crop identified from USDA Cropland Data Layer for each year

The output is a single PNG image saved under the field's `derived/reports/` directory.

## When to Use This Workflow

- **Field-level analysis** — inspect a single field's vegetation and weather history
- **Year-over-year comparison** — compare NDVI trajectories and weather across seasons
- **Crop rotation review** — verify modeled rotation against observed CDL labels
- **Report generation** — create dashboard images for farm reports or grower summaries

## Selected Field

| Property | Value |
|---|---|
| Grower | nebraska-grower |
| Farm | nebraska-farm |
| Field ID | osm-796351098 |
| County | Merrick, Nebraska |
| Area | 24.4 acres |
| Prototype year | 2022 |
| CDL crop (2022) | Corn |

## Prerequisites

```bash
pip install pandas matplotlib numpy rasterio geopandas scipy
```

The script reads from the canonical runtime tree at `${DATA_PIPELINE_DATA_ROOT}/data-pipeline`.

## Quick Start

Generate a dashboard for the default field (nebraska-grower / nebraska-farm / osm-796351098):

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/my-farm-advisor-runtime
python src/generate_field_dashboard.py
```

Generate a dashboard for a different field:

```bash
python src/generate_field_dashboard.py \
  --grower-slug nebraska-grower \
  --farm-slug nebraska-farm \
  --field-id osm-796351098
```

## Common Tasks

### Task 1: Generate Dashboard for the Selected Field

**What**: Produce the multi-year NDVI + weather + CDL dashboard.

**When to use**: Default field-year analysis.

**Code**:

```python
from pathlib import Path
import os

DATA_ROOT = Path(os.environ["DATA_PIPELINE_DATA_ROOT"])
field_dir = DATA_ROOT / "data-pipeline/growers/nebraska-grower/farms/nebraska-farm/fields/osm-796351098"

# The dashboard script accepts CLI arguments or environment variables
# Run from this directory:
# python src/generate_field_dashboard.py
```

### Task 2: Interpret the Dashboard

**What**: Read the generated dashboard image.

**Panels**:
- **NDVI panel** (top): Each year is a colored line showing mean NDVI through the growing season (Mar–Nov). Annotations mark peak NDVI, rapid increases (green arrows), and rapid decreases (red arrows). CDL crop labels appear in the legend.
- **Temperature panel** (middle): Shaded bands show max/min temperatures per day across all years. Hot days (>35°C) are marked as red scatter points. Heat waves (3+ consecutive hot days) are highlighted with red shading and duration labels.
- **Precipitation panel** (3rd): Blue bars show 7-day rolling average precipitation. A secondary axis shows cumulative precipitation (blue line, right axis). Heavy rain events (>20mm) are marked with diamond markers and callout labels.
- **Event caption** (bottom): Summary of notable events — peak NDVI values, fastest green-up, sharpest decline, heat-wave statistics, and heavy-rain count.

**Crop labels**: Each NDVI line is annotated with its CDL-determined crop (Corn or Soybeans), making rotation patterns visible at a glance.

## Complete Example

```python
import subprocess
import sys
from pathlib import Path

script = Path(__file__).parent / "src/generate_field_dashboard.py"
result = subprocess.run(
    [sys.executable, str(script)],
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print(result.stderr)
```

## Data Sources

| Source | Description | Path |
|---|---|---|
| Field boundary | GeoJSON polygon | `growers/{grower}/farms/{farm}/fields/{field}/boundary/field_boundary.geojson` |
| NDVI scenes | Per-scene NDVI GeoTIFFs | `growers/{grower}/farms/{farm}/fields/{field}/satellite/{sensor}/{year}/*_ndvi.tif` |
| Crop join | Yearly crop label + composite path | `growers/{grower}/farms/{farm}/fields/{field}/derived/tables/ndvi_year_crop_join.csv` |
| Weather | Daily NASA POWER data | `growers/{grower}/farms/{farm}/fields/{field}/weather/daily_weather.csv` |
| CDL composition | Full field-year crop breakdown | `growers/{grower}/farms/{farm}/derived/tables/{farm}_cdl_*_full_composition.csv` |

## Customization

To select a different field, pass `--grower-slug`, `--farm-slug`, and `--field-id` to the script. The runtime base is read from `DATA_PIPELINE_DATA_ROOT`.

## Design Notes

- **Clean data preferred**: The selected field-year (osm-796351098, 2022 Corn) was chosen because it has complete NDVI coverage (18 scenes), full weather records, and a clear CDL label — not because it shows dramatic variability.
- **All years rendered**: The dashboard always shows all available years for the field, not just the prototype year.
- **No external API calls**: All data is read from pre-computed local assets.
