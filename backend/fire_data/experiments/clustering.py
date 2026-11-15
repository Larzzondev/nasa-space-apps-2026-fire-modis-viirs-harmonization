"""Experiment A: representative-date cluster stability.

The seven full-month DBSCAN settings are cited from the published within-sensor
report. New labels are fit only on each satellite's representative date, plus
the existing 180-minute adjacent-date margin. Component ids are not fire ids.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fire_data.eda_figures import COLORS
from fire_data.eda_spatial import EARTH_RADIUS_M, lonlat_to_ecef
from fire_data.experiments.common import (
    DISPLAY,
    INDEX,
    SATELLITE_ORDER,
    ExperimentRunError,
    Stopwatch,
    assert_locks,
    base_results,
    begin,
    confidence_code,
    daynight_code,
    finish,
    publish_run,
    read_json,
    require_july_timestamp,
    require_satellite,
    save_figure,
    scan_archives,
    verify_checksum_cache,
    write_json,
)
from fire_data.experiments.prepare import ExperimentConfigError
from fire_data.experiments.validate import SchemaError
from fire_data.monthly_scan import ARCHIVES, ZERO_ROW_MEANING
from fire_data.spatiotemporal_analysis import AnalysisError
from fire_data.within_sensor_analysis import (
    FACTORIAL_EPS_M,
    FACTORIAL_MIN_SAMPLES,
    FACTORIAL_WINDOWS_MIN,
    FULL_SETTINGS,
    MAX_WINDOW_MIN,
    REPORT_JSON,
    directed_pairs,
    labels_from_pairs,
    margin_indices,
    summarize_labels,
)

SENSOR_FOR = {
    "Terra": "modis",
    "Aqua": "modis",
    "SNPP": "viirs_snpp",
    "N20": "viirs_noaa20",
    "N21": "viirs_noaa21",
}


def neighbor_flags(
    left: np.ndarray,
    right: np.ndarray,
    distance: np.ndarray,
    delta: np.ndarray,
    owned: int,
    eps_m: float,
    window_min: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Owned rows with a same-date neighbor, and with a margin neighbor.

    An edge counts in either direction. A margin neighbor is a row kept only
    because its clock falls inside the adjacent-date window.
    """

    has_same = np.zeros(owned, dtype=bool)
    has_margin = np.zeros(owned, dtype=bool)
    selected = (distance <= eps_m) & (delta <= window_min)
    if not np.any(selected):
        return has_same, has_margin
    pairs = ((left[selected], right[selected]), (right[selected], left[selected]))
    for source, partner in pairs:
        owned_source = source < owned
        if not np.any(owned_source):
            continue
        origin = source[owned_source]
        other = partner[owned_source]
        same = other < owned
        has_same[origin[same]] = True
        has_margin[origin[~same]] = True
    return has_same, has_margin


def _core_mask(
    count: int,
    left: np.ndarray,
    right: np.ndarray,
    distance: np.ndarray,
    delta: np.ndarray,
    *,
    eps_m: float,
    window_min: int,
    min_samples: int,
) -> np.ndarray:
    selected = (distance <= eps_m) & (delta <= window_min)
    if np.any(selected):
        endpoints_a = np.minimum(left[selected], right[selected])
        endpoints_b = np.maximum(left[selected], right[selected])
        order = np.lexsort((endpoints_b, endpoints_a))
        endpoints_a = endpoints_a[order]
        endpoints_b = endpoints_b[order]
        duplicate = np.zeros(endpoints_a.size, dtype=bool)
        duplicate[1:] = (endpoints_a[1:] == endpoints_a[:-1]) & (endpoints_b[1:] == endpoints_b[:-1])
        endpoints_a = endpoints_a[~duplicate]
        endpoints_b = endpoints_b[~duplicate]
        degree = np.bincount(np.concatenate([endpoints_a, endpoints_b]), minlength=count)
    else:
        degree = np.zeros(count, dtype=np.int64)
    return degree + 1 >= min_samples


