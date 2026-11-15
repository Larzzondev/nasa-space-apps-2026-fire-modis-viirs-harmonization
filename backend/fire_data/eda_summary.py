"""Aggregation for one day of FIRMS detections.

Statistics describe archive rows. They do not estimate unique fires, and the
MODIS integer confidence scale is never placed on the VIIRS flag scale.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from fire_data.eda_spatial import (
    DENSITY_METHOD,
    EARTH_RADIUS_M,
    OVERLAP_METHOD,
    count_grid,
    detections_per_1000_km2,
    pairwise_nearest_distances,
)
from fire_data.eda_table import DetectionTable
from fire_data.fields import parse_float

QUANTILES = (0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1.0)
DEFAULT_THRESHOLDS_M = (375.0, 1000.0, 5000.0)
SATELLITE_ORDER = ("Terra", "Aqua", "N20", "N21", "SNPP")
VIIRS_FLAG_ORDER = ("l", "n", "h")

CAVEATS = (
    "All figures and statistics are one-day global observations from the extracted FIRMS archives.",
    "Detections are not unique fires.",
    "No harmonization factor is calculated.",
    "Confidence scales are not equivalent.",
    "Extreme FRP values are retained.",
    "Raw detection counts are not a measure of sensor quality.",
    "This date does not support a seasonal or historical conclusion.",
    "The raw CSV files are not modified.",
)

UTC_NOTE = (
    "acq_time is read as UTC HHMM, which is how FIRMS stores acquisition time. "
    "The hour is the first two digits. Times are not converted to local time. "
    "A single UTC hour contains many local times, so the hour histogram is not a local diurnal cycle. "
    "The daynight column is the archive flag and is not recomputed from the clock."
)

DISPLAY_NAME = {
    "modis": "MODIS",
    "viirs_noaa20": "NOAA-20",
    "viirs_noaa21": "NOAA-21",
    "viirs_snpp": "S-NPP",
    "Terra": "Terra",
    "Aqua": "Aqua",
    "N20": "NOAA-20",
    "N21": "NOAA-21",
    "SNPP": "S-NPP",
}

RowLookup = Callable[[DetectionTable, set[int]], dict[int, dict[str, str]]]


def summarize_numeric(values: np.ndarray) -> dict:
    sample = np.asarray(values, dtype=np.float64)
    count = int(sample.size)
    if count == 0:
        raise ValueError("Cannot summarize an empty detection group")
    quantiles = np.quantile(sample, QUANTILES, method="linear")
    cutoff = float(quantiles[-2])
    zero_count = int(np.count_nonzero(sample == 0.0))
    return {
        "count": count,
        "mean": float(np.mean(sample)),
        "median": float(np.median(sample)),
        "std": None if count < 2 else float(np.std(sample, ddof=1)),
        "minimum": float(np.min(sample)),
        "maximum": float(np.max(sample)),
        "quantiles": {f"{quantile:.3f}": float(value) for quantile, value in zip(QUANTILES, quantiles)},
        "zero_count": zero_count,
        "zero_proportion": zero_count / count,
        "extreme_cutoff": cutoff,
        "extreme_count": int(np.count_nonzero(sample >= cutoff)),
    }


def summarize_confidence(values: np.ndarray, kind: str) -> dict:
    sample = np.asarray(values)
    count = int(sample.size)
    if count == 0:
        raise ValueError("Cannot summarize confidence for an empty group")
    labels, counts = np.unique(sample, return_counts=True)
    observed = {str(label): int(count) for label, count in zip(labels.tolist(), counts.tolist())}
    if kind == "modis_0_100":
        ordered = sorted(observed, key=lambda label: int(label))
        semantics = "MODIS integer confidence stored from 0 through 100."
        median_integer = float(np.median(sample.astype(np.int16)))
    elif kind == "viirs_lnh":
        ordered = [label for label in VIIRS_FLAG_ORDER if label in observed]
        ordered.extend(sorted(set(observed) - set(VIIRS_FLAG_ORDER)))
        semantics = (
            "VIIRS confidence flags stored as l, n, and h. "
            "FIRMS documents those flags as low, nominal, and high. "
            "The words name the stored flags and are not a conversion onto the MODIS 0-100 scale."
        )
        median_integer = None
    else:
        raise ValueError(f"Unknown confidence kind: {kind}")
    return {
        "kind": kind,
        "semantics": semantics,
        "counts": {label: observed[label] for label in ordered},
        "proportions": {label: observed[label] / count for label in ordered},
        "median_integer": median_integer,
    }


def summarize_daynight(values: np.ndarray) -> dict:
    sample = np.asarray(values)
    count = int(sample.size)
    day = int(np.count_nonzero(sample == "D"))
    night = int(np.count_nonzero(sample == "N"))
    other = count - day - night
    counts = {"D": day, "N": night}
    if other:
        counts["other"] = other
    return {
        "counts": counts,
        "proportions": {label: value / count for label, value in counts.items()},
        "meaning": "D and N are the stored daynight flags. They are not recomputed from local solar time.",
    }


def summarize_hours(hour_utc: np.ndarray, acq_hhmm: np.ndarray) -> dict:
    hours = np.asarray(hour_utc, dtype=np.int64)
    if hours.size and (int(hours.min()) < 0 or int(hours.max()) > 23):
        raise ValueError("UTC hour falls outside 0 through 23")
    counts = np.bincount(hours, minlength=24)
    total = int(counts.sum())
    peak_count = int(counts.max()) if total else 0
    peak_hours = [index for index, count in enumerate(counts.tolist()) if count == peak_count] if total else []
    return {
        "bin": "UTC hour from the first two digits of acq_time",
        "counts": counts.astype(int).tolist(),
        "proportions": (counts / total).astype(float).tolist() if total else [0.0] * 24,
        "distinct_timestamps": int(np.unique(acq_hhmm).size) if acq_hhmm.size else 0,
        "peak_hours_utc": peak_hours,
        "peak_count": peak_count,
    }


def _order_satellites(names: list[str]) -> list[str]:
    ordered = [name for name in SATELLITE_ORDER if name in names]
    ordered.extend(sorted(set(names) - set(ordered)))
    return ordered


def _select(values: np.ndarray, positions: np.ndarray | None) -> np.ndarray:
    if positions is None:
        return values
    return values[positions]


def _satellite_positions(table: DetectionTable) -> list[tuple[str, np.ndarray | None, int]]:
    satellites = _order_satellites(np.unique(table.satellite).tolist())
    groups: list[tuple[str, np.ndarray | None, int]] = []
    for satellite in satellites:
        if len(satellites) == 1 and table.satellite.size and str(table.satellite[0]) == satellite:
            groups.append((satellite, None, len(table)))
            continue
        positions = np.flatnonzero(table.satellite == satellite)
        groups.append((satellite, positions, int(positions.size)))
    return groups


def _summarize_columns(
    table: DetectionTable,
    positions: np.ndarray | None,
) -> dict:
    return {
        "detection_count": len(table) if positions is None else int(positions.size),
        "frp": summarize_numeric(_select(table.frp, positions)),
        "brightness": summarize_numeric(_select(table.brightness, positions)),
        "bright_t31": summarize_numeric(_select(table.bright_t31, positions)),
        "scan": summarize_numeric(_select(table.scan, positions)),
        "track": summarize_numeric(_select(table.track, positions)),
        "confidence": summarize_confidence(_select(table.confidence, positions), table.confidence_kind),
        "daynight": summarize_daynight(_select(table.daynight, positions)),
        "acquisition_hour_utc": summarize_hours(
            _select(table.hour_utc, positions),
            _select(table.acq_hhmm, positions),
        ),
    }


def _density_block(latitude: np.ndarray, longitude: np.ndarray, bin_degrees: float, *, keep_grid: bool) -> dict:
    grid, lat_edges, lon_edges = count_grid(latitude, longitude, bin_degrees)
    rate = detections_per_1000_km2(grid, lat_edges, lon_edges)
    max_count = int(grid.max())
    count_ties = np.argwhere(grid == max_count)
    count_lat, count_lon = (int(count_ties[0, 0]), int(count_ties[0, 1]))
    max_rate = float(rate.max())
    rate_ties = np.argwhere(rate == max_rate)
    rate_lat, rate_lon = (int(rate_ties[0, 0]), int(rate_ties[0, 1]))
    block = {
        "bin_degrees": bin_degrees,
        "occupied_cells": int(np.count_nonzero(grid)),
        "max_count": max_count,
        "max_count_ties": int(count_ties.shape[0]),
        "max_count_latitude_south": float(lat_edges[count_lat]),
        "max_count_longitude_west": float(lon_edges[count_lon]),
        "max_detections_per_1000_km2": max_rate,
        "max_rate_ties": int(rate_ties.shape[0]),
        "max_rate_latitude_south": float(lat_edges[rate_lat]),
        "max_rate_longitude_west": float(lon_edges[rate_lon]),
    }
    if keep_grid:
        block["latitude_edges"] = lat_edges.tolist()
        block["longitude_edges"] = lon_edges.tolist()
        block["counts"] = grid.astype(int).tolist()
        block["latitude_band_counts"] = [
            {
                "south": float(lat_edges[index]),
                "north": float(lat_edges[index + 1]),
                "detections": int(grid[index].sum()),
            }
            for index in range(grid.shape[0])
        ]
    return block


def _overlap_pairs(
    coordinates: dict[str, tuple[np.ndarray, np.ndarray]],
    thresholds_m: tuple[float, ...],
) -> list[dict]:
    names = _order_satellites(list(coordinates))
    distances = pairwise_nearest_distances(coordinates, max(thresholds_m))
    pairs = []
    for name_a in names:
        count_a = int(coordinates[name_a][0].size)
        for name_b in names:
            if name_a == name_b:
                continue
            measured = distances[(name_a, name_b)]
            thresholds = []
            for threshold in thresholds_m:
                hits = int(np.count_nonzero(measured <= threshold))
                thresholds.append(
                    {
                        "threshold_m": threshold,
                        "detections_with_neighbor": hits,
                        "proportion": hits / count_a,
                    }
                )
            pairs.append(
                {
                    "satellite_a": name_a,
                    "satellite_b": name_b,
                    "detections_in_a": count_a,
                    "thresholds": thresholds,
                }
            )
    return pairs


def _extreme_records(tables: list[DetectionTable], row_lookup: RowLookup) -> list[dict]:
    records: list[dict] = []
    for table in tables:
        pending: list[tuple[str, int, float, int]] = []
        line_numbers: set[int] = set()
        for satellite, positions, group_count in _satellite_positions(table):
            frp = _select(table.frp, positions)
            cutoff = float(np.quantile(frp, 0.999, method="linear"))
            local = np.flatnonzero(frp >= cutoff)
            chosen = local if positions is None else positions[local]
            for index in chosen.tolist():
                line_number = int(table.line_number[index])
                pending.append((satellite, index, cutoff, group_count))
                line_numbers.add(line_number)
        rows = row_lookup(table, line_numbers)
        for satellite, index, cutoff, group_count in pending:
            line_number = int(table.line_number[index])
            if line_number not in rows:
                raise ValueError(f"{table.source_id} line {line_number} was flagged and then not preserved")
            records.append(
                {
                    "source_id": table.source_id,
                    "archive": table.archive,
                    "line_number": line_number,
                    "satellite": satellite,
                    "group_detection_count": group_count,
                    "extreme_cutoff": cutoff,
                    "frp": float(table.frp[index]),
                    "latitude": float(table.latitude[index]),
                    "longitude": float(table.longitude[index]),
                    "row": rows[line_number],
                }
            )
    records.sort(
        key=lambda item: (
            SATELLITE_ORDER.index(item["satellite"]) if item["satellite"] in SATELLITE_ORDER else len(SATELLITE_ORDER),
            -item["frp"],
            item["source_id"],
            item["line_number"],
        )
    )
    return records


def _validate_thresholds(thresholds_m: tuple[float, ...]) -> tuple[float, ...]:
    if not thresholds_m:
        raise ValueError("At least one overlap threshold is required")
    cleaned = tuple(float(threshold) for threshold in thresholds_m)
    if any(threshold <= 0 for threshold in cleaned):
        raise ValueError("Overlap thresholds must be positive distances in meters")
    return cleaned


def build_summary(
    tables: list[DetectionTable],
    thresholds_m: tuple[float, ...] = DEFAULT_THRESHOLDS_M,
    row_lookup: RowLookup | None = None,
) -> dict:
    if not tables:
        raise ValueError("No detection tables were provided")
    thresholds = _validate_thresholds(thresholds_m)
    dates = tuple(sorted({date for table in tables for date in table.dates}))
    sources: dict[str, dict] = {}
    satellites: dict[str, dict] = {}
    coordinates: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    density: dict[str, dict] = {}
    for table in tables:
        source_summary = _summarize_columns(table, None)
        source_summary["archive"] = table.archive
        source_summary["dates"] = list(table.dates)
        source_summary["confidence_kind"] = table.confidence_kind
        satellite_blocks: dict[str, dict] = {}
        for satellite, positions, group_count in _satellite_positions(table):
            block = _summarize_columns(table, positions)
            block["source_id"] = table.source_id
            block["same_population_as_source"] = group_count == len(table)
            satellite_blocks[satellite] = block
            satellites[satellite] = block
            if positions is None:
                coordinates[satellite] = (table.latitude, table.longitude)
            else:
                coordinates[satellite] = (table.latitude[positions], table.longitude[positions])
        source_summary["satellites"] = satellite_blocks
        sources[table.source_id] = source_summary
        density[table.source_id] = {
            "archive": table.archive,
            "one_degree": _density_block(table.latitude, table.longitude, 1.0, keep_grid=False),
            "thirty_degree": _density_block(table.latitude, table.longitude, 30.0, keep_grid=True),
        }

    if row_lookup is None:
        raise ValueError("A source-row lookup is required so extreme FRP rows can be preserved")
    summary = {
        "scope": {
            "label": "one-day global observations" if len(dates) == 1 else "global observations",
            "dates": list(dates),
            "detection_count": int(sum(len(table) for table in tables)),
            "caveats": list(CAVEATS),
            "populations": (
                "Satellite groups partition each source. "
                "Source totals are the archive row counts. "
                "Adding a source total to its satellite totals double counts the same detections."
            ),
        },
        "numeric_methods": {
            "std": "Sample standard deviation with divisor n-1. Null when a group has fewer than two detections.",
            "quantiles": list(QUANTILES),
            "quantile_method": "numpy.quantile method=linear",
            "zero": "Count of values exactly equal to 0. Zeros remain in the mean, the quantiles, and the extrema.",
            "extremes": (
                "Within each satellite, FRP at or above the 0.999 quantile is flagged, including ties. "
                "Flagged rows remain in every distribution. The flag is an investigation list, not a filter."
            ),
        },
        "utc_time": {"note": UTC_NOTE},
        "sources": sources,
        "satellites": satellites,
        "spatial_density": {
            "method": DENSITY_METHOD,
            "by_source": density,
        },
        "spatial_overlap": {
            "method": OVERLAP_METHOD,
            "earth_radius_m": EARTH_RADIUS_M,
            "thresholds_m": list(thresholds),
            "pairs": _overlap_pairs(coordinates, thresholds),
        },
        "extreme_frp": {
            "rule": (
                "A row is listed when its FRP is at or above the 0.999 quantile of its own satellite, "
                "using the linear quantile method. The original CSV fields are preserved. "
                "line_number is 1-based and counts the header as line 1. "
                "No extreme row is removed from the distributions."
            ),
            "records": _extreme_records(tables, row_lookup),
        },
    }
    problems = summary_problems(summary)
    if problems:
        raise ValueError("EDA summary failed its internal checks: " + "; ".join(problems[:5]))
    return summary


def _numeric_problems(label: str, stats: dict) -> list[str]:
    problems = []
    if stats["zero_count"] > stats["count"]:
        problems.append(f"{label} zero count exceeds the group count")
    if not (stats["minimum"] <= stats["median"] <= stats["maximum"]):
        problems.append(f"{label} median falls outside the extrema")
    if stats["quantiles"]["0.000"] != stats["minimum"] or stats["quantiles"]["1.000"] != stats["maximum"]:
        problems.append(f"{label} quantile endpoints differ from the extrema")
    if stats["extreme_count"] < 1:
        problems.append(f"{label} dropped its extreme tail")
    if stats["std"] is not None and stats["std"] < 0:
        problems.append(f"{label} has a negative standard deviation")
    return problems


def _group_problems(label: str, group: dict) -> list[str]:
    problems = []
    count = group["detection_count"]
    for column in ("frp", "brightness", "bright_t31", "scan", "track"):
        problems.extend(_numeric_problems(f"{label} {column}", group[column]))
        if group[column]["count"] != count:
            problems.append(f"{label} {column} count differs from the detection count")
    confidence = group["confidence"]
    if abs(sum(confidence["proportions"].values()) - 1.0) > 1e-9:
        problems.append(f"{label} confidence proportions do not sum to 1")
    if sum(confidence["counts"].values()) != count:
        problems.append(f"{label} confidence counts do not sum to the group")
    kinds = set(confidence["counts"])
    if confidence["kind"] == "modis_0_100" and kinds & set(VIIRS_FLAG_ORDER):
        problems.append(f"{label} mixes VIIRS flags into MODIS confidence")
    if confidence["kind"] == "viirs_lnh" and any(label.isdigit() for label in kinds):
        problems.append(f"{label} mixes MODIS integers into VIIRS confidence")
    if confidence["kind"] == "viirs_lnh" and confidence["median_integer"] is not None:
        problems.append(f"{label} assigns a numeric median to VIIRS flags")
    daynight = group["daynight"]
    if sum(daynight["counts"].values()) != count:
        problems.append(f"{label} day/night counts do not sum to the group")
    hours = group["acquisition_hour_utc"]["counts"]
    if len(hours) != 24 or sum(hours) != count:
        problems.append(f"{label} UTC hour counts do not cover the group")
    return problems


def summary_problems(summary: dict) -> list[str]:
    problems: list[str] = []
    source_total = 0
    for source_id, source in summary["sources"].items():
        source_total += source["detection_count"]
        problems.extend(_group_problems(f"source {source_id}", source))
        satellite_total = 0
        for satellite, block in source["satellites"].items():
            satellite_total += block["detection_count"]
            problems.extend(_group_problems(f"satellite {satellite}", block))
            if block["confidence"]["kind"] != source["confidence_kind"]:
                problems.append(f"{satellite} confidence kind differs from {source_id}")
        if satellite_total != source["detection_count"]:
            problems.append(f"{source_id} satellites do not partition the archive")
    if source_total != summary["scope"]["detection_count"]:
        problems.append("Source counts do not match the scope total")
    pairs = summary["spatial_overlap"]["pairs"]
    if any(pair["satellite_a"] == pair["satellite_b"] for pair in pairs):
        problems.append("Spatial overlap includes a self-pair")
    satellite_count = len(summary["satellites"])
    expected_pairs = satellite_count * (satellite_count - 1)
    if len(summary["spatial_overlap"]["pairs"]) != expected_pairs:
        problems.append("Spatial overlap pair count does not match the ordered satellite pairs")
    for pair in summary["spatial_overlap"]["pairs"]:
        for threshold in pair["thresholds"]:
            hits = threshold["detections_with_neighbor"]
            if hits > pair["detections_in_a"] or not 0.0 <= threshold["proportion"] <= 1.0:
                problems.append(f"{pair['satellite_a']} to {pair['satellite_b']} overlap is outside 0 to 1")
    seen_lines: set[tuple[str, int]] = set()
    maxima: dict[str, float] = {}
    for record in summary["extreme_frp"]["records"]:
        key = (record["source_id"], record["line_number"])
        if key in seen_lines:
            problems.append(f"Duplicate extreme row {key}")
        seen_lines.add(key)
        if record["frp"] < record["extreme_cutoff"]:
            problems.append(f"{record['satellite']} lists an FRP below its cutoff")
        parsed = parse_float(record["row"]["frp"])
        latitude = parse_float(record["row"]["latitude"])
        longitude = parse_float(record["row"]["longitude"])
        if parsed != record["frp"]:
            problems.append(f"{record['satellite']} line {record['line_number']} lost its source FRP text")
        if latitude != record["latitude"] or longitude != record["longitude"]:
            problems.append(f"{record['satellite']} line {record['line_number']} lost its source coordinates")
        maxima[record["satellite"]] = max(maxima.get(record["satellite"], record["frp"]), record["frp"])
    for satellite, block in summary["satellites"].items():
        if satellite not in maxima or maxima[satellite] != block["frp"]["maximum"]:
            problems.append(f"{satellite} maximum FRP is missing from the extreme records")
    if "harmonized_confidence" in summary or "harmonization_factor" in summary:
        problems.append("A harmonization quantity was added to the summary")
    return problems
