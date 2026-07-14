---
name: eda-compare-growers
description: Cross-grower EDA comparing field boundaries, CDL/cropland data, and weather across multiple growers. Generates static comparison plots and summary tables for Assignment 2.
version: 1.0.0
author: Boreal Bytes
tags: [eda, comparison, growers, boundaries, cdl, weather, cross-grower]
---

# Workflow: Cross-Grower Comparison

## Description

Compare field boundaries, CDL/cropland data, and weather across multiple growers (Illinois, Iowa, Nebraska). Generates 9 static PNG plots and 1 CSV summary table organized into three categories:

- **Field Boundaries** (3 plots): size distribution, box plot comparison, location map
- **CDL / Cropland** (3 plots): crop composition, crop diversity, rotation patterns
- **Weather** (3 plots): seasonal climatology, growing season comparison, weather-crop correlation

This workflow is designed for the Assignment 2 dataset where all three growers have 10 fields each and soil analysis is not required.

## When to Use This Workflow

- **Cross-grower comparison**: Compare field characteristics across different states/regions
- **CDL patterns**: Understand how crop choices differ across geographies
- **Climate context**: Quantify weather differences that may drive management decisions
- **Quick survey**: Generate a complete set of comparison plots in a single run

## Prerequisites

```bash
pip install pandas geopandas matplotlib seaborn numpy
```

The runtime must have `DATA_PIPELINE_DATA_ROOT` set and the data pipeline must have been run for all target growers with boundary, CDL, and weather outputs available.

## Quick Start

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/eda/eda_compare_growers.py
```

Uses the default growers (illinois-grower, iowa-grower, nebraska-grower). Plots are written to `<DATA_ROOT>/growers/derived/reports/eda_compare_growers/`.

## Common Tasks

### Task 1: Run with Custom Growers

```bash
python scripts/eda/eda_compare_growers.py \
  --grower-slugs illinois-grower iowa-grower nebraska-grower
```

### Task 2: Specify a Custom Output Directory

```bash
python scripts/eda/eda_compare_growers.py \
  --output-dir /tmp/eda_output
```

### Task 3: Run a Single Category Independently

The script always runs all three categories, but each category checks for available data and skips gracefully if missing. To run only boundaries, you could source the relevant functions in a Python shell:

```python
import sys
from pathlib import Path
sys.path.insert(0, "scripts/lib")
from paths import GROWERS_ROOT
sys.path.insert(0, "scripts/eda")
from eda_compare_growers import load_all_data, plot_field_size_distribution

boundaries, cdl, rot, weather = load_all_data(["illinois-grower"])
out = GROWERS_ROOT / "derived" / "reports" / "eda_compare_growers"
out.mkdir(parents=True, exist_ok=True)
plot_field_size_distribution(boundaries, ["illinois-grower"], out)
```

## Complete Example

### Full Cross-Grower Comparison

```python
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

_SCRIPTS_DIR = Path("scripts").resolve()
sys.path.insert(0, str(_SCRIPTS_DIR / "lib"))
sys.path.insert(0, str(_SCRIPTS_DIR / "eda"))

from paths import DATA_ROOT
from eda_compare_growers import (
    load_all_data,
    plot_field_size_distribution,
    plot_field_size_boxplot,
    plot_boundary_location_map,
    plot_cdl_crop_composition,
    plot_cdl_crop_diversity,
    plot_cdl_rotation_comparison,
    plot_seasonal_climatology,
    plot_growing_season,
    plot_weather_crop_correlation,
    write_summary_table,
)

GROWERS = ["illinois-grower", "iowa-grower", "nebraska-grower"]
OUT_DIR = DATA_ROOT / "growers" / "derived" / "reports" / "eda_compare_growers"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading data ...")
boundaries, cdl, rotations, weather = load_all_data(GROWERS)

print("\nBoundary plots ...")
plot_field_size_distribution(boundaries, GROWERS, OUT_DIR)
plot_field_size_boxplot(boundaries, GROWERS, OUT_DIR)
plot_boundary_location_map(boundaries, GROWERS, OUT_DIR)

print("\nCDL plots ...")
plot_cdl_crop_composition(cdl, GROWERS, OUT_DIR)
plot_cdl_crop_diversity(rotations, GROWERS, OUT_DIR)
plot_cdl_rotation_comparison(rotations, GROWERS, OUT_DIR)

