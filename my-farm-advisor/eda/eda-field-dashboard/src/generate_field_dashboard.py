#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask

matplotlib.use("Agg")

YEAR_PALETTE = ["#0f766e", "#2563eb", "#ea580c", "#7c3aed", "#ca8a04"]
HEAVY_RAIN_MM = 20
HOT_DAY_C = 35
HEAT_WAVE_DAYS = 3
NDVI_CHANGE = 0.15
GDD_BASE = 10
GROWING_DOY = (80, 300)
PROTOTYPE_YEAR = 2022


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a multi-year field dashboard with NDVI, weather, and CDL crops."
    )
    parser.add_argument(
        "--data-root",
        default=os.environ.get("DATA_PIPELINE_DATA_ROOT", ""),
    )
    parser.add_argument("--grower-slug", default="nebraska-grower")
    parser.add_argument("--farm-slug", default="nebraska-farm")
    parser.add_argument("--field-id", default="osm-796351098")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def resolve_paths(args: argparse.Namespace) -> dict[str, Path]:
    data_root = Path(args.data_root)
    if not data_root.exists():
        print(f"Error: DATA_PIPELINE_DATA_ROOT not found: {data_root}", file=sys.stderr)
        sys.exit(1)
    runtime = data_root / "data-pipeline"
    farm_dir = runtime / "growers" / args.grower_slug / "farms" / args.farm_slug
    field_dir = farm_dir / "fields" / args.field_id
    return {
        "runtime": runtime,
        "farm_dir": farm_dir,
        "field_dir": field_dir,
        "boundary": field_dir / "boundary" / "field_boundary.geojson",
        "weather": field_dir / "weather" / "daily_weather.csv",
        "crop_join": field_dir / "derived" / "tables" / "ndvi_year_crop_join.csv",
        "satellite_sentinel": field_dir / "satellite" / "sentinel",
        "satellite_landsat": field_dir / "satellite" / "landsat",
    }


def load_manifest(manifest_path: Path) -> list[dict]:
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text())
        scenes = []
        for year_entry in data.get("years", []):
            year = year_entry.get("year")
            for scene in year_entry.get("scenes", []):
                ndvi_tif = scene.get("ndvi_tif")
                if ndvi_tif:
                    scenes.append(
                        {
                            "year": int(year) if year else None,
                            "date": scene.get("scene_date", ""),
                            "ndvi_path": ndvi_tif,
                            "cloud_cover": scene.get("cloud_cover", 999.0),
                            "sensor": manifest_path.parent.name,
                        }
                    )
        return scenes
    except (json.JSONDecodeError, KeyError):
        return []


def extract_mean_ndvi(ndvi_path: Path, boundary_geometry) -> float | None:
    if not ndvi_path.exists():
        return None
    try:
        with rasterio.open(ndvi_path) as src:
            boundary_proj = boundary_geometry.to_crs(src.crs)
            clipped, _ = mask(src, boundary_proj.geometry, crop=True, filled=False)
        array = np.ma.filled(clipped[0], np.nan).astype(float)
        valid = array[np.isfinite(array)]
        return float(np.nanmean(valid)) if valid.size > 0 else None
    except Exception:
        return None