def _noise_stability(primary: np.ndarray, other: np.ndarray) -> dict[str, float | int]:
    noise_primary = primary < 0
    noise_other = other < 0
    flips = noise_primary != noise_other
    rows = int(primary.size)
    return {
        "rows": rows,
        "rows_whose_noise_label_flips": int(np.count_nonzero(flips)),
        "flip_share": None if rows == 0 else float(np.count_nonzero(flips)) / rows,
        "cluster_identifiers_are_compared": False,
        "same_fire": "not_assessed",
    }


def _same_minute(labels_minute: np.ndarray, labels_half_hour: np.ndarray, owned: int) -> dict[str, Any]:
    minute = labels_minute[:owned]
    half_hour = labels_half_hour[:owned]
    clustered = half_hour >= 0
    clustered_rows = int(np.count_nonzero(clustered))
    already = int(np.count_nonzero(clustered & (minute >= 0)))
    pure_rows = 0
    pure_components = 0
    components = 0
    if clustered_rows:
        ids = half_hour[clustered]
        minute_ids = minute[clustered]
        order = np.argsort(ids, kind="mergesort")
        ids = ids[order]
        minute_ids = minute_ids[order]
        change = np.empty(ids.size, dtype=bool)
        change[0] = True
        change[1:] = ids[1:] != ids[:-1]
        starts = np.flatnonzero(change)
        ends = np.append(starts[1:], ids.size)
        components = int(starts.size)
        for start, end in zip(starts, ends, strict=True):
            group = minute_ids[start:end]
            present = group[group >= 0]
            if present.size == group.size and np.unique(present).size == 1:
                pure_components += 1
                pure_rows += int(group.size)
    return {
        "owned_rows": owned,
        "rows_clustered_at_30_minutes": clustered_rows,
        "rows_clustered_at_30_minutes_and_already_clustered_at_0_minutes": already,
        "share_of_30_minute_clustered_rows_already_clustered_at_0_minutes": (
            None if clustered_rows == 0 else already / clustered_rows
        ),
        "components_at_30_minutes": components,
        "components_whose_owned_rows_share_one_0_minute_component": pure_components,
        "rows_in_those_components": pure_rows,
        "noise_label_agreement_share": _agreement_share(minute, half_hour),
        "component_ids_are_not_matched_across_settings": True,
        "same_fire": "not_assessed",
        "clusters_are_confirmed_fires": False,
    }


def _agreement_share(minute: np.ndarray, half_hour: np.ndarray) -> float | None:
    if minute.size == 0:
        return None
    flips = int(np.count_nonzero((minute < 0) != (half_hour < 0)))
    return 1.0 - flips / int(minute.size)


def _load_blocks(dates: dict[str, str]) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, np.ndarray], int, int]:
    """Keep every row's day count, and the coordinates needed for the representative partitions."""

    needed_days = {name: set() for name in SATELLITE_ORDER}
    target_day = {}
    for name, text in dates.items():
        day = int(text[8:10])
        target_day[name] = day
        needed_days[name].update({day - 1, day, day + 1})
    specs = {str(spec["sensor"]): spec for spec in ARCHIVES}
    kept: dict[str, dict[str, list[Any]]] = {
        name: {"day": [], "minute": [], "latitude": [], "longitude": []} for name in SATELLITE_ORDER
    }
    daily = {name: np.zeros(32, dtype=np.int64) for name in SATELLITE_ORDER}

    def consume(sensor: str, row: list[str], index: dict[str, int]) -> None:
        del index
        satellite = require_satellite(row, specs[sensor]["satellites"], sensor)
        day, minute = require_july_timestamp(row, sensor, satellite)
        daily[satellite][day] += 1
        if day not in needed_days[satellite]:
            return
        bucket = kept[satellite]
        bucket["day"].append(day)
        bucket["minute"].append(minute)
        bucket["latitude"].append(float(row[INDEX["latitude"]]))
        bucket["longitude"].append(float(row[INDEX["longitude"]]))
        confidence_code(row, str(specs[sensor]["confidence"]), sensor)
        daynight_code(row, sensor)

    counts = scan_archives(tuple(spec["sensor"] for spec in ARCHIVES), consume)
    arrays = {
        name: {key: np.asarray(values) for key, values in bucket.items()}
        for name, bucket in kept.items()
    }
    for name, bucket in arrays.items():
        bucket["day"] = bucket["day"].astype(np.int16)
        bucket["minute"] = bucket["minute"].astype(np.int16)
        bucket["latitude"] = bucket["latitude"].astype(np.float64)
        bucket["longitude"] = bucket["longitude"].astype(np.float64)
    rows_read = sum(counts[sensor] for sensor in counts if sensor != "source_bytes_read")
    return arrays, daily, int(rows_read), int(counts["source_bytes_read"])


