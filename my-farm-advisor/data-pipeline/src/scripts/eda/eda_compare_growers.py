#!/usr/bin/env python3
# pyright: reportCallIssue=false
"""
eda_compare_growers.py — Cross-grower comparison for Assignment 2.

Loads boundary, CDL, and weather data from multiple growers and generates
comparison plots across three categories:
  - Field boundaries (size, distribution, polygon map, crop correlation)
  - CDL/cropland (crop composition, field-year tile, diversity, rotation)
  - Weather (seasonal climatology, growing season with per-field overlay,
             weather-crop correlation with Pearson r)

Usage:
    python scripts/eda/eda_compare_growers.py \\
        --grower-slugs illinois-grower iowa-grower nebraska-grower \\
        --output-dir growers/derived/reports

Output:
    11 PNG plots and 2 CSV tables under the output directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.paths import (  # noqa: E402
    DATA_ROOT,
    GROWERS_ROOT,
    farm_boundary_path,
    farm_cdl_full_composition_path,
    farm_cdl_rotation_path,
    farm_weather_path,
    grower_dir,
)

sns.set_style("whitegrid")
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150})


# ── helpers ──────────────────────────────────────────────────────────

def _farm_slug_for_grower(grower_slug: str) -> str:
    parts = grower_slug.rsplit("-", 1)
    base = parts[0]
    return f"{base}-farm"


def _grower_label(grower_slug: str) -> str:
    return grower_slug.replace("-grower", "").replace("-", " ").title()


def _output_dir(output_base: Path) -> Path:
    path = output_base / "eda_compare_growers"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _grower_color(index: int) -> str:
    palette = sns.color_palette("Set2", 8)
    return palette[index]


# ── data loading ─────────────────────────────────────────────────────

def load_all_data(
    grower_slugs: list[str],
) -> tuple[dict[str, gpd.GeoDataFrame], dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, pd.DataFrame], Path]:
    boundaries: dict[str, gpd.GeoDataFrame] = {}
    cdl: dict[str, pd.DataFrame] = {}
    rotations: dict[str, pd.DataFrame] = {}
    weather: dict[str, pd.DataFrame] = {}

    for slug in grower_slugs:
        farm_slug = _farm_slug_for_grower(slug)
        label = _grower_label(slug)

        # Boundaries
        bpath = farm_boundary_path(slug, farm_slug)
        if not bpath.exists():
            print(f"  [WARN] No boundary found for {slug}")
            continue
        gdf = gpd.read_file(bpath)
        gdf["grower"] = label
        boundaries[slug] = gdf

        # CDL full composition
        cdl_path = farm_cdl_full_composition_path(slug, farm_slug)
        if cdl_path.exists():
            df = pd.read_csv(cdl_path)
            df["grower"] = label
            cdl[slug] = df
        else:
            print(f"  [WARN] No CDL composition for {slug}")

        # Crop rotation
        rot_path = farm_cdl_rotation_path(slug, farm_slug)
        if rot_path.exists():
            rotations[slug] = pd.read_csv(rot_path)
            rotations[slug]["grower"] = label

        # Weather
        wpath = farm_weather_path(slug, farm_slug)
        if wpath.exists():
            wdf = pd.read_csv(wpath, parse_dates=["date"])
            wdf["grower"] = label
            weather[slug] = wdf
        else:
            print(f"  [WARN] No weather table for {slug}")

    return boundaries, cdl, rotations, weather


# ── boundary plots ───────────────────────────────────────────────────

def plot_field_size_distribution(
    boundaries: dict[str, gpd.GeoDataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        gdf = boundaries.get(slug)
        if gdf is None:
            continue
        for _, row in gdf.iterrows():
            rows.append({"grower": _grower_label(slug), "area_acres": row["area_acres"]})
    if not rows:
        return ""
    df = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    for ax, (grower, group) in zip(axes, df.groupby("grower")):
        ax.hist(group["area_acres"], bins=8, color=_grower_color(list(df["grower"].unique()).index(grower)),
                edgecolor="white", alpha=0.8)
        ax.set_title(grower, fontsize=12, fontweight="bold")
        ax.set_xlabel("Area (acres)", fontsize=10)
        if ax == axes[0]:
            ax.set_ylabel("Field count", fontsize=10)
        mean_val = group["area_acres"].mean()
        ax.axvline(mean_val, color="red", linestyle="--", linewidth=1)
        ax.text(mean_val, ax.get_ylim()[1] * 0.9, f"μ={mean_val:.0f}", color="red",
                fontsize=8, ha="left")

    fig.suptitle("Field Size Distribution by Grower", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = out_dir / "boundary_field_size_distribution.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


def plot_field_size_boxplot(
    boundaries: dict[str, gpd.GeoDataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        gdf = boundaries.get(slug)
        if gdf is None:
            continue
        for _, row in gdf.iterrows():
            rows.append({"grower": _grower_label(slug), "area_acres": row["area_acres"]})
    if not rows:
        return ""
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(8, 5))
    order = [_grower_label(s) for s in slug_order if s in boundaries]
    bp = sns.boxplot(data=df, x="grower", y="area_acres", hue="grower", palette="Set2",
                      order=order, legend=False, ax=ax)
    sns.stripplot(data=df, x="grower", y="area_acres", color="0.3", size=5, alpha=0.6,
                  order=order, ax=ax)

    for i, grower in enumerate(order):
        group = df[df["grower"] == grower]["area_acres"]
        mean_val = group.mean()
        median_val = group.median()
        ax.text(i, ax.get_ylim()[1] * 0.95, f"μ={mean_val:.0f}\nM={median_val:.0f}",
                ha="center", fontsize=8, color="blue")

    ax.set_title("Field Size Comparison Across Growers", fontsize=14, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Field Area (acres)", fontsize=11)
    plt.tight_layout()
    path = out_dir / "boundary_field_size_boxplot.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


def plot_boundary_location_map(
    boundaries: dict[str, gpd.GeoDataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    fig, ax = plt.subplots(figsize=(10, 7))
    for i, slug in enumerate(slug_order):
        gdf = boundaries.get(slug)
        if gdf is None:
            continue
        label = _grower_label(slug)
        gdf.boundary.plot(ax=ax, color=_grower_color(i), linewidth=1.2, label=label)
        gdf.plot(ax=ax, color=_grower_color(i), alpha=0.25, edgecolor="none")

    for i, slug in enumerate(slug_order):
        gdf = boundaries.get(slug)
        if gdf is None:
            continue
        for _, row in gdf.iterrows():
            centroid = row.geometry.centroid
            area = row.get("area_acres", 0)
            ax.annotate(f"{area:.0f}ac", (centroid.x, centroid.y),
                        fontsize=6, ha="center", va="center", alpha=0.8,
                        bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.6, edgecolor="none"))

    ax.set_xlabel("Longitude", fontsize=11)
    ax.set_ylabel("Latitude", fontsize=11)
    ax.set_title("Field Boundary Polygons Colored by Grower", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, loc="upper right")
    ax.set_aspect("equal")
    plt.tight_layout()
    path = out_dir / "boundary_location_map.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


# ── CDL plots ────────────────────────────────────────────────────────

def plot_cdl_crop_composition(
    cdl: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        df = cdl.get(slug)
        if df is None:
            continue
        rows.append(df)
    if not rows:
        return ""
    combined = pd.concat(rows, ignore_index=True)

    top_crops = (
        combined.groupby(["grower", "crop_name"])["pct"]
        .mean()
        .reset_index()
        .sort_values("pct", ascending=False)
    )
    top_crop_names = top_crops.groupby("crop_name")["pct"].max().nlargest(4).index.tolist()
    top_crops = top_crops[top_crops["crop_name"].isin(top_crop_names)]

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=top_crops, x="grower", y="pct", hue="crop_name",
                palette="Set2", ax=ax)
    ax.set_title("Mean CDL Crop Composition by Grower (top 4 crops)", fontsize=13, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Mean field coverage (%)", fontsize=11)
    ax.legend(title="Crop", fontsize=9)
    plt.tight_layout()
    path = out_dir / "cdl_crop_composition.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


def plot_cdl_crop_diversity(
    rotations: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        rot = rotations.get(slug)
        if rot is None or "crop_diversity" not in rot.columns:
            continue
        for _, r in rot.iterrows():
            rows.append({"grower": _grower_label(slug), "crop_diversity": r["crop_diversity"]})
    if not rows:
        return ""
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(8, 5))
    order = [_grower_label(s) for s in slug_order if s in rotations and "crop_diversity" in rotations[s].columns]
    if not order:
        return ""
    sns.violinplot(data=df, x="grower", y="crop_diversity", hue="grower", palette="Set2",
                   order=order, inner="quartile", legend=False, ax=ax)
    sns.stripplot(data=df, x="grower", y="crop_diversity", color="0.3",
                  size=6, alpha=0.6, order=order, ax=ax)
    ax.set_title("Crop Diversity per Field (unique crops, 2021–2025)", fontsize=13, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Unique crop types", fontsize=11)
    plt.tight_layout()
    path = out_dir / "cdl_crop_diversity.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


def plot_cdl_rotation_comparison(
    rotations: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    slug_colors = []
    for slug in slug_order:
        rot = rotations.get(slug)
        if rot is None or "rotation_patterns" not in rot.columns:
            continue
        for _, r in rot.iterrows():
            patterns = str(r.get("rotation_patterns", "")).split(";")
            for pat in patterns:
                pat = pat.strip()
                if pat:
                    rows.append({"grower": _grower_label(slug), "pattern": pat})
        slug_colors.append(_grower_label(slug))
    if not rows:
        return ""
    df = pd.DataFrame(rows)
    pivot = df.groupby(["grower", "pattern"]).size().reset_index(name="field_count")
    pivot["fraction"] = pivot.groupby("grower")["field_count"].transform(lambda x: x / x.sum())

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=pivot, x="grower", y="fraction", hue="pattern",
                palette="Set2", ax=ax)
    ax.set_title("Crop Rotation Pattern Distribution by Grower", fontsize=13, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Fraction of fields", fontsize=11)
    ax.legend(title="Rotation", fontsize=8, title_fontsize=9)
    plt.tight_layout()
    path = out_dir / "cdl_rotation_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


def plot_cdl_field_crop_tile(
    cdl: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        df = cdl.get(slug)
        if df is None:
            continue
        top_per_field = (
            df.groupby(["field_id", "year"])[["pct", "crop_name"]]
            .apply(lambda x: x.sort_values("pct", ascending=False).iloc[0])
            .reset_index()
        )
        top_per_field["grower"] = _grower_label(slug)
        rows.append(top_per_field[["field_id", "year", "crop_name", "grower"]])

    if not rows:
        return ""
    combined = pd.concat(rows, ignore_index=True)

    colors = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494"]
    crop_codes = combined["crop_name"].unique()
    palette = {c: colors[i % len(colors)] for i, c in enumerate(sorted(crop_codes))}

    fig, axes = plt.subplots(1, len(slug_order), figsize=(14, 5), sharey=True)
    if len(slug_order) == 1:
        axes = [axes]

    for ax_idx, slug in enumerate(slug_order):
        label = _grower_label(slug)
        sub = combined[combined["grower"] == label].copy()
        if sub.empty:
            axes[ax_idx].set_title(f"{label}\n(no data)", fontsize=11)
            continue

        sub["field_short"] = sub["field_id"].str.replace("osm-", "")

        pivot = sub.pivot_table(index="field_short", columns="year",
                                 values="crop_name", aggfunc="first")
        years = sorted(pivot.columns)
        fields = list(pivot.index)

        for fi, field in enumerate(fields):
            for yi, year in enumerate(years):
                crop = pivot.loc[field, year]
                color = palette.get(crop, "#cccccc")
                axes[ax_idx].fill_between([yi - 0.45, yi + 0.45], fi - 0.45, fi + 0.45,
                                           color=color, edgecolor="white", linewidth=0.5)

        axes[ax_idx].set_yticks(range(len(fields)))
        axes[ax_idx].set_yticklabels(fields, fontsize=7)
        axes[ax_idx].set_xticks(range(len(years)))
        axes[ax_idx].set_xticklabels(years, fontsize=9)
        axes[ax_idx].set_title(label, fontsize=12, fontweight="bold")
        axes[ax_idx].set_xlabel("Year", fontsize=10)

    fig.suptitle("Dominant CDL Crop per Field per Year", fontsize=14, fontweight="bold")

    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=palette[c], edgecolor="white", label=c)
                       for c in sorted(palette.keys())]
    fig.legend(handles=legend_elements, title="Crop", fontsize=8,
               title_fontsize=9, loc="lower center", ncol=min(len(palette), 5),
               bbox_to_anchor=(0.5, -0.08))

    plt.tight_layout()
    path = out_dir / "cdl_field_crop_tile.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


def plot_boundary_crop_correlation(
    boundaries: dict[str, gpd.GeoDataFrame],
    cdl: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        gdf = boundaries.get(slug)
        cdf = cdl.get(slug)
        if gdf is None or cdf is None:
            continue
        label = _grower_label(slug)
        corn_pct = cdf[cdf["crop_code"] == 1].groupby("field_id")["pct"].mean().reset_index()
        corn_pct.columns = ["field_id", "corn_pct"]
        merged = gdf[["field_id", "area_acres"]].merge(corn_pct, on="field_id", how="inner")
        merged["grower"] = label
        rows.append(merged)

    if not rows:
        return ""
    combined = pd.concat(rows, ignore_index=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    from scipy import stats as scipy_stats
    for i, grower in enumerate(combined["grower"].unique()):
        g = combined[combined["grower"] == grower]
        color = _grower_color(i)
        ax.scatter(g["area_acres"], g["corn_pct"], c=[color], label=grower,
                   s=60, alpha=0.7, edgecolors="black", linewidth=0.5)
        if len(g) > 2:
            r, p = scipy_stats.pearsonr(g["area_acres"], g["corn_pct"])
            z = np.polyfit(g["area_acres"], g["corn_pct"], 1)
            p_fn = np.poly1d(z)
            x_line = np.linspace(g["area_acres"].min(), g["area_acres"].max(), 50)
            ax.plot(x_line, p_fn(x_line), color=color, linestyle="--", linewidth=1.5, alpha=0.7)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            ax.annotate(f"r={r:.2f}{sig}", xy=(0.05, 0.9 - i * 0.08), xycoords="axes fraction",
                        fontsize=9, color=color, fontweight="bold")

    ax.set_xlabel("Field Area (acres)", fontsize=11)
    ax.set_ylabel("Mean Corn Coverage (%)", fontsize=11)
    ax.set_title("Field Size vs Corn Percentage by Grower", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    plt.tight_layout()
    path = out_dir / "boundary_crop_correlation.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


# ── weather plots ────────────────────────────────────────────────────

def plot_seasonal_climatology(
    weather: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        wdf = weather.get(slug)
        if wdf is None:
            continue
        wdf = wdf.copy()
        wdf["month"] = wdf["date"].dt.month
        rows.append(wdf)
    if not rows:
        return ""
    combined = pd.concat(rows, ignore_index=True)

    monthly = (
        combined.groupby(["grower", "month"])[["T2M", "PRECTOTCORR"]]
        .agg(["mean", "std"])
        .reset_index()
    )
    monthly.columns = ["grower", "month", "t2m_mean", "t2m_std", "precip_mean", "precip_std"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    for i, grower in enumerate(monthly["grower"].unique()):
        g = monthly[monthly["grower"] == grower]
        color = _grower_color(i)
        ax1.plot(g["month"], g["t2m_mean"], "o-", color=color, label=grower, linewidth=2)
        ax1.fill_between(g["month"], g["t2m_mean"] - g["t2m_std"],
                          g["t2m_mean"] + g["t2m_std"], alpha=0.15, color=color)
        ax2.bar(g["month"] - 0.2 + i * 0.15, g["precip_mean"], width=0.15,
                color=color, label=grower, alpha=0.8)
    ax1.set_ylabel("Temperature (°C)", fontsize=11)
    ax1.set_title("Monthly Climatology (±1σ)", fontsize=13, fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.axhline(0, color="gray", linewidth=0.5)

    ax2.set_ylabel("Precipitation (mm)", fontsize=11)
    ax2.set_xlabel("Month", fontsize=11)
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax2.legend(fontsize=9)

    plt.tight_layout()
    path = out_dir / "weather_seasonal_climatology.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


def plot_growing_season(
    weather: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        wdf = weather.get(slug)
        if wdf is None:
            continue
        wdf = wdf.copy()
        wdf["month"] = wdf["date"].dt.month
        wdf["year"] = wdf["date"].dt.year
        growing = wdf[wdf["month"].between(4, 9)]
        rows.append(growing)
    if not rows:
        return ""
    combined = pd.concat(rows, ignore_index=True)

    gs = (
        combined.groupby(["grower", "year"])[["T2M", "PRECTOTCORR"]]
        .agg({"T2M": "mean", "PRECTOTCORR": "sum"})
        .reset_index()
    )
    gs.columns = ["grower", "year", "growing_season_t2m", "growing_season_precip"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    for i, grower_name in enumerate(gs["grower"].unique()):
        g = gs[gs["grower"] == grower_name]
        color = _grower_color(i)

        for slug in slug_order:
            if _grower_label(slug) != grower_name:
                continue
            wdf = weather.get(slug)
            if wdf is None:
                continue
            wdf = wdf.copy()
            wdf["month"] = wdf["date"].dt.month
            wdf["year"] = wdf["date"].dt.year
            growing = wdf[wdf["month"].between(4, 9)]
            if growing.empty:
                continue
            per_field = (
                growing.groupby(["field_id", "year"])[["T2M", "PRECTOTCORR"]]
                .agg({"T2M": "mean", "PRECTOTCORR": "sum"})
                .reset_index()
            )
            for field_id in per_field["field_id"].unique():
                fg = per_field[per_field["field_id"] == field_id]
                ax1.plot(fg["year"], fg["T2M"], color=color, linewidth=0.5, alpha=0.25)
                ax2.plot(fg["year"], fg["PRECTOTCORR"], color=color, linewidth=0.5, alpha=0.25,
                         linestyle="--")

        ax1.plot(g["year"], g["growing_season_t2m"], "o-", color=color,
                 label=grower_name, linewidth=2.5, markersize=7, zorder=5)
        ax2.plot(g["year"], g["growing_season_precip"], "s--", color=color,
                 label=grower_name, linewidth=2.5, markersize=7, zorder=5)

    ax1.set_ylabel("Mean T2M Apr–Sep (°C)", fontsize=11)
    ax1.set_title("Growing Season (Apr–Sep) Temperature (faint lines = per-field)", fontsize=13, fontweight="bold")
    ax1.legend(fontsize=9)

    ax2.set_ylabel("Total Precip Apr–Sep (mm)", fontsize=11)
    ax2.set_xlabel("Year", fontsize=11)
    ax2.set_title("Growing Season (Apr–Sep) Precipitation (faint lines = per-field)", fontsize=13, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.set_xticks(sorted(gs["year"].unique()))

    for ax in (ax1, ax2):
        ax.set_xlim(min(gs["year"]) - 0.3, max(gs["year"]) + 0.3)

    plt.tight_layout()
    path = out_dir / "weather_growing_season.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


def plot_weather_crop_correlation(
    weather: dict[str, pd.DataFrame],
    cdl: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    from scipy import stats as scipy_stats
    field_precip: list[dict] = []
    field_corn: list[dict] = []

    for slug in slug_order:
        wdf = weather.get(slug)
        cdf = cdl.get(slug)
        if wdf is None or cdf is None:
            continue
        label = _grower_label(slug)

        wdf = wdf.copy()
        wdf["year"] = wdf["date"].dt.year
        yearly_precip = wdf.groupby(["field_id", "year"])["PRECTOTCORR"].sum().reset_index()

        corn_pct = cdf[cdf["crop_code"] == 1].groupby(["field_id", "year"])["pct"].max().reset_index()
        corn_pct.columns = ["field_id", "year", "corn_pct"]

        merged = yearly_precip.merge(corn_pct, on=["field_id", "year"], how="inner")
        if merged.empty:
            continue
        merged["grower"] = label
        field_precip.append(merged)

        avg = merged.groupby("field_id").agg({"PRECTOTCORR": "mean", "corn_pct": "mean"}).reset_index()
        avg["grower"] = label
        field_corn.append(avg)

    if not field_corn and not field_precip:
        return ""

    avg_all = pd.concat(field_corn, ignore_index=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    for i, grower in enumerate(avg_all["grower"].unique()):
        g = avg_all[avg_all["grower"] == grower]
        color = _grower_color(i)
        ax.scatter(g["PRECTOTCORR"], g["corn_pct"], c=[color], label=grower,
                   s=60, alpha=0.7, edgecolors="black", linewidth=0.5)
        if len(g) > 2:
            r, p = scipy_stats.pearsonr(g["PRECTOTCORR"], g["corn_pct"])
            z = np.polyfit(g["PRECTOTCORR"], g["corn_pct"], 1)
            p_fn = np.poly1d(z)
            x_line = np.linspace(g["PRECTOTCORR"].min(), g["PRECTOTCORR"].max(), 50)
            ax.plot(x_line, p_fn(x_line), color=color, linestyle="--", linewidth=1.5, alpha=0.7)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            ax.annotate(f"r={r:.2f}{sig}", xy=(0.05, 0.85 - i * 0.08), xycoords="axes fraction",
                        fontsize=9, color=color, fontweight="bold")
        elif len(g) == 2:
            z = np.polyfit(g["PRECTOTCORR"], g["corn_pct"], 1)
            p_fn = np.poly1d(z)
            x_line = np.linspace(g["PRECTOTCORR"].min(), g["PRECTOTCORR"].max(), 50)
            ax.plot(x_line, p_fn(x_line), color=color, linestyle="--", linewidth=1.5, alpha=0.7)

    ax.set_xlabel("Mean Annual Precipitation (mm)", fontsize=11)
    ax.set_ylabel("Mean Corn Coverage (%)", fontsize=11)
    ax.set_title("Field-Level Precip vs Corn % by Grower", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    plt.tight_layout()
    path = out_dir / "weather_crop_correlation.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  Plot saved: {path.name}")
    return str(path)


# ── summary table ────────────────────────────────────────────────────

def write_summary_table(
    boundaries: dict[str, gpd.GeoDataFrame],
    cdl: dict[str, pd.DataFrame],
    rotations: dict[str, pd.DataFrame],
    weather: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    rows = []
    for slug in slug_order:
        label = _grower_label(slug)
        gdf = boundaries.get(slug)
        if gdf is None:
            continue

        field_count = len(gdf)
        mean_area = gdf["area_acres"].mean()
        total_area = gdf["area_acres"].sum()

        corn_pct = None
        soy_pct = None
        cdf = cdl.get(slug)
        if cdf is not None and "crop_code" in cdf.columns and "pct" in cdf.columns:
            by_field = cdf.groupby(["field_id", "crop_code"])["pct"].mean().reset_index()
            corn = by_field[by_field["crop_code"] == 1]["pct"].mean() if 1 in by_field["crop_code"].values else 0
            soy = by_field[by_field["crop_code"] == 5]["pct"].mean() if 5 in by_field["crop_code"].values else 0
            corn_pct = round(corn, 1)
            soy_pct = round(soy, 1)

        crop_div = None
        rot = rotations.get(slug)
        if rot is not None and "crop_diversity" in rot.columns:
            crop_div = round(rot["crop_diversity"].mean(), 1)

        mean_t2m = None
        mean_annual_precip = None
        wdf = weather.get(slug)
        if wdf is not None:
            mean_t2m = round(wdf["T2M"].mean(), 1)
            wdf_copy = wdf.copy()
            wdf_copy["year"] = wdf_copy["date"].dt.year
            annual_precip = wdf_copy.groupby(["field_id", "year"])["PRECTOTCORR"].sum()
            mean_annual_precip = round(annual_precip.groupby("field_id").mean().mean(), 0)

        rows.append({
            "grower": label,
            "field_count": field_count,
            "mean_area_acres": round(mean_area, 1),
            "total_area_acres": round(total_area, 1),
            "mean_corn_pct": corn_pct,
            "mean_soybean_pct": soy_pct,
            "mean_crop_diversity": crop_div,
            "mean_t2m_c": mean_t2m,
            "mean_annual_precip_mm": mean_annual_precip,
        })

    if not rows:
        return ""
    summary = pd.DataFrame(rows)
    path = out_dir / "grower_comparison_summary.csv"
    summary.to_csv(path, index=False)
    print(f"  Summary table saved: {path.name}")
    return str(path)


def write_per_field_table(
    boundaries: dict[str, gpd.GeoDataFrame],
    cdl: dict[str, pd.DataFrame],
    rotations: dict[str, pd.DataFrame],
    weather: dict[str, pd.DataFrame],
    slug_order: list[str],
    out_dir: Path,
) -> str:
    from scipy import stats as scipy_stats
    rows = []
    for slug in slug_order:
        gdf = boundaries.get(slug)
        if gdf is None:
            continue
        label = _grower_label(slug)
        farm_slug = _farm_slug_for_grower(slug)

        cdf = cdl.get(slug)
        rot = rotations.get(slug)
        wdf = weather.get(slug)

        for _, field_row in gdf.iterrows():
            fid = field_row["field_id"]
            area = field_row["area_acres"]

            corn_pct = None
            soy_pct = None
            if cdf is not None:
                fcdl = cdf[cdf["field_id"] == fid]
                corn_sub = fcdl[fcdl["crop_code"] == 1]
                soy_sub = fcdl[fcdl["crop_code"] == 5]
                if not corn_sub.empty:
                    corn_pct = round(corn_sub["pct"].mean(), 1)
                if not soy_sub.empty:
                    soy_pct = round(soy_sub["pct"].mean(), 1)

            crop_div = None
            if rot is not None and "crop_diversity" in rot.columns:
                rsub = rot[rot["field_id"] == fid]
                if not rsub.empty:
                    crop_div = int(rsub["crop_diversity"].iloc[0])

            mean_t2m = None
            mean_precip = None
            if wdf is not None:
                fw = wdf[wdf["field_id"] == fid]
                if not fw.empty:
                    mean_t2m = round(fw["T2M"].mean(), 1)
                    fw_copy = fw.copy()
                    fw_copy["year"] = fw_copy["date"].dt.year
                    ap = fw_copy.groupby("year")["PRECTOTCORR"].sum()
                    mean_precip = round(ap.mean(), 0)

            rows.append({
                "grower": label,
                "field_id": fid,
                "area_acres": round(area, 1),
                "mean_corn_pct": corn_pct,
                "mean_soybean_pct": soy_pct,
                "crop_diversity": crop_div,
                "mean_t2m_c": mean_t2m,
                "mean_annual_precip_mm": mean_precip,
            })

    if not rows:
        return ""
    per_field = pd.DataFrame(rows)
    path = out_dir / "field_level_summary.csv"
    per_field.to_csv(path, index=False)
    print(f"  Per-field table saved: {path.name}")
    return str(path)


# ── main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cross-grower comparison EDA for Assignment 2")
    parser.add_argument(
        "--grower-slugs", nargs="+",
        default=["illinois-grower", "iowa-grower", "nebraska-grower"],
        help="Grower slugs to compare (default: Assignment 2 growers)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(GROWERS_ROOT / "derived" / "reports"),
        help="Output directory for plots and tables (default: growers/derived/reports under DATA_ROOT)",
    )
    args = parser.parse_args()

    output_base = Path(args.output_dir)
    out = _output_dir(output_base)
    slug_order = args.grower_slugs

    print("=" * 60)
    print("Assignment 2 — Cross-Grower Comparison EDA")
    print("=" * 60)
    print(f"Growers: {', '.join(slug_order)}")
    print(f"Output:  {out}")
    print()

    print("Loading data ...")
    boundaries, cdl, rotations, weather = load_all_data(slug_order)

    if not boundaries:
        print("ERROR: No boundary data loaded for any grower.")
        sys.exit(1)

    print()

    has_cdl = any(s in cdl for s in slug_order)
    has_rotations = any(s in rotations for s in slug_order)
    has_weather = any(s in weather for s in slug_order)

    # ── Boundaries (2 stat viz + 1 comparison/correlation) ──
    print("[1/3] Field Boundaries")
    plot_field_size_distribution(boundaries, slug_order, out)
    plot_field_size_boxplot(boundaries, slug_order, out)
    plot_boundary_location_map(boundaries, slug_order, out)
    if has_cdl:
        plot_boundary_crop_correlation(boundaries, cdl, slug_order, out)
    else:
        print("  [SKIP] Field size vs corn correlation — no CDL data")
    print()

    # ── CDL (2 stat viz + 1 comparison/correlation) ──
    print("[2/3] CDL / Cropland")
    if has_cdl:
        plot_cdl_crop_composition(cdl, slug_order, out)
        plot_cdl_field_crop_tile(cdl, slug_order, out)
    else:
        print("  [SKIP] No CDL composition data")
    if has_rotations:
        plot_cdl_crop_diversity(rotations, slug_order, out)
        plot_cdl_rotation_comparison(rotations, slug_order, out)
    else:
        print("  [SKIP] No crop rotation data")
    print()

    # ── Weather (2 stat viz + 1 comparison/correlation) ──
    print("[3/3] Weather")
    if has_weather:
        plot_seasonal_climatology(weather, slug_order, out)
        plot_growing_season(weather, slug_order, out)
        if has_cdl:
            plot_weather_crop_correlation(weather, cdl, slug_order, out)
        else:
            print("  [SKIP] Weather-crop correlation — no CDL data")
    else:
        print("  [SKIP] No weather data")
    print()

    # ── Summary tables ──
    print("[+] Summary tables")
    write_summary_table(boundaries, cdl, rotations, weather, slug_order, out)
    write_per_field_table(boundaries, cdl, rotations, weather, slug_order, out)
    print()

    print("Done. All plots and tables in:")
    print(f"  {out}")


if __name__ == "__main__":
    main()
