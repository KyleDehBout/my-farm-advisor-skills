---
name: grower-web-map
description: Generate a lightweight, self-contained Leaflet HTML web map for each grower showing real field polygon boundaries, click popups with metadata, and a sidebar field list. Leaflet assets are downloaded once to the shared vendor cache; OSM basemap tiles load at view time.
version: 1.0.0
author: Boreal Bytes
tags: [web-map, visualization, leaflet, grower, field-boundaries, interactive, html]
---

# Workflow: grower-web-map

## Description

Generates a single self-contained HTML map per grower. The map reads the actual downloaded field boundary polygons from the pipeline output and renders them on an OpenStreetMap basemap using Leaflet.js. No rasters, imagery bundles, or large embedded assets are included — only field coordinates and metadata.

**Output per grower:**

```
growers/{grower_slug}/derived/maps/grower_web_map.html
```

**Map features:**

- All field polygons for the grower, loaded from `farms/{farm_slug}/boundary/field_boundaries.geojson`
- OpenStreetMap basemap (loads from internet at view time)
- Click any field → popup showing Grower, Farm, Field, County, and Area (acres)
- Sidebar field list — click any row to fly the map to that field
- `fitBounds` on all fields at load; zoom in/out freely
- Leaflet JS + CSS embedded inline (downloaded once to `shared/vendor/leaflet/1.9.4/`)
- Output size: typically 200–400 KB for a grower with 3–6 fields

## Prerequisites

- `DATA_PIPELINE_DATA_ROOT` exported (points to the runtime root)
- The grower's farm pipeline must have already run so `boundary/field_boundaries.geojson` exists
- Internet access the first time (to download Leaflet assets); subsequent runs use the cache
- Standard library Python only — no additional pip installs needed

## Running the Map Generator

From the runtime source directory:

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
VENV="${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python"

# Generate map for a specific grower
"$VENV" scripts/reporting/generate_grower_web_map.py --grower-slug illinois-grower

# Override the data root on the fly
"$VENV" scripts/reporting/generate_grower_web_map.py \
  --grower-slug iowa-grower \
  --data-root /path/to/my-farm-advisor-runtime
```

## Seeding into the Runtime

The script lives in `data-pipeline/src/scripts/reporting/` in the skill checkout. Copy it to the runtime with:

```bash
rsync -av \
  "skills/my-farm-advisor-skills/my-farm-advisor/data-pipeline/src/scripts/reporting/generate_grower_web_map.py" \
  "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src/scripts/reporting/"
```

A full `install.sh` run also picks it up automatically on the next re-seed.

## Output Locations

| Asset | Path |
|---|---|
| Grower web map HTML | `growers/{grower_slug}/derived/maps/grower_web_map.html` |
| Leaflet JS cache | `shared/vendor/leaflet/1.9.4/leaflet.min.js` |
| Leaflet CSS cache | `shared/vendor/leaflet/1.9.4/leaflet.min.css` |

## Viewing the Map

Open the output HTML directly in any modern browser:

```bash
open "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/illinois-grower/derived/maps/grower_web_map.html"
```

The map works offline after the first load because Leaflet is embedded inline. Only the OSM basemap tiles require an internet connection each time the map is opened.