def _partition(block: dict[str, np.ndarray], day: int) -> tuple[np.ndarray, np.ndarray, int]:
    owned_mask = block["day"] == day
    by_day: dict[int, np.ndarray] = {}
    if block["day"].size:
        order = np.argsort(block["day"], kind="mergesort")
        days = block["day"][order]
        change = np.empty(days.size, dtype=bool)
        change[0] = True
        if days.size > 1:
            change[1:] = days[1:] != days[:-1]
        starts = np.flatnonzero(change)
        ends = np.append(starts[1:], days.size)
        by_day = {int(days[start]): order[start:end] for start, end in zip(starts, ends, strict=True)}
    owned = by_day.get(day, np.empty(0, dtype=np.int64))
    margin = margin_indices(by_day, block["minute"], day, MAX_WINDOW_MIN)
    chosen = np.concatenate([owned, margin]) if margin.size else owned
    if chosen.size == 0:
        empty = np.empty((0, 3), dtype=np.float64)
        return empty, np.empty(0, dtype=np.int32), 0
    latitude = block["latitude"][chosen]
    longitude = block["longitude"][chosen]
    ecef = lonlat_to_ecef(latitude, longitude)
    epoch = (block["day"][chosen].astype(np.int32) - 1) * 1440 + block["minute"][chosen].astype(np.int32)
    return ecef, epoch, int(owned.size)


def _compare_factorial(recomputed: list[dict[str, Any]], published: list[dict[str, Any]]) -> dict[str, Any]:
    mismatches = []
    published_by_key = {
        (float(item["eps_m"]), int(item["window_min"]), int(item["min_samples"])): item for item in published
    }
    for item in recomputed:
        key = (float(item["eps_m"]), int(item["window_min"]), int(item["min_samples"]))
        prior = published_by_key.get(key)
        if prior is None:
            mismatches.append({"setting": list(key), "reason": "missing from the published factorial"})
            continue
        for field in ("rows", "noise_rows", "clustered_rows", "partition_cluster_count"):
            if int(item[field]) != int(prior[field]):
                mismatches.append(
                    {
                        "setting": {"eps_m": key[0], "window_min": key[1], "min_samples": key[2]},
                        "field": field,
                        "recomputed": int(item[field]),
                        "published": int(prior[field]),
                    }
                )
    return {
        "cells": 27,
        "matches_published_representative_date": not mismatches,
        "mismatches": mismatches,
        "published_report": "reports/within_sensor_analysis_2024_07.json",
        "full_month_recomputed": False,
    }


