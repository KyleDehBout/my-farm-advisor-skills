#!/usr/bin/env python3
"""
generate_grower_web_map.py — Generate a self-contained Leaflet HTML web map for a grower.

Usage:
    python scripts/reporting/generate_grower_web_map.py --grower-slug illinois-grower

Reads field boundary GeoJSON files already produced by the main pipeline and writes a
single self-contained HTML file with Leaflet JS/CSS embedded inline.  OSM basemap tiles
load from the internet at view time.  No geopandas or additional packages required.

Output:
    {DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/{grower_slug}/derived/maps/grower_web_map.html

Leaflet assets are downloaded once to:
    {DATA_PIPELINE_DATA_ROOT}/data-pipeline/shared/vendor/leaflet/1.9.4/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import urlopen

_LEAFLET_VERSION = "1.9.4"
_LEAFLET_BASE_URL = f"https://unpkg.com/leaflet@{_LEAFLET_VERSION}/dist"
# Transparent 1×1 GIF — replaces marker image refs in Leaflet CSS (unused in polygon maps).
_EMPTY_GIF_URI = (
    "data:image/gif;base64,"
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)

# HTML template.  Uses [[PLACEHOLDER]] markers to avoid conflicts with Leaflet CSS/JS
# curly braces and the Leaflet tile URL {z}/{x}/{y} placeholders.
_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>[[GROWER_NAME]] — Field Map</title>
<style>
[[LEAFLET_CSS]]
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  height: 100vh;
  overflow: hidden;
}
#sidebar {
  width: 280px;
  min-width: 200px;
  background: #fff;
  border-right: 1px solid #ddd;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
#sidebar-header {
  padding: 14px 16px;
  background: #1B5E20;
  color: #fff;
  flex-shrink: 0;
}
#sidebar-header h1 {
  font-size: 1.0em;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
#sidebar-header .sub {
  font-size: 0.76em;
  opacity: 0.85;
  margin-top: 3px;
}
#field-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}
.field-row {
  padding: 9px 14px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.12s;
}
.field-row:hover {
  background: #f1f8e9;
}
.field-row:active {
  background: #dcedc8;
}
.field-id {
  display: block;
  font-size: 0.82em;
  font-weight: 600;
  color: #1B5E20;
  word-break: break-all;
}
.field-farm {
  display: block;
  font-size: 0.75em;
  color: #555;
  margin-top: 2px;
}
.field-detail {
  display: block;
  font-size: 0.73em;
  color: #888;
  margin-top: 1px;
}
#map { flex: 1; }
</style>
</head>
<body>
<div id="sidebar">
  <div id="sidebar-header">
    <h1>[[GROWER_NAME]]</h1>
    <div class="sub">
      [[FIELD_COUNT]] field[[FIELD_PLURAL]] &bull; [[FARM_COUNT]] farm[[FARM_PLURAL]]
    </div>
  </div>
  <div id="field-list">
[[FIELD_LIST_HTML]]
  </div>
</div>
<div id="map"></div>
<script>[[LEAFLET_JS]]</script>
<script>
var map = L.map('map');

L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGS, and the GIS User Community',
    maxZoom: 19
  }
).addTo(map);

var fieldData = [[GEOJSON]];

var geoLayer = L.geoJSON(fieldData, {
  style: {
    color: '#FFEB3B',
    weight: 2.5,
    fillColor: '#FFEB3B',
    fillOpacity: 0.18
  },
  onEachFeature: function(feature, layer) {
    var p = feature.properties || {};
    var areaStr = p.area_acres != null ? (+p.area_acres).toFixed(1) + ' ac' : '—';
    layer.bindPopup(
      '<b>Grower:</b> ' + (p.grower_name || '—') + '<br>' +
      '<b>Farm:</b> '   + (p.farm_name   || '—') + '<br>' +
      '<b>Field:</b> '  + (p.field_id    || '—') + '<br>' +
      '<b>County:</b> ' + (p.county_name || '—') + '<br>' +
      '<b>Area:</b> '   + areaStr
    );
    layer.on('mouseover', function() { layer.setStyle({ fillOpacity: 0.42 }); });
    layer.on('mouseout',  function() { geoLayer.resetStyle(layer); });
  }
}).addTo(map);

if (geoLayer.getBounds().isValid()) {
  map.fitBounds(geoLayer.getBounds(), { padding: [24, 24], maxZoom: 16 });
}

function flyToField(lat, lon) {
  map.flyTo([lat, lon], 14, { duration: 0.8 });
}
</script>
</body>
</html>
"""


def _read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _fetch_leaflet(vendor_dir: Path) -> tuple[str, str]:
    """Download Leaflet JS and CSS to vendor_dir (cached on disk). Return (js, css)."""
    vendor_dir.mkdir(parents=True, exist_ok=True)
    js_path = vendor_dir / "leaflet.min.js"
    css_path = vendor_dir / "leaflet.min.css"

    if not js_path.exists():
        print(f"  Downloading Leaflet {_LEAFLET_VERSION} JS …", flush=True)
        with urlopen(f"{_LEAFLET_BASE_URL}/leaflet.js", timeout=30) as resp:
            js_path.write_bytes(resp.read())

    if not css_path.exists():
        print(f"  Downloading Leaflet {_LEAFLET_VERSION} CSS …", flush=True)
        with urlopen(f"{_LEAFLET_BASE_URL}/leaflet.css", timeout=30) as resp:
            css_path.write_bytes(resp.read())

    js = js_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    # Replace marker image references with an empty pixel — we only draw polygons.
    css = re.sub(r"url\(images/[^)]+\)", f"url({_EMPTY_GIF_URI})", css)
    return js, css


