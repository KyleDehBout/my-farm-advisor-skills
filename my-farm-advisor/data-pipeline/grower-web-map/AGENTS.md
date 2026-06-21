# Grower Web Map Local Instructions

## Purpose

This subskill owns the `generate_grower_web_map.py` reporting script. It reads field boundary GeoJSON files already produced by the main pipeline and generates a lightweight, self-contained Leaflet HTML map per grower.

## Safe edit scope

Stay within `data-pipeline/grower-web-map/` and `data-pipeline/src/scripts/reporting/generate_grower_web_map.py`. Do not touch other pipeline scripts, shared lib modules, or parent skill docs unless the user explicitly asks.

## Read nearby docs first

Read `GUIDE.md` (this folder) and `../README.md` before changing the script or workflow. Check `../AGENTS.md` for the full runtime contract (DATA_PIPELINE_DATA_ROOT, rsync seeding rules, venv paths).

## Local workflow notes

**Generate a map (from runtime src directory):**

```bash
export DATA_PIPELINE_DATA_ROOT=/path/to/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_grower_web_map.py --grower-slug illinois-grower
```

**Sync script from skill checkout to runtime after editing:**

```bash
rsync -av \
  "data-pipeline/src/scripts/reporting/generate_grower_web_map.py" \
  "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src/scripts/reporting/"
```

**Script dependencies:** stdlib only (`json`, `pathlib`, `argparse`, `os`, `re`, `urllib.request`). No extra pip installs.

**Leaflet vendor cache:** Downloaded once to `shared/vendor/leaflet/1.9.4/` on first run. Subsequent runs skip the download. Marker image CSS refs are replaced with an empty data URI since the map uses polygons only, not point markers.

**Output:** `growers/{grower_slug}/derived/maps/grower_web_map.html` — typically 200–400 KB, fully self-contained except for OSM tile requests.

## Local validation

After editing the script, seed it to the runtime and regenerate for one grower:

```bash
rsync -av data-pipeline/src/scripts/reporting/generate_grower_web_map.py \
  "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src/scripts/reporting/"
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_grower_web_map.py --grower-slug illinois-grower
```

Open the output HTML in a browser and confirm: polygons render, clicking a field shows a popup with grower/farm/field/county/area, and the sidebar field list zooms to each field.

## Local-delta-only reminder

This AGENTS.md only records instructions that differ from the parent. See `../AGENTS.md` and `../../../AGENTS.md` for root-level runtime contract, environment variable conventions, and safe-seeding rules.