def _analyze_satellite(
    name: str,
    block: dict[str, np.ndarray],
    daily: np.ndarray,
    date_text: str,
    published_sensor: dict[str, Any],
) -> dict[str, Any]:
    day = int(date_text[8:10])
    present = [index for index in range(1, 32) if int(daily[index]) > 0]
    counts = [(index, int(daily[index])) for index in present]
    target = float(np.median(np.array([count for _, count in counts], dtype=np.float64))) if counts else None
    chosen = representative_day_from_counts(counts)
    ecef, epoch, owned = _partition(block, day)
    if ecef.shape[0] < 2:
        left = right = distance = np.empty(0)
        delta = np.empty(0, dtype=np.int32)
    else:
        # Every setting labeled here uses a radius of at most 2 km. Pairs beyond
        # that radius cannot change these labels, so the 5 km pair list is not built.
        left, right, distance, delta = directed_pairs(ecef, epoch, 2_000.0)
    factorial = []
    labeled: dict[tuple[float, int, int], np.ndarray] = {}
    for eps in FACTORIAL_EPS_M:
        for window in FACTORIAL_WINDOWS_MIN:
            for minimum in FACTORIAL_MIN_SAMPLES:
                labels = labels_from_pairs(
                    int(ecef.shape[0]),
                    left,
                    right,
                    distance,
                    delta,
                    eps_m=float(eps),
                    window_min=int(window),
                    min_samples=int(minimum),
                )
                labeled[(float(eps), int(window), int(minimum))] = labels
                item = summarize_labels(labels, owned=owned)
                item.update(
                    {
                        "eps_m": float(eps),
                        "window_min": int(window),
                        "min_samples": int(minimum),
                        "noise_share": None if int(item["rows"]) == 0 else int(item["noise_rows"]) / int(item["rows"]),
                        "date": date_text,
                        "min_samples_includes_row": True,
                        "label_meaning": "analytical_component_not_a_fire",
                    }
                )
                factorial.append(item)
    published_factorial = published_sensor["dbscan_representative_day"]["factorial"]
    comparison = _compare_factorial(factorial, published_factorial)
    primary_key = (1000.0, 30, 4)
    minute_key = (1000.0, 0, 4)
    primary = labeled[primary_key]
    alternate = labels_from_pairs(
        int(ecef.shape[0]),
        left,
        right,
        distance,
        delta,
        eps_m=1000.0,
        window_min=30,
        min_samples=4,
        border_tie_break="largest_core_index",
    )
    core = _core_mask(
        int(ecef.shape[0]),
        left,
        right,
        distance,
        delta,
        eps_m=1000.0,
        window_min=30,
        min_samples=4,
    )
    owned_primary = primary[:owned]
    owned_alternate = alternate[:owned]
    owned_core = core[:owned]
    moved = owned_primary != owned_alternate
    border = (~owned_core) & ((owned_primary >= 0) | (owned_alternate >= 0))
    stability = []
    for setting in FULL_SETTINGS:
        key = (float(setting["eps_m"]), int(setting["window_min"]), int(setting["min_samples"]))
        if key == primary_key:
            continue
        compared = _noise_stability(owned_primary, labeled[key][:owned])
        compared.update({"role": setting["role"], "eps_m": key[0], "window_min": key[1], "min_samples": key[2]})
        stability.append(compared)
    margin_reports = []
    for eps, window, role in ((1000.0, 0, "same_minute"), (1000.0, 30, "primary"), (1000.0, 180, "wider_window")):
        has_same, has_margin = neighbor_flags(left, right, distance, delta, owned, eps, window)
        only = has_margin & ~has_same
        margin_reports.append(
            {
                "role": role,
                "eps_m": eps,
                "window_min": window,
                "owned_rows": owned,
                "rows_with_same_date_neighbor": int(np.count_nonzero(has_same)),
                "rows_with_margin_neighbor": int(np.count_nonzero(has_margin)),
                "rows_whose_in_window_neighbor_is_only_in_the_margin": int(np.count_nonzero(only)),
                "margin_rows_are_context": True,
                "partition_counts_are_additive": False,
                "same_fire": "not_assessed",
            }
        )
    absent = [f"2024-07-{index:02d}" for index in range(1, 32) if int(daily[index]) == 0]
    return {
        "satellite": name,
        "display": DISPLAY[name],
        "date": date_text,
        "owned_rows": owned,
        "margin_context_rows": int(ecef.shape[0] - owned),
        "representative_date_matches_published_rule": chosen == day,
        "median_daily_rows_among_dates_with_rows": target,
        "dates_with_rows": len(present),
        "dates_without_rows": absent,
        "dates_without_rows_are_zero_detections": False,
        "dates_without_rows_meaning": ZERO_ROW_MEANING,
        "earth_radius_m": EARTH_RADIUS_M,
        "distance": "great_circle_from_ecef_chord",
        "pair_radius_m": 2000.0,
        "margin_minutes": MAX_WINDOW_MIN,
        "min_samples_includes_row": True,
        "factorial": factorial,
        "factorial_reproducibility": comparison,
        "published_full_month": [
            {
                "eps_m": item["eps_m"],
                "window_min": item["window_min"],
                "min_samples": item["min_samples"],
                "role": item["role"],
                "rows": item["rows"],
                "noise_rows": item["noise_rows"],
                "noise_share": item["noise_share"],
                "partition_cluster_count_sum": item["partition_cluster_count_sum"],
                "partition_cluster_count_is_additive": False,
                "recomputed": False,
                "clusters_are_confirmed_fires": False,
            }
            for item in published_sensor["dbscan_full_coverage"]
        ],
        "border_assignment": {
            "setting": {"eps_m": 1000.0, "window_min": 30, "min_samples": 4},
            "published_tie_break": "smallest_core_index",
            "alternate_tie_break": "largest_core_index",
            "owned_rows": owned,
            "owned_core_rows": int(np.count_nonzero(owned_core)),
            "owned_border_rows": int(np.count_nonzero(border)),
            "owned_rows_whose_label_changes": int(np.count_nonzero(moved)),
            "owned_border_rows_whose_label_changes": int(np.count_nonzero(moved & border)),
            "core_labels_changed": int(np.count_nonzero(moved & owned_core)),
            "label_is_a_fire_identifier": False,
            "same_fire": "not_assessed",
        },
        "noise_label_stability_against_primary": stability,
        "same_minute_components": _same_minute(labeled[minute_key], primary, owned),
        "margin_only_neighbors": margin_reports,
        "same_fire": "not_assessed",
        "clusters_are_confirmed_fires": False,
    }


