# Local Instructions

## Purpose

This folder owns the field dashboard workflow — a per-field multi-year visualization that combines NDVI time series, daily weather, and CDL crop labels into a single summary image.

## Selected Field

- **Grower:** nebraska-grower
- **Farm:** nebraska-farm
- **Field:** osm-796351098 (24.4 acres, Merrick County, Nebraska)
- **Prototype year:** 2022
- **CDL crop (prototype year):** Corn

## Safe edit scope

Edits should stay in this folder and its children unless the user explicitly asks for a broader skill change. Do not change parent `SKILL.md`, sibling EDA workflows, or root policy from a subskill task unless explicitly requested.

## Read nearby docs first

Read `README.md` first, then `GUIDE.md`. If routing context is needed, read `../INDEX.md` and `../../SKILL.md`.

## Local validation

Run `./scripts/validate.sh` from the repository root after structural changes. After code changes, test against the existing nebraska-grower runtime data by running `generate_field_dashboard.py` with default arguments.

## Local-delta-only reminder

This nested AGENTS.md only records instructions that differ from the parent or root files. Do not duplicate root-wide asset, vendor, or validation policy here except this pointer to `../../../AGENTS.md`.