print("\nWeather plots ...")
plot_seasonal_climatology(weather, GROWERS, OUT_DIR)
plot_growing_season(weather, GROWERS, OUT_DIR)
plot_weather_crop_correlation(weather, cdl, GROWERS, OUT_DIR)

print("\nSummary ...")
write_summary_table(boundaries, cdl, rotations, weather, GROWERS, OUT_DIR)

print(f"\nDone. All outputs in: {OUT_DIR}")
```

## Output Files

| File | Category | Type | Description |
|------|----------|------|-------------|
| `boundary_field_size_distribution.png` | Boundaries | Stat viz | Histogram of field area by grower, with mean annotation |
| `boundary_field_size_boxplot.png` | Boundaries | Stat viz | Box + strip plot of field sizes with μ/M labels and jitter |
| `boundary_location_map.png` | Boundaries | Geospatial map | True polygon boundaries colored by grower, with area labels |
| `boundary_crop_correlation.png` | Boundaries | Correlation | Field area vs corn % scatter with trend lines and Pearson r |
| `cdl_crop_composition.png` | CDL | Stat viz | Grouped bar of mean crop percentages (top 4 crops) |
| `cdl_crop_diversity.png` | CDL | Stat viz | Violin + strip plot of unique crop types per field |
| `cdl_field_crop_tile.png` | CDL | Comparison | Tile/heatmap: dominant crop per field per year, faceted by grower |
| `cdl_rotation_comparison.png` | CDL | Comparison | Rotation pattern fractions (Corn→Soy, Corn→Corn, etc.) |
| `weather_seasonal_climatology.png` | Weather | Stat viz | Monthly T2M (±1σ) and precipitation by grower |
| `weather_growing_season.png` | Weather | Stat viz | Apr–Sep T2M and precip per year; faint lines = per-field variability |
| `weather_crop_correlation.png` | Weather | Correlation | Field-level precip vs corn % with trend lines and Pearson r |
| `grower_comparison_summary.csv` | Summary | Table | Per-grower aggregate stats (field count, mean area, corn/soy %, T2M, precip) |
| `field_level_summary.csv` | Summary | Table | Per-field raw data (area, corn/soy %, diversity, T2M, precip) for all 30 fields |

## Data Sources

Each grower's data is loaded from the standard pipeline output paths:

- **Boundaries**: `<farm>/boundary/field_boundaries.geojson` — field polygons with `area_acres`, `county_name`, `state_fips`
- **CDL composition**: `<farm>/derived/tables/<prefix>_cdl_2021_2025_full_composition.csv` — per-field crop percentages by year
- **Crop rotation**: `<farm>/derived/tables/<prefix>_crop_rotation.csv` — rotation sequences, diversity, predictions
- **Weather**: `<farm>/derived/tables/<prefix>_weather_2021_2025.csv` — daily T2M, PRECTOTCORR, RH2M, WS10M per field

All tables join on `field_id` (e.g., `osm-1035467708`).

## Best Practices

- Run the farm pipeline first with `--skip-soil` for all target growers before running this EDA
- Review the `grower_comparison_summary.csv` table first for a quick numeric overview, then inspect the plots for distribution details
- The weather-crop correlation is most informative at the field level; outliers often have small field size or unusual CDL classifications
- For deeper dives into any single category, refer to the more focused guides:
  - [Explore Guide](../eda-explore/GUIDE.md) for per-grower summaries
  - [Correlate Guide](../eda-correlate/GUIDE.md) for pairwise relationships
  - [Time Series Guide](../eda-time-series/GUIDE.md) for seasonal weather patterns

## Common Issues

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| No data loaded for a grower | Pipeline not run for that grower | Run `bootstrap_farm_from_county.py --run-pipeline --skip-soil` |
| Missing weather table | Weather step skipped or failed | Check pipeline logs; verify `farm_weather_path()` exists |
| CDL composition missing | CDL step not completed | Run `run_farm_pipeline.py` with CDL step enabled |
| Rotation table missing | CDL pipeline step didn't generate rotation | Verify `farm_cdl_rotation_path()` exists |

## Resources

- Source script: `scripts/eda/eda_compare_growers.py`
- Path helpers: `scripts/lib/paths.py`
- Pipeline runner: `scripts/run_farm_pipeline.py`
- Grower bootstrap: `scripts/ingest/bootstrap_farm_from_county.py`