def representative_day_from_counts(counts: list[tuple[int, int]]) -> int | None:
    if not counts:
        return None
    target = float(np.median(np.array([count for _, count in counts], dtype=np.float64)))
    day, _count = min(counts, key=lambda item: (abs(item[1] - target), item[0]))
    return int(day)


def _figures(results: dict[str, Any], directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    names = []
    roles = [setting["role"] for setting in FULL_SETTINGS]
    figure, axis = plt.subplots(figsize=(10.5, 5.2))
    positions = np.arange(len(FULL_SETTINGS))
    width = 0.15
    for index, sensor in enumerate(results["satellites"]):
        shares = []
        lookup = {
            (float(item["eps_m"]), int(item["window_min"]), int(item["min_samples"])): item["noise_share"]
            for item in sensor["factorial"]
        }
        for setting in FULL_SETTINGS:
            key = (float(setting["eps_m"]), int(setting["window_min"]), int(setting["min_samples"]))
            share = lookup[key]
            shares.append(0.0 if share is None else float(share))
        axis.bar(positions + (index - 2) * width, shares, width=width, color=COLORS[sensor["satellite"]], label=sensor["display"])
    axis.set_xticks(positions)
    axis.set_xticklabels(roles, rotation=25, ha="right")
    axis.set_ylim(0, 1)
    axis.set_ylabel("Noise share of owned rows")
    axis.set_title("Representative-date DBSCAN noise share")
    axis.legend(ncol=5, frameon=False)
    path = directory / "representative_noise_share.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)

    figure, axis = plt.subplots(figsize=(8.5, 4.6))
    labels = [sensor["display"] for sensor in results["satellites"]]
    changed = [sensor["border_assignment"]["owned_border_rows_whose_label_changes"] for sensor in results["satellites"]]
    border = [sensor["border_assignment"]["owned_border_rows"] for sensor in results["satellites"]]
    axis.bar(labels, border, color="#c8c1b4", label="Border rows")
    axis.bar(labels, changed, color="#8c4a2f", label="Border rows that change label")
    axis.set_ylabel("Owned rows")
    axis.set_title("Border tie-break at 1 km, 30 min, min_samples 4")
    axis.legend(frameon=False)
    path = directory / "border_tie_break.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)

    figure, axis = plt.subplots(figsize=(8.5, 4.6))
    roles = ("same_minute", "primary", "wider_window")
    width = 0.25
    positions = np.arange(len(results["satellites"]))
    for index, role in enumerate(roles):
        values = []
        for sensor in results["satellites"]:
            record = next(item for item in sensor["margin_only_neighbors"] if item["role"] == role)
            values.append(record["rows_whose_in_window_neighbor_is_only_in_the_margin"])
        axis.bar(positions + (index - 1) * width, values, width=width, label=role.replace("_", " "))
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel("Owned rows")
    axis.set_title("Neighbors that exist only inside the 180-minute margin")
    axis.legend(frameon=False)
    path = directory / "margin_only_neighbors.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)
    return names


def _markdown(results: dict[str, Any]) -> str:
    lines = [
        "# Experiment A: spatial-temporal clustering",
        "",
        "Question: how stable are the within-sensor analytical components on the representative date when the neighborhood or the border rule changes, and how much of that neighborhood exists only because of the midnight margin?",
        "",
        "Scope: `published_baseline_plus_representative_date`. The seven full-month settings are cited. They were not fit again. New labels cover one UTC date per satellite plus the 180-minute adjacent-date margin. `full_month_rebuild` was not run.",
        "",
        f"`same_fire` is `{results['same_fire']}`. A component id is an analytical label inside one date partition. It is not a fire identifier. Partition counts are not additive and are not a monthly fire total.",
        "",
        f"Distance is the great-circle length recovered from the ECEF chord on a sphere of radius {results['earth_radius_m']} m. `min_samples` includes the row.",
        "",
        "## Representative dates",
        "",
        "| Satellite | Date | Owned rows | Margin context rows | Dates without rows | Factorial matches published |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for sensor in results["satellites"]:
        lines.append(
            f"| {sensor['display']} | {sensor['date']} | {sensor['owned_rows']} | {sensor['margin_context_rows']} | "
            f"{len(sensor['dates_without_rows'])} | {sensor['factorial_reproducibility']['matches_published_representative_date']} |"
        )
    lines.extend(
        [
            "",
            "Dates without rows stay out of the cluster denominators. They are not entered as zero clusters. S-NPP's empty dates are in that satellite's list when the file has no row for them.",
            "",
            "## Published full-month baseline",
            "",
            "These noise shares are copied from the within-sensor report. This run did not recompute them.",
            "",
            "| Satellite | 375 m / 30 min | 1 km / 30 min | 2 km / 30 min | 1 km / 0 min | 1 km / 180 min | min_samples 2 | min_samples 8 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in results["satellites"]:
        shares = [f"{float(item['noise_share']):.3f}" for item in sensor["published_full_month"]]
        lines.append("| " + sensor["display"] + " | " + " | ".join(shares) + " |")
    lines.extend(
        [
            "",
            "The 1 km, 30 minute, `min_samples` 4 column is the primary setting. At 375 m the published MODIS noise share is 1. Terra and Aqua are not pooled, because a 375 m radius is a different relative scale on MODIS than on VIIRS.",
            "",
            "## Representative-date factorial",
            "",
            "The 27 cells were labeled again from the July CSVs and compared with the published representative-date factorial. A match is an exact match of owned rows, noise rows, clustered rows, and the partition component count.",
            "",
            "| Satellite | Primary noise share | Primary components | Primary clustered rows |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for sensor in results["satellites"]:
        primary = next(
            item
            for item in sensor["factorial"]
            if item["eps_m"] == 1000.0 and item["window_min"] == 30 and item["min_samples"] == 4
        )
        share = primary["noise_rows"] / primary["rows"] if primary["rows"] else None
        lines.append(
            f"| {sensor['display']} | {share:.3f} | {primary['partition_cluster_count']} | {primary['clustered_rows']} |"
        )
    lines.extend(
        [
            "",
            "Noise share moves with radius, window, and `min_samples`. The factorial table in `results.json` is the sensitivity record. Component ids are not aligned across those cells.",
            "",
            "## Border assignment",
            "",
            "The published rule gives a border row to the neighboring core component with the smallest core index. The alternate rule uses the largest core index. The count below is the number of owned border rows whose label changes. It is not a better fire map.",
            "",
            "| Satellite | Border rows | Border rows that change | Core rows whose label changes |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for sensor in results["satellites"]:
        border = sensor["border_assignment"]
        lines.append(
            f"| {sensor['display']} | {border['owned_border_rows']} | {border['owned_border_rows_whose_label_changes']} | {border['core_labels_changed']} |"
        )
    lines.extend(
        [
            "",
            "## Same archived minute",
            "",
            "The 0-minute window is the archived `acq_time`. The comparison asks how much of the 30-minute component structure, at 1 km and `min_samples` 4, is already present at that minute.",
            "",
            "| Satellite | Clustered at 30 min | Also clustered at 0 min | Share | Components that stay one 0-minute component |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in results["satellites"]:
        item = sensor["same_minute_components"]
        share = item["share_of_30_minute_clustered_rows_already_clustered_at_0_minutes"]
        share_text = "n/a" if share is None else f"{share:.3f}"
        lines.append(
            f"| {sensor['display']} | {item['rows_clustered_at_30_minutes']} | "
            f"{item['rows_clustered_at_30_minutes_and_already_clustered_at_0_minutes']} | {share_text} | "
            f"{item['components_whose_owned_rows_share_one_0_minute_component']} |"
        )
    lines.extend(
        [
            "",
            "## Cross-midnight margin",
            "",
            "A margin-only row has at least one neighbor inside the stated radius and window on an adjacent date, and no neighbor inside that same limit on its own date. Those rows are context. They are not copied into a second date and they do not add the two dates into one component inventory.",
            "",
            "| Satellite | 0 min | 30 min | 180 min |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for sensor in results["satellites"]:
        values = {
            item["role"]: item["rows_whose_in_window_neighbor_is_only_in_the_margin"]
            for item in sensor["margin_only_neighbors"]
        }
        lines.append(f"| {sensor['display']} | {values['same_minute']} | {values['primary']} | {values['wider_window']} |")
    lines.extend(
        [
            "",
            "## Noise-label stability",
            "",
            "Each published one-factor setting is compared with the primary setting on the same owned rows. The share is the fraction of rows whose noise label flips. Cluster ids are not treated as the same object across settings.",
            "",
            "The per-setting shares are in `results.json` under `noise_label_stability_against_primary`.",
            "",
            "## Limits",
            "",
            "- No row is labeled the same fire as another row.",
            "- Empty dates are absent. They are not zero-fire days and they were not filled.",
            "- NOAA-20 and NOAA-21 processing level stays unresolved.",
            "- No harmonization coefficient was calculated. XGBoost was not trained.",
            "- scikit-learn DBSCAN was not used. The neighborhood is a spatial radius combined with a time window.",
            "",
        ]
    )
    return "\n".join(lines)


def run(work_root: Path, run_id: str, checksum_cache: Path) -> int:
    clock = Stopwatch()
    destination: Path | None = None
    schema: dict[str, Any] | None = None
    try:
        destination, config, schema = begin("A", work_root, run_id)
        assert_locks(config)
        if config["parameters"]["execution_scope"] != "published_baseline_plus_representative_date":
            raise ExperimentRunError("experiment A must stay on the representative-date scope")
        if config["parameters"]["earth_radius_m"] != EARTH_RADIUS_M:
            raise ExperimentRunError("earth radius does not match EARTH_RADIUS_M")
        checksums = verify_checksum_cache(checksum_cache, config)
        published = read_json(REPORT_JSON)
        published_by_satellite = {sensor["satellite"]: sensor for sensor in published["sensors"]}
        blocks, daily, rows_read, bytes_read = _load_blocks(config["parameters"]["representative_dates"])
        satellites = []
        for name in SATELLITE_ORDER:
            date_text = config["parameters"]["representative_dates"][name]
            satellites.append(_analyze_satellite(name, blocks[name], daily[name], date_text, published_by_satellite[name]))
        records = sum(sensor["owned_rows"] for sensor in satellites)
        matched = all(sensor["factorial_reproducibility"]["matches_published_representative_date"] for sensor in satellites)
        core_stable = all(sensor["border_assignment"]["core_labels_changed"] == 0 for sensor in satellites)
        dates_ok = all(sensor["representative_date_matches_published_rule"] for sensor in satellites)
        results = base_results(config, checksums)
        results.update(
            {
                "execution_scope": config["parameters"]["execution_scope"],
                "full_month_rebuild": False,
                "earth_radius_m": EARTH_RADIUS_M,
                "min_samples_includes_row": True,
                "label_meaning": "analytical_component_not_a_fire",
                "satellites": satellites,
                "published_settings_reused": [dict(setting) for setting in FULL_SETTINGS],
                "representative_factorial_matches_published": matched,
                "records_processed": records,
            }
        )
        checks = [
            {"name": "factorial_matches_published", "passed": matched},
            {"name": "core_labels_unchanged_by_border_rule", "passed": core_stable},
            {"name": "representative_dates_match_rule", "passed": dates_ok},
            {"name": "same_fire_not_assessed", "passed": results["same_fire"] == "not_assessed"},
            {"name": "full_month_not_rebuilt", "passed": results["full_month_rebuild"] is False},
            {"name": "source_rows_match_manifest", "passed": rows_read == config["inputs"]["expected_rows"]},
        ]
        status = "completed" if all(item["passed"] for item in checks) else "failed"
        results["validation"] = checks
        figure_names = _figures(results, destination / "figures")
        results["figures"] = figure_names
        write_json(destination / "results.json", results)
        (destination / "report.md").write_text(_markdown(results), encoding="utf-8")
        write_json(destination / "validation.json", {"passed": status == "completed", "checks": checks})
        execution = {
            "wall_clock_seconds": clock.wall(),
            "cpu_seconds": clock.cpu(),
            "source_rows_read": rows_read,
            "source_bytes_read": bytes_read,
            "records_processed": records,
            "records_per_second": None if clock.wall() == 0 else records / clock.wall(),
            "retries": 0,
            "cancelled": False,
        }
        write_json(destination / "execution.json", execution)
        finish(
            destination,
            schema,
            status=status,
            science_executed=True,
            results=results,
            source_rows_read=rows_read,
            source_bytes_read=bytes_read,
            records_processed=records,
            science_seconds=clock.wall(),
            cpu_seconds=clock.cpu(),
        )
        publish_run(destination, "A")
        return 0 if status == "completed" else 1
    except (OSError, ExperimentRunError, ExperimentConfigError, SchemaError, AnalysisError, KeyError, ValueError) as exc:
        if destination is not None and schema is not None:
            _fail(destination, schema, clock, exc)
        else:
            print(str(exc))
        return 1


def _fail(destination: Path, schema: dict[str, Any], clock: Stopwatch, exc: Exception) -> None:
    payload = {"error": f"{type(exc).__name__}: {exc}", "same_fire": "not_assessed"}
    try:
        finish(
            destination,
            schema,
            status="failed",
            science_executed=True,
            results=payload,
            source_rows_read=0,
            source_bytes_read=0,
            records_processed=0,
            science_seconds=clock.wall(),
            cpu_seconds=clock.cpu(),
        )
    except (OSError, ExperimentRunError):
        (destination / "error.txt").write_text(str(exc), encoding="utf-8")
    write_json(destination / "validation.json", {"passed": False, "checks": [{"name": "run", "passed": False, "detail": str(exc)}]})
    try:
        publish_run(destination, "A")
    except OSError:
        pass