def _enrich_features(features: list, grower_name: str, farm_name: str) -> None:
    for feat in features:
        props = feat.setdefault("properties", {})
        props.setdefault("grower_name", grower_name)
        props.setdefault("farm_name", farm_name)


def _lonlat_pairs(geometry: dict) -> list[list[float]]:
    geo_type = geometry.get("type", "")
    raw = geometry.get("coordinates", [])
    pairs: list[list[float]] = []
    if geo_type == "Polygon":
        for ring in raw:
            pairs.extend(ring)
    elif geo_type == "MultiPolygon":
        for poly in raw:
            for ring in poly:
                pairs.extend(ring)
    return pairs


def _centroid_latlon(feature: dict) -> tuple[float, float]:
    pts = _lonlat_pairs(feature.get("geometry", {}))
    if not pts:
        return 0.0, 0.0
    avg_lat = sum(p[1] for p in pts) / len(pts)
    avg_lon = sum(p[0] for p in pts) / len(pts)
    return avg_lat, avg_lon


def _build_field_list_html(features: list) -> str:
    rows: list[str] = []
    for i, feat in enumerate(features):
        p = feat.get("properties", {})
        lat, lon = _centroid_latlon(feat)
        field_id = p.get("field_id", f"field-{i}")
        farm_name = p.get("farm_name", "")
        county = p.get("county_name", "")
        area = p.get("area_acres") or 0
        area_str = f"{float(area):.1f}"
        rows.append(
            f'    <div class="field-row" onclick="flyToField({lat:.6f},{lon:.6f})">\n'
            f'      <span class="field-id">{field_id}</span>\n'
            f'      <span class="field-farm">{farm_name}</span>\n'
            f'      <span class="field-detail">{county} Co. &bull; {area_str} ac</span>\n'
            f"    </div>"
        )
    return "\n".join(rows)


def _generate_html(
    geojson: dict,
    grower_name: str,
    farm_count: int,
    leaflet_js: str,
    leaflet_css: str,
) -> str:
    features = geojson["features"]
    field_count = len(features)

    return (
        _HTML_TEMPLATE
        .replace("[[GROWER_NAME]]", grower_name)
        .replace("[[FIELD_COUNT]]", str(field_count))
        .replace("[[FIELD_PLURAL]]", "" if field_count == 1 else "s")
        .replace("[[FARM_COUNT]]", str(farm_count))
        .replace("[[FARM_PLURAL]]", "" if farm_count == 1 else "s")
        .replace("[[FIELD_LIST_HTML]]", _build_field_list_html(features))
        .replace("[[LEAFLET_CSS]]", leaflet_css)
        .replace("[[LEAFLET_JS]]", leaflet_js)
        .replace("[[GEOJSON]]", json.dumps(geojson, separators=(",", ":")))
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a self-contained Leaflet web map for a grower's fields."
    )
    parser.add_argument("--grower-slug", required=True, help="Grower slug, e.g. illinois-grower")
    parser.add_argument(
        "--data-root",
        default=os.environ.get("DATA_PIPELINE_DATA_ROOT"),
        help="Data pipeline root directory (default: DATA_PIPELINE_DATA_ROOT env var)",
    )
    args = parser.parse_args()

    if not args.data_root:
        sys.exit(
            "ERROR: DATA_PIPELINE_DATA_ROOT is not set. "
            "Pass --data-root or export the variable."
        )

    pipeline_root = Path(args.data_root) / "data-pipeline"
    grower_dir = pipeline_root / "growers" / args.grower_slug

    if not grower_dir.is_dir():
        sys.exit(f"ERROR: Grower directory not found: {grower_dir}")

    grower_meta = _read_json(grower_dir / "grower.json")
    grower_name = grower_meta.get("display_name", args.grower_slug)

    print(f"Generating web map for: {grower_name} ({args.grower_slug})")

    all_features: list[dict] = []
    farm_count = 0
    farms_dir = grower_dir / "farms"

    for farm_dir in sorted(farms_dir.iterdir()):
        if not farm_dir.is_dir():
            continue
        farm_json_path = farm_dir / "farm.json"
        boundaries_path = farm_dir / "boundary" / "field_boundaries.geojson"
        if not farm_json_path.exists() or not boundaries_path.exists():
            continue

        farm_meta = _read_json(farm_json_path)
        farm_name = farm_meta.get("display_name", farm_dir.name)
        farm_count += 1

        fc = _read_json(boundaries_path)
        features = fc.get("features", [])
        _enrich_features(features, grower_name, farm_name)
        all_features.extend(features)
        print(f"  Farm: {farm_name} — {len(features)} field(s)")

    if not all_features:
        sys.exit(f"ERROR: No field boundary features found under {farms_dir}")

    combined: dict = {"type": "FeatureCollection", "features": all_features}

    vendor_dir = pipeline_root / "shared" / "vendor" / "leaflet" / _LEAFLET_VERSION
    leaflet_js, leaflet_css = _fetch_leaflet(vendor_dir)

    html = _generate_html(combined, grower_name, farm_count, leaflet_js, leaflet_css)

    out_dir = grower_dir / "derived" / "maps"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "grower_web_map.html"
    out_path.write_text(html, encoding="utf-8")

    size_kb = out_path.stat().st_size // 1024
    print(f"✓ Written: {out_path} ({size_kb} KB)")


if __name__ == "__main__":
    main()