def load_crop_join(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        if "year" in df.columns:
            df["year"] = df["year"].astype(int)
        return df
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def load_weather(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, parse_dates=["date"])
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def collect_ndvi_scenes(paths: dict[str, Path], runtime: Path) -> list[dict]:
    all_scenes = []
    for key in ("satellite_sentinel", "satellite_landsat"):
        scenes = load_manifest(paths[key] / "manifest.json")
        for scene in scenes:
            scene["ndvi_fullpath"] = runtime / scene["ndvi_path"]
        all_scenes.extend(scenes)
    all_scenes.sort(key=lambda s: (s["year"] or 0, s["date"]))
    return all_scenes


def check_data_coverage(
    weather_df: pd.DataFrame,
    ndvi_df: pd.DataFrame,
    sentinel_manifest: Path,
    landsat_manifest: Path,
) -> dict:
    report: dict[int, dict] = {}
    growing_start, growing_end = GROWING_DOY

    weather_df = weather_df.copy()
    weather_df["year"] = weather_df["date"].dt.year
    weather_df["doy"] = weather_df["date"].dt.dayofyear

    for year in sorted(weather_df["year"].unique()):
        info: dict = {"weather_gaps": [], "ndvi_months": defaultdict(int), "missing_growing_months": []}
        sub = weather_df[weather_df["year"] == year]
        expected = 366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365
        if len(sub) < expected:
            full = pd.date_range(f"{year}-01-01", f"{year}-12-31")
            missing = full.difference(sub["date"])
            info["weather_gaps"] = [str(d.date()) for d in missing[:10]]
        info["weather_days"] = len(sub)
        report[year] = info

    for path, label in [(sentinel_manifest, "sentinel"), (landsat_manifest, "landsat")]:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            for y in data.get("years", []):
                yr = y.get("year")
                if yr is None:
                    continue
                info = report.setdefault(int(yr), {"weather_gaps": [], "ndvi_months": defaultdict(int), "missing_growing_months": []})
                for s in y.get("scenes", []):
                    sd = s.get("scene_date", "")
                    if sd:
                        m = int(sd.split("-")[1])
                        info["ndvi_months"][m] += 1
        except (json.JSONDecodeError, KeyError):
            continue

    for year, info in report.items():
        ndvi_months = info.get("ndvi_months", {})
        missing = sorted(
            m for m in range(growing_start // 30 + 1, growing_end // 30 + 1)
            if m not in ndvi_months or ndvi_months[m] == 0
        )
        info["missing_growing_months"] = missing

    return report


def detect_ndvi_events(
    ndvi_df: pd.DataFrame, crop_lookup: dict[int, str]
) -> list[dict]:
    events = []
    if ndvi_df.empty:
        return events
    for year, group in ndvi_df.groupby("year"):
        group = group.sort_values("doy")
        vals = group["mean_ndvi"].values
        dates = group["date"].values
        doys = group["doy"].values
        if len(vals) < 2:
            continue
        peak_idx = int(np.argmax(vals))
        events.append(
            {
                "type": "ndvi_peak",
                "year": int(year),
                "doy": int(doys[peak_idx]),
                "date": str(pd.Timestamp(dates[peak_idx]).date()),
                "value": float(vals[peak_idx]),
                "label": f"Peak {vals[peak_idx]:.2f}",
            }
        )
        for i in range(1, len(vals)):
            change = vals[i] - vals[i - 1]
            if change > NDVI_CHANGE:
                events.append(
                    {
                        "type": "rapid_increase",
                        "year": int(year),
                        "doy": int(doys[i]),
                        "date": str(pd.Timestamp(dates[i]).date()),
                        "from_val": float(vals[i - 1]),
                        "to_val": float(vals[i]),
                        "change": float(change),
                        "label": f"+{change:.2f}",
                    }
                )
            elif change < -NDVI_CHANGE:
                events.append(
                    {
                        "type": "rapid_decrease",
                        "year": int(year),
                        "doy": int(doys[i]),
                        "date": str(pd.Timestamp(dates[i]).date()),
                        "from_val": float(vals[i]),
                        "to_val": float(vals[i - 1]),
                        "change": float(abs(change)),
                        "label": f"\u2212{abs(change):.2f}",
                    }
                )
        season_onset = None
        for i in range(len(vals)):
            if vals[i] > 0.3:
                season_onset = int(doys[i])
                break
        if season_onset is not None:
            events.append(
                {
                    "type": "season_onset",
                    "year": int(year),
                    "doy": season_onset,
                    "date": "",
                    "value": 0.3,
                    "label": "Onset",
                }
            )
    return events


def detect_frost_events(weather_df: pd.DataFrame, year: int) -> list[dict]:
    events = []
    sub = weather_df[weather_df["date"].dt.year == year].sort_values("date")
    if sub.empty:
        return events
    growing = sub[(sub["date"].dt.dayofyear >= GROWING_DOY[0]) & (sub["date"].dt.dayofyear <= GROWING_DOY[1])]
    frost = growing[growing["T2M_MIN"] < 0]
    if frost.empty:
        return events
    first = frost.iloc[0]
    last = frost.iloc[-1]
    events.append({
        "type": "frost",
        "year": year,
        "first_date": str(first["date"].date()),
        "last_date": str(last["date"].date()),
        "first_doy": int(first["date"].dayofyear),
        "last_doy": int(last["date"].dayofyear),
        "count": len(frost),
        "min_temp": float(growing["T2M_MIN"].min()),
        "label": f"{len(frost)} frost days",
    })
    return events


def detect_weather_events(weather_df: pd.DataFrame) -> list[dict]:
    events = []
    if weather_df.empty:
        return events
    weather_df = weather_df.copy()
    weather_df["year"] = weather_df["date"].dt.year
    for year, group in weather_df.groupby("year"):
        group = group.sort_values("date").reset_index(drop=True)
        heavy = group[group["PRECTOTCORR"] > HEAVY_RAIN_MM]
        for _, row in heavy.iterrows():
            events.append(
                {
                    "type": "heavy_rain",
                    "year": int(year),
                    "date": str(row["date"].date()),
                    "doy": int(row["date"].dayofyear),
                    "value": float(row["PRECTOTCORR"]),
                    "label": f"{row['PRECTOTCORR']:.0f}mm",
                }
            )
        hot = (group["T2M_MAX"] > HOT_DAY_C).astype(int)
        streak_id = (hot != hot.shift()).cumsum()
        streaks = (
            group[hot == 1]
            .groupby(streak_id)
            .filter(lambda x: len(x) >= HEAT_WAVE_DAYS)
        )
        if not streaks.empty:
            for _, sg in streaks.groupby(streak_id):
                start = sg["date"].iloc[0]
                end = sg["date"].iloc[-1]
                peak = float(sg["T2M_MAX"].max())
                events.append(
                    {
                        "type": "heat_wave",
                        "year": int(year),
                        "start_date": str(start.date()),
                        "end_date": str(end.date()),
                        "start_doy": int(start.dayofyear),
                        "end_doy": int(end.dayofyear),
                        "duration": len(sg),
                        "peak_temp": peak,
                        "label": f"{len(sg)}d {peak:.0f}\u00b0C",
                    }
                )
        for ev in detect_frost_events(weather_df, int(year)):
            events.append(ev)
    return events


def calculate_gdd(weather_df: pd.DataFrame) -> pd.DataFrame:
    df = weather_df.copy()
    df["year"] = df["date"].dt.year
    df["doy"] = df["date"].dt.dayofyear
    tavg = (df["T2M_MAX"] + df["T2M_MIN"]) / 2
    df["gdd"] = np.clip(tavg - GDD_BASE, 0, None)
    df["cum_gdd"] = df.groupby("year")["gdd"].cumsum()
    df["cum_precip"] = df.groupby("year")["PRECTOTCORR"].cumsum()
    return df


def collect_ndvi_data(boundary, paths, runtime) -> pd.DataFrame:
    scenes = collect_ndvi_scenes(paths, runtime)
    print(f"  NDVI scenes found: {len(scenes)}")
    records = []
    for scene in scenes:
        mean_ndvi = extract_mean_ndvi(Path(scene["ndvi_fullpath"]), boundary)
        if mean_ndvi is not None:
            records.append(
                {
                    "date": pd.Timestamp(scene["date"]),
                    "year": scene["year"],
                    "doy": pd.Timestamp(scene["date"]).dayofyear,
                    "mean_ndvi": mean_ndvi,
                    "sensor": scene["sensor"],
                }
            )
    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    print(f"  NDVI measurements extracted: {len(df)}")
    return df


def plot_ndvi_panel(
    ax, ndvi_df, crop_lookup, ndvi_events, growing_doy
):
    ax.set_facecolor("#ffffff")
    ax.grid(True, alpha=0.2)
    ax.set_ylabel("Mean NDVI", fontsize=11)
    ax.set_title("NDVI Time Series", fontsize=13, fontweight="bold", loc="left")
    ax.set_xlim(growing_doy[0] - 20, growing_doy[1] + 20)
    ax.set_ylim(-0.15, 1.0)
    ax.axhline(y=0, color="#cbd5e1", linewidth=0.5)
    ax.axvspan(
        growing_doy[0], growing_doy[1], color="#bbf7d0", alpha=0.06, zorder=0
    )

    year_groups = ndvi_df.groupby("year") if not ndvi_df.empty else {}
    for idx, (year, group) in enumerate(year_groups):
        year_int = int(year)
        group = group.sort_values("doy")
        if group.empty:
            continue
        color = YEAR_PALETTE[idx % len(YEAR_PALETTE)]
        crop = crop_lookup.get(year_int, "")
        label = f"{year_int}" + (f" ({crop})" if crop else "")
        ax.plot(
            group["doy"],
            group["mean_ndvi"],
            linewidth=2.0,
            marker="o",
            markersize=4.5,
            color=color,
            label=label,
            zorder=3,
        )

    for ev in ndvi_events:
        if ev["type"] == "ndvi_peak":
            ev_year = ev["year"]
            idx = list(year_groups.groups.keys()).index(ev_year) if ev_year in year_groups.groups else -1
            if idx >= 0:
                c = YEAR_PALETTE[idx % len(YEAR_PALETTE)]
                ax.annotate(
                    ev["label"],
                    xy=(ev["doy"], ev["value"]),
                    xytext=(8, 10),
                    textcoords="offset points",
                    fontsize=7,
                    fontweight="bold",
                    color=c,
                    arrowprops=dict(
                        arrowstyle="->", color=c, lw=0.8
                    ),
                )
        elif ev["type"] in ("rapid_increase", "rapid_decrease"):
            ev_year = ev["year"]
            idx = list(year_groups.groups.keys()).index(ev_year) if ev_year in year_groups.groups else -1
            if idx >= 0:
                c = "#16a34a" if ev["type"] == "rapid_increase" else "#dc2626"
                ax.annotate(
                    ev["label"],
                    xy=(ev["doy"], ev.get("to_val", 0)),
                    xytext=(0, -14 if ev["type"] == "rapid_decrease" else 14),
                    textcoords="offset points",
                    fontsize=6.5,
                    fontweight="bold",
                    color=c,
                    ha="center",
                )

    crops = sorted(set(crop_lookup.values()))
    rotation_text = f"{' \u2192 '.join(crops)} rotation" if crops else ""
    if rotation_text:
        ax.text(0.98, 0.02, rotation_text, transform=ax.transAxes,
                fontsize=6.5, color="#475569", ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8fafc", edgecolor="#cbd5e1", alpha=0.85))

    ax.legend(
        title="Year (CDL Crop)",
        fontsize=8,
        title_fontsize=8.5,
        loc="upper left",
        ncol=3,
    )


def plot_temperature_panel(ax, weather_df, weather_events, growing_doy):
    ax.set_facecolor("#ffffff")
    ax.grid(True, alpha=0.2)
    ax.set_ylabel("Temperature (\u00b0C)", fontsize=11)
    ax.set_title("Daily Temperature & Extremes", fontsize=13, fontweight="bold", loc="left")
    ax.axhline(y=0, color="#94a3b8", linewidth=0.5, linestyle="--", label="0\u00b0C frost line")
    ax.axvspan(
        growing_doy[0], growing_doy[1], color="#bbf7d0", alpha=0.06, zorder=0
    )

    weather_df = weather_df.copy()
    weather_df["year_int"] = weather_df["date"].dt.year
    weather_df["doy"] = weather_df["date"].dt.dayofyear

    for idx, year in enumerate(sorted(weather_df["year_int"].unique())):
        subset = weather_df[weather_df["year_int"] == year].sort_values("doy")
        if subset.empty:
            continue
        color = YEAR_PALETTE[idx % len(YEAR_PALETTE)]
        ax.plot(subset["doy"], subset["T2M_MAX"], linewidth=0.8, color=color, alpha=0.35)
        ax.plot(subset["doy"], subset["T2M_MIN"], linewidth=0.8, color=color, alpha=0.35)
        ax.fill_between(
            subset["doy"], subset["T2M_MIN"], subset["T2M_MAX"],
            color=color, alpha=0.06,
        )

    if "T2M" in weather_df.columns:
        avg_temp = weather_df.groupby("doy")["T2M"].mean()
        ax.plot(avg_temp.index, avg_temp.values, linewidth=1.8, color="#1e293b", alpha=0.6, label="5-yr mean")

    hot_doys = set()
    for ev in weather_events:
        if ev["type"] == "heat_wave":
            ax.axvspan(
                ev["start_doy"], ev["end_doy"],
                color="#ef4444", alpha=0.1, zorder=2,
            )
            mid_doy = (ev["start_doy"] + ev["end_doy"]) // 2
            ax.annotate(
                ev["label"],
                xy=(mid_doy, ax.get_ylim()[1]),
                xytext=(0, -6),
                textcoords="offset points",
                fontsize=6,
                color="#dc2626",
                ha="center",
                va="top",
            )
            for d in range(ev["start_doy"], ev["end_doy"] + 1):
                hot_doys.add(d)
        elif ev["type"] == "frost":
            ax.annotate(
                f"{ev['count']} frost days",
                xy=(ev["first_doy"], 0),
                xytext=(4, -14),
                textcoords="offset points",
                fontsize=5.5, color="#3b82f6", fontweight="bold",
            )
            ax.annotate(
                f"Last {ev['last_date']}",
                xy=(ev["last_doy"], 0),
                xytext=(4, 6),
                textcoords="offset points",
                fontsize=5, color="#3b82f6",
            )

    hot_mask = weather_df["T2M_MAX"] > HOT_DAY_C
    hot_subset = weather_df[hot_mask & ~weather_df["doy"].isin(hot_doys)]
    if not hot_subset.empty:
        ax.scatter(
            hot_subset["doy"],
            hot_subset["T2M_MAX"],
            s=6,
            color="#ef4444",
            alpha=0.4,
            zorder=3,
            label=f"Hot days >{HOT_DAY_C}\u00b0C",
        )

    hottest = max((e for e in weather_events if e.get("peak_temp")), key=lambda e: e["peak_temp"], default=None)
    parts = []
    if hottest:
        parts.append(f"Peak {hottest['peak_temp']:.0f}\u00b0C {hottest['start_date']}")
    hot_count = len(weather_df[weather_df["T2M_MAX"] > HOT_DAY_C].drop_duplicates("doy")) if not weather_df.empty else 0
    if hot_count:
        parts.append(f"{hot_count} hot days >{HOT_DAY_C}\u00b0C")
    frost_events = [e for e in weather_events if e["type"] == "frost"]
    if frost_events:
        total_frost = sum(e["count"] for e in frost_events)
        parts.append(f"{total_frost} frost days in growing season")
    if parts:
        ax.text(0.98, 0.98, " \u2022 ".join(parts), transform=ax.transAxes,
                fontsize=6.5, color="#475569", ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8fafc", edgecolor="#cbd5e1", alpha=0.85))

    ax.legend(fontsize=7, loc="upper left")


def plot_precip_panel(ax, weather_df, weather_events, growing_doy):
    ax.set_facecolor("#ffffff")
    ax.grid(True, alpha=0.2)
    ax.set_ylabel("Precipitation (mm)", fontsize=11)
    ax.set_xlabel("Day of Year", fontsize=11)
    ax.set_title("Precipitation", fontsize=13, fontweight="bold", loc="left")
    ax.axvspan(
        growing_doy[0], growing_doy[1], color="#bbf7d0", alpha=0.06, zorder=0
    )

    weather_df = weather_df.copy()
    weather_df["year_int"] = weather_df["date"].dt.year
    weather_df["doy"] = weather_df["date"].dt.dayofyear

    proto = weather_df[weather_df["year_int"] == PROTOTYPE_YEAR].copy()
    if not proto.empty:
        ax.bar(
            proto["doy"], proto["PRECTOTCORR"],
            width=0.8, color="#60a5fa", alpha=0.5,
            label=f"Daily {PROTOTYPE_YEAR}",
        )

    rolling_precip = (
        weather_df.groupby("doy")["PRECTOTCORR"]
        .mean()
        .rolling(window=7, center=True)
        .mean()
    )
    ax.plot(
        rolling_precip.index,
        rolling_precip.values,
        linewidth=1.5,
        color="#1e293b",
        alpha=0.5,
        label="7-day avg (all years)",
    )

    cum_precip = weather_df.groupby("doy")["PRECTOTCORR"].mean().cumsum()
    ax2 = ax.twinx()
    ax2.plot(
        cum_precip.index,
        cum_precip.values,
        linewidth=2.0,
        color="#1e40af",
        alpha=0.7,
        label="Cumulative (mean)",
    )
    ax2.set_ylabel("Cumulative Precip (mm)", fontsize=10, color="#1e40af")
    ax2.tick_params(axis="y", labelcolor="#1e40af", labelsize=8)
    total = cum_precip.iloc[-1] if not cum_precip.empty else 0
    ax2.text(
        0.98, 0.95, f"{total:.0f} mm avg annual",
        transform=ax2.transAxes, fontsize=8, color="#1e40af",
        ha="right", va="top",
    )

    for ev in weather_events:
        if ev["type"] == "heavy_rain":
            ax.annotate(
                ev["label"],
                xy=(ev["doy"], ev["value"]),
                xytext=(6, 8),
                textcoords="offset points",
                fontsize=6.5,
                fontweight="bold",
                color="#2563eb",
                arrowprops=dict(arrowstyle="->", color="#2563eb", lw=0.7),
            )
            ax.scatter(
                [ev["doy"]], [ev["value"]],
                s=30, color="#2563eb", zorder=4, marker="D",
            )

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(
        lines1 + lines2, labels1 + labels2,
        fontsize=7.5, loc="upper left",
    )


def plot_gdd_panel(ax, weather_df, weather_events, growing_doy):
    ax.set_facecolor("#ffffff")
    ax.grid(True, alpha=0.2)
    ax.set_ylabel("Cumulative GDD (base 10\u00b0C)", fontsize=11)
    ax.set_xlabel("Day of Year", fontsize=11)
    ax.set_title("Cumulative Growing Degree Days", fontsize=13, fontweight="bold", loc="left")
    ax.axvspan(
        growing_doy[0], growing_doy[1], color="#bbf7d0", alpha=0.06, zorder=0
    )

    weather_df = weather_df.copy()
    weather_df["doy"] = weather_df["date"].dt.dayofyear
    weather_df["year_int"] = weather_df["date"].dt.year
    tavg = (weather_df["T2M_MAX"] + weather_df["T2M_MIN"]) / 2
    weather_df["gdd"] = np.clip(tavg - GDD_BASE, 0, None)

    gdd_summary_parts = []
    for idx, year in enumerate(sorted(weather_df["year_int"].unique())):
        sub = weather_df[weather_df["year_int"] == year].sort_values("doy")
        if sub.empty:
            continue
        sub["cum_gdd"] = sub["gdd"].cumsum()
        color = YEAR_PALETTE[idx % len(YEAR_PALETTE)]
        ax.plot(sub["doy"], sub["cum_gdd"], linewidth=1.8, color=color, alpha=0.8, label=str(year))
        final_gdd = sub["cum_gdd"].iloc[-1]
        ax.annotate(
            f"{final_gdd:.0f}",
            xy=(sub["doy"].iloc[-1], final_gdd),
            xytext=(6, 0),
            textcoords="offset points",
            fontsize=6.5, fontweight="bold", color=color,
        )
        gdd_summary_parts.append((int(year), float(final_gdd)))

    if gdd_summary_parts:
        warmest = max(gdd_summary_parts, key=lambda x: x[1])
        coolest = min(gdd_summary_parts, key=lambda x: x[1])
        ax.text(0.98, 0.02,
                f"Warmest: {warmest[0]} ({warmest[1]:.0f} GDD) | Coolest: {coolest[0]} ({coolest[1]:.0f} GDD)",
                transform=ax.transAxes, fontsize=6.5, color="#475569",
                ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8fafc", edgecolor="#cbd5e1", alpha=0.85))
    ax.text(0.02, 0.98,
            "Growing degree days measure\nheat accumulation for crop development",
            transform=ax.transAxes, fontsize=6, color="#94a3b8", ha="left", va="top")

    ax.legend(fontsize=7.5, loc="upper left", title="Year", title_fontsize=8)





def build_dashboard(paths: dict[str, Path], args: argparse.Namespace) -> Path:
    print("=" * 60)
    print("Field Dashboard Generator")
    print("=" * 60)
    field_id = args.field_id
    field_dir = paths["field_dir"]
    print(f"Field: {field_id}")
    print(f"Data root: {args.data_root}")

    boundary = gpd.read_file(paths["boundary"])
    crop_join = load_crop_join(paths["crop_join"])
    weather = load_weather(paths["weather"])
    print(f"  Boundary: loaded ({len(boundary)} feature(s))")
    print(f"  Crop join: {len(crop_join)} rows")
    print(f"  Weather: {len(weather)} daily records")

    ndvi_df = collect_ndvi_data(boundary, paths, paths["runtime"])

    crop_lookup = {}
    if not crop_join.empty and {"year", "crop_name"}.issubset(crop_join.columns):
        crop_lookup = {
            int(r["year"]): str(r["crop_name"])
            for _, r in crop_join.iterrows()
        }

    print(f"  CDL crops: {crop_lookup}")

    coverage_report = check_data_coverage(
        weather, ndvi_df,
        paths["satellite_sentinel"] / "manifest.json",
        paths["satellite_landsat"] / "manifest.json",
    )
    for yr, info in sorted(coverage_report.items()):
        gaps = info.get("weather_gaps", [])
        missing_months = info.get("missing_growing_months", [])
        ndvi_months = dict(info.get("ndvi_months", {}))
        gap_str = f", gaps={gaps}" if gaps else ""
        miss_str = f", missing months: {missing_months}" if missing_months else ""
        print(f"  {yr}: weather={info.get('weather_days', '?')}d{gap_str} | NDVI months: {ndvi_months}{miss_str}")

    ndvi_events = detect_ndvi_events(ndvi_df, crop_lookup)
    weather_events = detect_weather_events(weather)

    n_ndvi = len(ndvi_events)
    n_weather = len(weather_events)
    print(f"  NDVI events detected: {n_ndvi}")
    print(f"  Weather events detected: {n_weather}")

    gdd_df = calculate_gdd(weather)
    years_available = sorted(ndvi_df["year"].unique()) if not ndvi_df.empty else []

    print("\nBuilding dashboard figure...")
    fig = plt.figure(figsize=(14, 9.0))
    fig.patch.set_facecolor("#fafaf9")

    gs = fig.add_gridspec(4, 1, height_ratios=[1.5, 0.9, 1.0, 0.8], hspace=0.22)
    ax_ndvi = fig.add_subplot(gs[0])
    ax_precip = fig.add_subplot(gs[1])
    ax_temp = fig.add_subplot(gs[2])
    ax_gdd = fig.add_subplot(gs[3])

    fig.text(
        0.5, 0.968,
        f"Field Dashboard \u2014 {field_id}",
        fontsize=15, fontweight="bold", color="#0f172a", ha="center",
    )
    fig.text(
        0.5, 0.948,
        (
            f"{args.grower_slug} / {args.farm_slug}  \u00b7  "
            f"Merrick County, Nebraska  \u00b7  "
            f"{', '.join(str(y) for y in years_available)}  \u00b7  "
            f"CDL crop 2022: {crop_lookup.get(2022, 'N/A')}"
        ),
        fontsize=9.5, color="#64748b", ha="center",
    )

    plot_ndvi_panel(ax_ndvi, ndvi_df, crop_lookup, ndvi_events, GROWING_DOY)
    plot_precip_panel(ax_precip, weather, weather_events, GROWING_DOY)
    plot_temperature_panel(ax_temp, weather, weather_events, GROWING_DOY)
    plot_gdd_panel(ax_gdd, weather, weather_events, GROWING_DOY)

    xlim = (GROWING_DOY[0] - 20, GROWING_DOY[1] + 20)
    for ax in [ax_ndvi, ax_precip, ax_temp, ax_gdd]:
        ax.tick_params(axis="both", labelsize=8.5)
        ax.set_xlim(xlim)

    output_path = Path(
        args.output
        or str(field_dir / "derived" / "reports" / "field_dashboard.png")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"\n\u2713 Dashboard saved: {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    if not args.data_root:
        print(
            "Error: DATA_PIPELINE_DATA_ROOT not set. Use --data-root or set the environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
    build_dashboard(resolve_paths(args), args)


if __name__ == "__main__":
    main()
