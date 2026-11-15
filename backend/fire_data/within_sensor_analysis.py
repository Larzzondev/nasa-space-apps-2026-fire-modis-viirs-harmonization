"""Within-sensor neighborhoods for the July 2024 FIRMS archives.

Every result counts archived rows from one satellite. A nearest neighbor, a
count of nearby rows, and a DBSCAN component are not confirmed physical fires.
``same_fire`` stays ``not_assessed``. No harmonization coefficient is calculated.
"""

from __future__ import annotations

import json
import math
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from fire_data.eda_figures import COLORS
from fire_data.eda_spatial import EARTH_RADIUS_M, count_grid
from fire_data.monthly_scan import EXPECTED_ROWS, ZERO_ROW_MEANING
from fire_data.spatiotemporal_analysis import (
    DISPLAY,
    PROVENANCE,
    VIIRS_FLAGS,
    AnalysisError,
    ObservationTable,
    _confidence_counts,
    _peak_working_set,
    chord_limit_m,
    geodesic_m_from_chord,
    load_tables,
)

SATELLITES = ("Terra", "Aqua", "SNPP", "N20", "N21")
RADII_M = (375.0, 1_000.0, 2_000.0, 5_000.0)
WINDOWS_MIN = (0, 30, 180)
PRIMARY = (1_000.0, 30)
MAX_RADIUS_M = 5_000.0
MAX_WINDOW_MIN = 180
DISTANCE_EDGES = np.linspace(0.0, 5_000.0, 21)
SIZE_EDGES = np.array([1, 2, 5, 10, 50, 100, 1_000, 10_000, 1_000_000_000], dtype=np.int64)
FULL_SETTINGS = (
    {"eps_m": 375.0, "window_min": 30, "min_samples": 4, "role": "narrower_radius"},
    {"eps_m": 1_000.0, "window_min": 30, "min_samples": 4, "role": "primary"},
    {"eps_m": 2_000.0, "window_min": 30, "min_samples": 4, "role": "wider_radius"},
    {"eps_m": 1_000.0, "window_min": 0, "min_samples": 4, "role": "same_minute"},
    {"eps_m": 1_000.0, "window_min": 180, "min_samples": 4, "role": "wider_window"},
    {"eps_m": 1_000.0, "window_min": 30, "min_samples": 2, "role": "lower_min_samples"},
    {"eps_m": 1_000.0, "window_min": 30, "min_samples": 8, "role": "higher_min_samples"},
)
FACTORIAL_EPS_M = (375.0, 1_000.0, 2_000.0)
FACTORIAL_WINDOWS_MIN = (0, 30, 180)
FACTORIAL_MIN_SAMPLES = (2, 4, 8)
REPORT_JSON = Path(__file__).resolve().parents[1] / "reports" / "within_sensor_analysis_2024_07.json"
REPORT_MD = Path(__file__).resolve().parents[1] / "reports" / "within_sensor_analysis_2024_07.md"
FIGURE_DIR = Path(__file__).resolve().parents[1] / "reports" / "figures" / "within_sensor_2024_07"
MILESTONE_DIR = Path(__file__).resolve().parents[1] / "reports" / "milestones"
PAIR_BYTE_GUARD = 30_000_000

# Bounded probe on the busiest NOAA-20 date in the coverage table. It justified
# per-date graphs and ruled out dropping the 5 km radius. It is not a result.
PROBE = {
    "satellite": "N20",
    "date": "2024-07-25",
    "rows": 127_817,
    "csv_read_seconds": 2.59,
    "tree_build_seconds": 0.02,
    "query_k2_seconds": 0.064,
    "same_day_nearest_median_m": 379.64,
    "share_of_nearest_within_m": {"375": 0.480, "1000": 0.836, "5000": 0.921},
    "same_day_nearest_median_minutes": 0.0,
    "sparse_directed_pairs_including_diagonal_at_5km": 6_065_137,
    "sparse_seconds": 0.146,
    "sparse_bytes": 145_563_288,
    "degree_sample_size": 3_000,
    "degree_sample_seed": 7,
    "sample_mean_other_neighbors": {"375": 1.0, "1000": 6.93, "2000": 16.65, "5000": 45.16},
}

LIMITATIONS = (
    "A nearest neighbor, a neighborhood count, and a DBSCAN component describe archived rows. They are not confirmed physical fires.",
    "same_fire is not_assessed. No row is labeled as the same fire as another row.",
    "DBSCAN is fit separately on each UTC date. Rows from the adjacent date are included only when their clock falls inside the 180-minute midnight margin. Cluster counts from those partitions are not a month-long census and are not additive.",
    "Neighborhood counts stop at 5 km. The unrestricted same-day nearest neighbor is a separate k=2 query, so a neighbor beyond 5 km still has a distance.",
    "A 0-minute window is the archived acquisition minute. That is the clock resolution of these files, not proof of the same instant.",
    "Exact-duplicate counts in this report use the loaded analysis fields. They omit version, type, and bright_t31. The July temporal scan remains the full-line duplicate account: 0 extra full lines, and 5 extra location-time keys.",
    "Same coordinate means bit-identical float64 latitude and longitude after parsing the CSV. It is not a rounded cell.",
    "S-NPP dates with no delivered rows are left out. They are not zero detections and they are not filled from another sensor.",
    "Dates 16, 24, and 29 July are used only to the extent S-NPP rows are present. Partial delivery is not repaired.",
    PROVENANCE,
    "No harmonization coefficient is calculated. XGBoost is not trained.",
    "MODIS confidence stays on 0-100. VIIRS confidence stays l, n, or h. The two scales are not converted.",
    "FRP quantiles keep zero and negative values. No FRP filter is applied.",
)


def _date(day: int) -> str:
    return f"2024-07-{day:02d}"


def _bits(values: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.float64).view(np.uint64)


def _quantiles(values: np.ndarray) -> dict[str, float | int | None]:
    sample = np.asarray(values, dtype=np.float64)
    sample = sample[np.isfinite(sample)]
    if sample.size == 0:
        return {"count": 0, "p10": None, "p50": None, "p90": None, "min": None, "max": None}
    low, mid, high = np.quantile(sample, [0.1, 0.5, 0.9])
    return {
        "count": int(sample.size),
        "p10": float(low),
        "p50": float(mid),
        "p90": float(high),
        "min": float(sample.min()),
        "max": float(sample.max()),
    }


def _median_bin(values: np.ndarray, edges: np.ndarray) -> dict[str, float | int | None]:
    sample = np.asarray(values, dtype=np.float64)
    sample = sample[np.isfinite(sample)]
    if sample.size == 0:
        return {"count": 0, "bin_start": None, "bin_end": None}
    counts, _ = np.histogram(np.clip(sample, edges[0], edges[-1]), bins=edges)
    total = int(sample.size)
    cumulative = np.cumsum(counts)
    index = int(np.searchsorted(cumulative, (total + 1) // 2, side="left"))
    index = min(index, counts.size - 1)
    return {"count": total, "bin_start": float(edges[index]), "bin_end": float(edges[index + 1])}


def duplicate_inventory(table: ObservationTable) -> dict[str, object]:
    """Extra copies on the loaded fields. Nothing is removed."""

    empty = {"groups": 0, "extra_rows": 0, "rows_retained": int(table.count), "rows_removed": 0}
    if table.count < 2:
        return empty
    keys = np.empty(
        table.count,
        dtype=[
            ("day", np.int16),
            ("minute", np.int16),
            ("lat", np.uint64),
            ("lon", np.uint64),
            ("brightness", np.uint64),
            ("scan", np.uint64),
            ("track", np.uint64),
            ("frp", np.uint64),
            ("daynight", np.int16),
            ("confidence", np.int16),
        ],
    )
    keys["day"] = table.day
    keys["minute"] = table.minute
    keys["lat"] = _bits(table.latitude)
    keys["lon"] = _bits(table.longitude)
    keys["brightness"] = _bits(table.brightness)
    keys["scan"] = _bits(table.scan)
    keys["track"] = _bits(table.track)
    keys["frp"] = _bits(table.frp)
    keys["daynight"] = table.daynight
    keys["confidence"] = table.confidence
    _, counts = np.unique(keys, return_counts=True)
    repeated = counts[counts > 1]
    return {
        "groups": int(repeated.size),
        "extra_rows": int(np.sum(repeated - 1)) if repeated.size else 0,
        "rows_retained": int(table.count),
        "rows_removed": 0,
        "fields": [
            "acq_date",
            "acq_time",
            "latitude",
            "longitude",
            "brightness",
            "scan",
            "track",
            "frp",
            "daynight",
            "confidence",
        ],
        "omitted_fields": ["bright_t31", "version", "type", "satellite", "instrument"],
        "same_fire": "not_assessed",
    }


def coordinate_inventory(table: ObservationTable) -> dict[str, object]:
    """Bit-identical coordinates, split by whether the acquisition minute repeats."""

    base = {
        "same_coordinate_and_time_groups": 0,
        "same_coordinate_and_time_extra_rows": 0,
        "multi_epoch_locations": 0,
        "rows_at_multi_epoch_locations": 0,
        "max_epochs_at_one_coordinate": 0,
        "coordinate_identity": "float64 bits of parsed latitude and longitude",
        "same_fire": "not_assessed",
        "temporally_separated_means_same_fire": False,
    }
    count = table.count
    if count == 0:
        return base
    lat_bits = _bits(table.latitude)
    lon_bits = _bits(table.longitude)
    order = np.lexsort((table.epoch, lon_bits, lat_bits))
    lat_s = lat_bits[order]
    lon_s = lon_bits[order]
    epoch_s = table.epoch[order]
    coord_change = np.empty(count, dtype=bool)
    coord_change[0] = True
    if count > 1:
        coord_change[1:] = (lat_s[1:] != lat_s[:-1]) | (lon_s[1:] != lon_s[:-1])
    starts = np.flatnonzero(coord_change)
    ends = np.append(starts[1:], count)
    sizes = ends - starts
    epoch_change = np.empty(count, dtype=bool)
    epoch_change[0] = True
    if count > 1:
        epoch_change[1:] = epoch_s[1:] != epoch_s[:-1]
    # A new coordinate starts a new epoch even when the minute matches the previous coordinate.
    epoch_change[starts] = True
    distinct = np.add.reduceat(epoch_change.astype(np.int32), starts)
    same_time = (sizes > 1) & (distinct == 1)
    multi_epoch = distinct > 1
    base.update(
        {
            "same_coordinate_and_time_groups": int(np.count_nonzero(same_time)),
            "same_coordinate_and_time_extra_rows": int(np.sum(sizes[same_time] - 1)) if np.any(same_time) else 0,
            "multi_epoch_locations": int(np.count_nonzero(multi_epoch)),
            "rows_at_multi_epoch_locations": int(np.sum(sizes[multi_epoch])) if np.any(multi_epoch) else 0,
            "max_epochs_at_one_coordinate": int(distinct.max()) if distinct.size else 0,
        }
    )
    return base


def _group_days(table: ObservationTable) -> dict[int, np.ndarray]:
    if table.count == 0:
        return {}
    order = np.argsort(table.day, kind="mergesort")
    days = table.day[order]
    change = np.empty(days.size, dtype=bool)
    change[0] = True
    if days.size > 1:
        change[1:] = days[1:] != days[:-1]
    starts = np.flatnonzero(change)
    ends = np.append(starts[1:], days.size)
    return {int(days[start]): order[start:end] for start, end in zip(starts, ends, strict=True)}


def margin_indices(by_day: dict[int, np.ndarray], minute: np.ndarray, day: int, window_min: int) -> np.ndarray:
    """Adjacent-date rows that can fall inside ``window_min`` of this UTC date."""

    parts: list[np.ndarray] = []
    previous = by_day.get(day - 1)
    if previous is not None and previous.size:
        chosen = previous[minute[previous] >= 1440 - window_min]
        if chosen.size:
            parts.append(chosen)
    nxt = by_day.get(day + 1)
    if nxt is not None and nxt.size:
        chosen = nxt[minute[nxt] <= window_min]
        if chosen.size:
            parts.append(chosen)
    if not parts:
        return np.empty(0, dtype=np.int64)
    return np.concatenate(parts)


def directed_pairs(ecef: np.ndarray, epoch: np.ndarray, max_geodesic_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Directed pairs inside the radius, self pairs removed, one copy of each ordered pair."""

    count = int(len(epoch))
    empty = (
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.float64),
        np.empty(0, dtype=np.int32),
    )
    if count < 2 or max_geodesic_m <= 0:
        return empty
    found = cKDTree(ecef).sparse_distance_matrix(
        cKDTree(ecef),
        max_distance=chord_limit_m(max_geodesic_m),
        output_type="ndarray",
    )
    if found.size == 0:
        return empty
    left = found["i"].astype(np.int64, copy=False)
    right = found["j"].astype(np.int64, copy=False)
    keep = left != right
    if not np.any(keep):
        return empty
    left = left[keep]
    right = right[keep]
    distance = geodesic_m_from_chord(found["v"][keep])
    inside = distance <= max_geodesic_m + 1e-6
    left = left[inside]
    right = right[inside]
    distance = distance[inside]
    if left.size == 0:
        return empty
    if left.size > PAIR_BYTE_GUARD:
        raise AnalysisError(
            f"A date partition produced {left.size} pairs at {max_geodesic_m:.0f} m. "
            "The run stopped instead of dropping rows or widening the partition silently."
        )
    order = np.lexsort((distance, right, left))
    left = left[order]
    right = right[order]
    distance = distance[order]
    duplicate = np.zeros(left.size, dtype=bool)
    duplicate[1:] = (left[1:] == left[:-1]) & (right[1:] == right[:-1])
    left = left[~duplicate]
    right = right[~duplicate]
    distance = distance[~duplicate]
    delta = np.abs(epoch[left] - epoch[right]).astype(np.int32)
    return left, right, distance, delta


def nearest_other(ecef: np.ndarray, epoch: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unrestricted nearest other row in this array. Distance is great-circle metres.

    ``query(k=2)`` usually returns the row itself and then another row. Coincident
    coordinates can reverse that order, and a broken hit can repeat the same index.
    The nearest index that is not the row is kept. Only unresolved rows are queried
    again, with a wider ``k``.
    """

    count = int(len(epoch))
    distance = np.full(count, np.nan, dtype=np.float64)
    delta = np.full(count, np.nan, dtype=np.float64)
    if count < 2:
        return distance, delta
    tree = cKDTree(ecef)
    pending = np.arange(count, dtype=np.int64)
    width = 2
    while pending.size:
        width = min(count, width)
        chord, index = tree.query(ecef[pending], k=width)
        chord = np.asarray(chord, dtype=np.float64).reshape(pending.size, width)
        index = np.asarray(index, dtype=np.int64).reshape(pending.size, width)
        chosen_chord = np.full(pending.size, np.nan, dtype=np.float64)
        chosen_index = np.full(pending.size, -1, dtype=np.int64)
        for column in range(width):
            candidate = index[:, column]
            valid = (candidate != pending) & (candidate >= 0) & (candidate < count) & np.isfinite(chord[:, column])
            take = valid & ~np.isfinite(chosen_chord)
            chosen_chord[take] = chord[take, column]
            chosen_index[take] = candidate[take]
        found = np.isfinite(chosen_chord)
        rows = pending[found]
        distance[rows] = geodesic_m_from_chord(chosen_chord[found])
        delta[rows] = np.abs(epoch[rows] - epoch[chosen_index[found]])
        pending = pending[~found]
        if pending.size == 0:
            break
        if width == count:
            raise AnalysisError(f"Nearest-other query found no other row for {int(pending.size)} rows")
        width = min(count, max(width * 4, width + 1))
    return distance, delta


def _neighbor_count_bins(counts: np.ndarray) -> dict[str, int]:
    return {
        "0": int(np.count_nonzero(counts == 0)),
        "1": int(np.count_nonzero(counts == 1)),
        "2_to_5": int(np.count_nonzero((counts >= 2) & (counts <= 5))),
        "6_to_20": int(np.count_nonzero((counts >= 6) & (counts <= 20))),
        "21_or_more": int(np.count_nonzero(counts >= 21)),
    }


def _time_gap_bins(delta: np.ndarray) -> dict[str, int]:
    sample = np.asarray(delta, dtype=np.float64)
    sample = sample[np.isfinite(sample)]
    return {
        "0_same_minute": int(np.count_nonzero(sample == 0)),
        "1_to_30": int(np.count_nonzero((sample >= 1) & (sample <= 30))),
        "31_to_180": int(np.count_nonzero((sample >= 31) & (sample <= 180))),
        "181_to_720": int(np.count_nonzero((sample >= 181) & (sample <= 720))),
        "721_or_more": int(np.count_nonzero(sample >= 721)),
    }


def _distance_histogram(distance: np.ndarray) -> list[int]:
    sample = np.asarray(distance, dtype=np.float64)
    sample = sample[np.isfinite(sample) & (sample <= DISTANCE_EDGES[-1])]
    if sample.size == 0:
        return [0] * (DISTANCE_EDGES.size - 1)
    counts, _ = np.histogram(sample, bins=DISTANCE_EDGES)
    return [int(value) for value in counts]


def labels_from_pairs(
    count: int,
    left: np.ndarray,
    right: np.ndarray,
    distance: np.ndarray,
    delta: np.ndarray,
    *,
    eps_m: float,
    window_min: int,
    min_samples: int,
    border_tie_break: str = "smallest_core_index",
) -> np.ndarray:
    """DBSCAN labels. ``min_samples`` counts the point itself. -1 is noise.

    A border row joins one neighboring core component. The published tie-break
    chooses the component whose lowest core index is smallest. The alternate
    tie-break chooses the component whose highest core index is largest. Either
    label is an analytical component id, not a fire identifier.
    """

    if min_samples < 2:
        raise AnalysisError("min_samples includes the row itself and must be at least 2")
    if eps_m <= 0 or window_min < 0:
        raise AnalysisError("DBSCAN radius must be positive and the time window cannot be negative")
    labels = np.full(count, -1, dtype=np.int32)
    if count == 0:
        return labels
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
    else:
        endpoints_a = np.empty(0, dtype=np.int64)
        endpoints_b = np.empty(0, dtype=np.int64)
    if endpoints_a.size:
        degree = np.bincount(np.concatenate([endpoints_a, endpoints_b]), minlength=count)
    else:
        degree = np.zeros(count, dtype=np.int64)
    core = degree + 1 >= min_samples
    if not np.any(core):
        return labels
    if endpoints_a.size:
        core_edge = core[endpoints_a] & core[endpoints_b]
        core_a = endpoints_a[core_edge]
        core_b = endpoints_b[core_edge]
    else:
        core_a = np.empty(0, dtype=np.int64)
        core_b = np.empty(0, dtype=np.int64)
    if core_a.size:
        graph = coo_matrix(
            (
                np.ones(core_a.size * 2, dtype=np.uint8),
                (np.concatenate([core_a, core_b]), np.concatenate([core_b, core_a])),
            ),
            shape=(count, count),
        )
    else:
        graph = coo_matrix((count, count))
    _, components = connected_components(graph, directed=False, return_labels=True)
    labels[core] = components[core]
    if endpoints_a.size:
        border = (~core[endpoints_a] & core[endpoints_b]) | (core[endpoints_a] & ~core[endpoints_b])
        border_row = np.concatenate([endpoints_a[border & ~core[endpoints_a]], endpoints_b[border & ~core[endpoints_b]]])
        border_core = np.concatenate([endpoints_b[border & ~core[endpoints_a]], endpoints_a[border & ~core[endpoints_b]]])
    else:
        border_row = np.empty(0, dtype=np.int64)
        border_core = np.empty(0, dtype=np.int64)
    if border_row.size:
        core_index = np.flatnonzero(core)
        component_count = int(components.max()) + 1
        if border_tie_break == "smallest_core_index":
            score_by_component = np.full(component_count, count, dtype=np.int64)
            np.minimum.at(score_by_component, labels[core_index], core_index)
            score = score_by_component[labels[border_core]]
            order = np.lexsort((border_core, score, border_row))
        elif border_tie_break == "largest_core_index":
            score_by_component = np.full(component_count, -1, dtype=np.int64)
            np.maximum.at(score_by_component, labels[core_index], core_index)
            score = score_by_component[labels[border_core]]
            order = np.lexsort((-border_core, -score, border_row))
        else:
            raise AnalysisError("border_tie_break must be smallest_core_index or largest_core_index")
        border_row = border_row[order]
        border_core = border_core[order]
        first = np.ones(border_row.size, dtype=bool)
        first[1:] = border_row[1:] != border_row[:-1]
        labels[border_row[first]] = labels[border_core[first]]
    return labels


def dbscan_labels(
    ecef: np.ndarray,
    epoch: np.ndarray,
    *,
    eps_m: float,
    window_min: int,
    min_samples: int,
) -> np.ndarray:
    left, right, distance, delta = directed_pairs(ecef, epoch, max(eps_m, 1.0))
    return labels_from_pairs(
        int(len(epoch)),
        left,
        right,
        distance,
        delta,
        eps_m=eps_m,
        window_min=window_min,
        min_samples=min_samples,
    )


def summarize_labels(labels: np.ndarray, *, owned: int | None = None) -> dict[str, object]:
    """Summarize one partition. Cluster counts are not fire counts."""

    chosen = labels if owned is None else labels[:owned]
    noise = int(np.count_nonzero(chosen < 0))
    clustered_labels = chosen[chosen >= 0]
    if clustered_labels.size:
        _, sizes = np.unique(clustered_labels, return_counts=True)
        size_hist, _ = np.histogram(sizes, bins=SIZE_EDGES)
        summary = {
            "rows": int(chosen.size),
            "noise_rows": noise,
            "clustered_rows": int(clustered_labels.size),
            "partition_cluster_count": int(sizes.size),
            "max_owned_cluster_size": int(sizes.max()),
            "median_owned_cluster_size": float(np.median(sizes)),
            "size_histogram": [int(value) for value in size_hist],
        }
    else:
        summary = {
            "rows": int(chosen.size),
            "noise_rows": noise,
            "clustered_rows": 0,
            "partition_cluster_count": 0,
            "max_owned_cluster_size": 0,
            "median_owned_cluster_size": None,
            "size_histogram": [0] * (SIZE_EDGES.size - 1),
        }
    summary["same_fire"] = "not_assessed"
    summary["clusters_are_confirmed_fires"] = False
    summary["cluster_count_is_a_fire_count"] = False
    return summary


def _new_accumulator() -> dict[str, object]:
    return {
        "rows": 0,
        "noise_rows": 0,
        "clustered_rows": 0,
        "partition_cluster_count_sum": 0,
        "max_owned_cluster_size": 0,
        "size_histogram": np.zeros(SIZE_EDGES.size - 1, dtype=np.int64),
        "sizes": [],
        "dates_labeled": 0,
    }


def _add_summary(bucket: dict[str, object], summary: dict[str, object], sizes: np.ndarray) -> None:
    bucket["rows"] = int(bucket["rows"]) + int(summary["rows"])
    bucket["noise_rows"] = int(bucket["noise_rows"]) + int(summary["noise_rows"])
    bucket["clustered_rows"] = int(bucket["clustered_rows"]) + int(summary["clustered_rows"])
    bucket["partition_cluster_count_sum"] = int(bucket["partition_cluster_count_sum"]) + int(summary["partition_cluster_count"])
    bucket["max_owned_cluster_size"] = max(int(bucket["max_owned_cluster_size"]), int(summary["max_owned_cluster_size"]))
    bucket["size_histogram"] = bucket["size_histogram"] + np.asarray(summary["size_histogram"], dtype=np.int64)
    if sizes.size:
        bucket["sizes"].append(sizes)
    bucket["dates_labeled"] = int(bucket["dates_labeled"]) + 1


def _finish_accumulator(setting: dict[str, object], bucket: dict[str, object]) -> dict[str, object]:
    sizes = bucket["sizes"]
    if sizes:
        combined = np.concatenate(sizes)
        median = float(np.median(combined))
    else:
        median = None
    rows = int(bucket["rows"])
    return {
        "eps_m": setting["eps_m"],
        "window_min": setting["window_min"],
        "min_samples": setting["min_samples"],
        "role": setting.get("role", "factorial"),
        "rows": rows,
        "noise_rows": int(bucket["noise_rows"]),
        "clustered_rows": int(bucket["clustered_rows"]),
        "noise_share": None if rows == 0 else float(bucket["noise_rows"]) / rows,
        "partition_cluster_count_sum": int(bucket["partition_cluster_count_sum"]),
        "partition_cluster_count_is_additive": False,
        "max_owned_cluster_size": int(bucket["max_owned_cluster_size"]),
        "median_owned_cluster_size": median,
        "size_histogram": [int(value) for value in bucket["size_histogram"]],
        "size_histogram_edges": [int(value) for value in SIZE_EDGES],
        "dates_labeled": int(bucket["dates_labeled"]),
        "same_fire": "not_assessed",
        "clusters_are_confirmed_fires": False,
        "cluster_count_is_a_fire_count": False,
    }


def representative_day(table: ObservationTable) -> int | None:
    """Earliest UTC date whose row count is closest to the median of dates with rows."""

    counts = [(day, table.count_on(day)) for day in range(1, 32) if table.count_on(day) > 0]
    if not counts:
        return None
    target = float(np.median(np.array([count for _, count in counts], dtype=np.float64)))
    day, _ = min(counts, key=lambda item: (abs(item[1] - target), item[0]))
    return int(day)


def _characteristics(table: ObservationTable, mask: np.ndarray) -> dict[str, object]:
    if table.count == 0 or not np.any(mask):
        empty_q = _quantiles(np.empty(0))
        return {
            "rows": int(np.count_nonzero(mask)) if mask.size else 0,
            "frp": empty_q,
            "brightness": empty_q,
            "scan": empty_q,
            "track": empty_q,
            "nonpositive_frp_rows": 0,
            "day_rows": 0,
            "night_rows": 0,
            "confidence": {},
        }
    frp = table.frp[mask]
    return {
        "rows": int(np.count_nonzero(mask)),
        "frp": _quantiles(frp),
        "brightness": _quantiles(table.brightness[mask]),
        "scan": _quantiles(table.scan[mask]),
        "track": _quantiles(table.track[mask]),
        "nonpositive_frp_rows": int(np.count_nonzero(frp <= 0)),
        "day_rows": int(np.count_nonzero(table.daynight[mask] == 0)),
        "night_rows": int(np.count_nonzero(table.daynight[mask] == 1)),
        "confidence": _confidence_counts(table, mask),
    }


def spatial_profile(latitude: np.ndarray, longitude: np.ndarray) -> dict[str, object]:
    count = int(len(latitude))
    bands = []
    for south in range(-90, 90, 30):
        north = south + 30
        if north == 90:
            chosen = (latitude >= south) & (latitude <= north)
        else:
            chosen = (latitude >= south) & (latitude < north)
        bands.append({"south": south, "north": north, "rows": int(np.count_nonzero(chosen))})
    sectors = []
    for west in (-180, -90, 0, 90):
        east = west + 90
        if east == 180:
            chosen = (longitude >= west) & (longitude <= east)
        else:
            chosen = (longitude >= west) & (longitude < east)
        sectors.append({"west": west, "east": east, "rows": int(np.count_nonzero(chosen))})
    if count == 0:
        occupied = 0
        maximum = 0
    else:
        grid, _, _ = count_grid(latitude, longitude, 2.0)
        occupied = int(np.count_nonzero(grid))
        maximum = int(grid.max())
    return {
        "rows": count,
        "latitude": _quantiles(latitude),
        "occupied_2deg_cells": occupied,
        "max_2deg_cell_rows": maximum,
        "latitude_bands_30deg": bands,
        "longitude_sectors_90deg": sectors,
        "longitude_note": "Longitude sectors are cut at -180, -90, 0, and 90. The cut at ±180 splits the Pacific. A sector count is not a fire region.",
        "cells_are_not_equal_area": True,
        "same_fire": "not_assessed",
    }


def _owned_nearest_window(
    owned: int,
    left: np.ndarray,
    right: np.ndarray,
    distance: np.ndarray,
    delta: np.ndarray,
    window_min: int,
) -> tuple[np.ndarray, np.ndarray]:
    nearest_distance = np.full(owned, np.nan, dtype=np.float64)
    nearest_delta = np.full(owned, np.nan, dtype=np.float64)
    selected = (left < owned) & (delta <= window_min)
    if not np.any(selected):
        return nearest_distance, nearest_delta
    group = left[selected]
    dist = distance[selected]
    gap = delta[selected]
    partner = right[selected]
    order = np.lexsort((partner, gap, dist, group))
    group = group[order]
    dist = dist[order]
    gap = gap[order]
    first = np.ones(group.size, dtype=bool)
    first[1:] = group[1:] != group[:-1]
    nearest_distance[group[first]] = dist[first]
    nearest_delta[group[first]] = gap[first]
    return nearest_distance, nearest_delta


def analyze_sensor(table: ObservationTable, *, common_days: list[int]) -> dict[str, object]:
    """One satellite. Dates with no rows stay null and are not added as zeros."""

    started = perf_counter()
    by_day = _group_days(table)
    present = [day for day in range(1, 32) if day in by_day]
    absent = [_date(day) for day in range(1, 32) if day not in by_day]
    primary_counts = np.zeros(table.count, dtype=np.int32)
    same_distance = np.full(table.count, np.nan, dtype=np.float64)
    same_delta = np.full(table.count, np.nan, dtype=np.float64)
    window_counts = {(radius, window): np.zeros(table.count, dtype=np.int32) for radius in RADII_M for window in WINDOWS_MIN}
    window_distance = {(radius, window): np.full(table.count, np.nan) for radius in RADII_M for window in WINDOWS_MIN}
    next_within = {radius: np.zeros(table.count, dtype=bool) for radius in (1_000.0, 5_000.0)}
    next_eligible = np.zeros(table.count, dtype=bool)
    excluded_gap_rows = 0
    excluded_outside_rows = 0
    accumulators = [_new_accumulator() for _ in FULL_SETTINGS]
    factorial: list[dict[str, object]] = []
    chosen_day = representative_day(table)
    daily = []
    for day in range(1, 32):
        owned = by_day.get(day)
        if owned is None:
            daily.append(
                {
                    "date": _date(day),
                    "status": "no_rows_delivered",
                    "rows": None,
                    "zero_detections": False,
                    "meaning": ZERO_ROW_MEANING,
                    "share_with_neighbor_1km_30min": None,
                    "dbscan_primary": None,
                }
            )
            continue
        margin = margin_indices(by_day, table.minute, day, MAX_WINDOW_MIN)
        block = np.concatenate([owned, margin]) if margin.size else owned
        owned_count = int(owned.size)
        same_distance[owned], same_delta[owned] = nearest_other(table.ecef[owned], table.epoch[owned])
        left, right, distance, delta = directed_pairs(table.ecef[block], table.epoch[block], MAX_RADIUS_M)
        for radius in RADII_M:
            for window in WINDOWS_MIN:
                selected = (left < owned_count) & (distance <= radius) & (delta <= window)
                counts = window_counts[(radius, window)]
                if np.any(selected):
                    counts[owned] = np.bincount(left[selected], minlength=owned_count)
                nearest_d, _ = _owned_nearest_window(owned_count, left, right, distance, delta, window)
                # A larger radius must not keep a neighbor outside this radius.
                nearest_d[~(np.isnan(nearest_d) | (nearest_d <= radius))] = np.nan
                window_distance[(radius, window)][owned] = nearest_d
        primary_counts[owned] = window_counts[PRIMARY][owned]
        labels_primary = None
        for setting, bucket in zip(FULL_SETTINGS, accumulators, strict=True):
            labels = labels_from_pairs(
                int(block.size),
                left,
                right,
                distance,
                delta,
                eps_m=float(setting["eps_m"]),
                window_min=int(setting["window_min"]),
                min_samples=int(setting["min_samples"]),
            )
            summary = summarize_labels(labels, owned=owned_count)
            clustered = labels[:owned_count]
            clustered = clustered[clustered >= 0]
            sizes = np.unique(clustered, return_counts=True)[1] if clustered.size else np.empty(0, dtype=np.int64)
            _add_summary(bucket, summary, sizes)
            if setting["role"] == "primary":
                labels_primary = summary
        if day == chosen_day:
            for eps in FACTORIAL_EPS_M:
                for window in FACTORIAL_WINDOWS_MIN:
                    for minimum in FACTORIAL_MIN_SAMPLES:
                        labels = labels_from_pairs(
                            int(block.size),
                            left,
                            right,
                            distance,
                            delta,
                            eps_m=float(eps),
                            window_min=int(window),
                            min_samples=int(minimum),
                        )
                        item = summarize_labels(labels, owned=owned_count)
                        item.update({"eps_m": float(eps), "window_min": int(window), "min_samples": int(minimum), "date": _date(day)})
                        factorial.append(item)
        nxt = by_day.get(day + 1)
        next_record: dict[str, object]
        if day == 31:
            excluded_outside_rows += owned_count
            next_record = {
                "status": "next_date_outside_period",
                "rows_with_next_date_neighbor_1km": None,
                "rows_with_next_date_neighbor_5km": None,
                "zero_detections": False,
                "meaning": "1 August 2024 is outside this July extract. It is not a zero-detection date.",
            }
        elif nxt is None:
            excluded_gap_rows += owned_count
            next_record = {
                "status": "next_date_has_no_rows",
                "rows_with_next_date_neighbor_1km": None,
                "rows_with_next_date_neighbor_5km": None,
                "zero_detections": False,
                "meaning": ZERO_ROW_MEANING,
            }
        else:
            next_eligible[owned] = True
            chord, _index = cKDTree(table.ecef[nxt]).query(
                table.ecef[owned],
                k=1,
                distance_upper_bound=chord_limit_m(MAX_RADIUS_M),
            )
            finite = np.isfinite(chord)
            geo = np.full(owned_count, np.nan, dtype=np.float64)
            geo[finite] = geodesic_m_from_chord(np.asarray(chord, dtype=np.float64)[finite])
            next_within[1_000.0][owned] = finite & (geo <= 1_000.0)
            next_within[5_000.0][owned] = finite & (geo <= 5_000.0)
            next_record = {
                "status": "compared",
                "rows_with_next_date_neighbor_1km": int(np.count_nonzero(next_within[1_000.0][owned])),
                "rows_with_next_date_neighbor_5km": int(np.count_nonzero(next_within[5_000.0][owned])),
                "zero_detections": False,
            }
        share = None if owned_count == 0 else float(np.count_nonzero(primary_counts[owned] > 0)) / owned_count
        daily.append(
            {
                "date": _date(day),
                "status": "rows_delivered",
                "rows": owned_count,
                "zero_detections": False,
                "meaning": "The source CSV contains this many rows with this acquisition date.",
                "share_with_neighbor_1km_30min": share,
                "dbscan_primary": labels_primary,
                "next_date": next_record,
            }
        )
    neighborhoods = []
    for radius in RADII_M:
        for window in WINDOWS_MIN:
            counts = window_counts[(radius, window)]
            nearest = window_distance[(radius, window)]
            neighborhoods.append(
                {
                    "radius_m": radius,
                    "max_delta_minutes": window,
                    "rows_with_neighbor": int(np.count_nonzero(counts > 0)),
                    "rows_without_neighbor": int(np.count_nonzero(counts == 0)),
                    "neighbor_count_bins": _neighbor_count_bins(counts),
                    "nearest_distance": _quantiles(nearest),
                    "nearest_distance_histogram": _distance_histogram(nearest),
                    "nearest_distance_median_bin": _median_bin(nearest, DISTANCE_EDGES),
                    "same_fire": "not_assessed",
                    "neighbor_is_same_fire": False,
                }
            )
    eligible = int(np.count_nonzero(next_eligible))
    isolated = primary_counts == 0
    common_mask = np.isin(table.day, np.asarray(common_days, dtype=np.int8)) if common_days else np.zeros(table.count, dtype=bool)
    beyond = int(np.count_nonzero(np.isfinite(same_distance) & (same_distance > MAX_RADIUS_M)))
    sensor = {
        "satellite": table.satellite,
        "instrument": table.instrument,
        "display": DISPLAY.get(table.satellite, table.satellite),
        "confidence_scale": table.confidence_scale,
        "rows": int(table.count),
        "rows_removed": 0,
        "same_fire": "not_assessed",
        "dates_with_rows": [_date(day) for day in present],
        "dates_without_rows": absent,
        "dates_without_rows_are_zero_detections": False,
        "duplicates": duplicate_inventory(table),
        "coordinates": coordinate_inventory(table),
        "same_day_nearest": {
            "rows_with_neighbor": int(np.count_nonzero(np.isfinite(same_distance))),
            "rows_without_neighbor": int(np.count_nonzero(~np.isfinite(same_distance))),
            "distance": _quantiles(same_distance),
            "distance_histogram_to_5km": _distance_histogram(same_distance),
            "beyond_5km": beyond,
            "time_gap_bins": _time_gap_bins(same_delta),
            "same_fire": "not_assessed",
            "nearest_neighbor_is_same_fire": False,
        },
        "neighborhoods": neighborhoods,
        "next_date_neighbor": {
            "eligible_rows": eligible,
            "excluded_because_next_date_has_no_rows": excluded_gap_rows,
            "excluded_because_next_date_is_outside_july": excluded_outside_rows,
            "within_1km": int(np.count_nonzero(next_within[1_000.0])),
            "within_5km": int(np.count_nonzero(next_within[5_000.0])),
            "search_cap_m": MAX_RADIUS_M,
            "zero_detections": False,
            "same_fire": "not_assessed",
            "next_date_neighbor_is_same_fire": False,
        },
        "characteristics": {
            "definition": "Neighborhood rows have at least one other row of this satellite inside 1 km and 30 minutes. Isolated rows do not. Isolation is not absence of fire.",
            "all": _characteristics(table, np.ones(table.count, dtype=bool)),
            "isolated_1km_30min": _characteristics(table, isolated),
            "neighborhood_1km_30min": _characteristics(table, ~isolated),
            "same_fire": "not_assessed",
        },
        "spatial_all_delivered_dates": spatial_profile(table.latitude, table.longitude),
        "spatial_on_dates_with_all_five_sensors": spatial_profile(table.latitude[common_mask], table.longitude[common_mask]),
        "dbscan_full_coverage": [_finish_accumulator(setting, bucket) for setting, bucket in zip(FULL_SETTINGS, accumulators, strict=True)],
        "dbscan_representative_day": {
            "date": None if chosen_day is None else _date(chosen_day),
            "rows": 0 if chosen_day is None else int(by_day[chosen_day].size),
            "selection": "Earliest UTC date whose delivered-row count is closest to the median count among dates that have rows.",
            "factorial": factorial,
            "same_fire": "not_assessed",
            "clusters_are_confirmed_fires": False,
        },
        "daily": daily,
        "seconds": perf_counter() - started,
    }
    return sensor


def _expected_counts(tables: dict[str, ObservationTable]) -> None:
    checks = {
        "modis": tables["Terra"].count + tables["Aqua"].count,
        "viirs_snpp": tables["SNPP"].count,
        "viirs_noaa20": tables["N20"].count,
        "viirs_noaa21": tables["N21"].count,
    }
    for sensor, count in checks.items():
        expected = int(EXPECTED_ROWS[sensor])
        if count != expected:
            raise AnalysisError(f"{sensor} has {count} rows; the ingestion manifest records {expected}")


def build_report(tables: dict[str, ObservationTable], *, load_seconds: float, started: float) -> dict[str, object]:
    _expected_counts(tables)
    common = [day for day in range(1, 32) if all(tables[name].count_on(day) > 0 for name in SATELLITES)]
    sensors = []
    for name in SATELLITES:
        print(f"sensor={name} rows={tables[name].count}", flush=True)
        sensors.append(analyze_sensor(tables[name], common_days=common))
        print(f"sensor={name} seconds={sensors[-1]['seconds']:.1f}", flush=True)
    current, peak = tracemalloc.get_traced_memory()
    return {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "dataset": "NASA FIRMS July 2024 monthly extracts",
        "satellites": list(SATELLITES),
        "rows": int(sum(tables[name].count for name in SATELLITES)),
        "same_fire": "not_assessed",
        "harmonization_coefficient": None,
        "modis_to_viirs_scaling_factor": None,
        "xgboost_trained": False,
        "h3_aggregation": False,
        "parameters": {
            "radii_m": list(RADII_M),
            "windows_min": list(WINDOWS_MIN),
            "primary_radius_m": PRIMARY[0],
            "primary_window_minutes": PRIMARY[1],
            "max_radius_m": MAX_RADIUS_M,
            "midnight_margin_minutes": MAX_WINDOW_MIN,
            "dbscan_full_coverage": list(FULL_SETTINGS),
            "dbscan_factorial_on_representative_day": {
                "eps_m": list(FACTORIAL_EPS_M),
                "windows_min": list(FACTORIAL_WINDOWS_MIN),
                "min_samples": list(FACTORIAL_MIN_SAMPLES),
            },
            "earth_radius_m": EARTH_RADIUS_M,
            "index": "scipy.spatial.cKDTree on ECEF coordinates",
            "separation": "great-circle length recovered from the ECEF chord",
            "dbscan": "Core points are connected components. min_samples includes the row. Border rows take the core component with the smallest core index.",
            "partition": "One UTC date, plus the 180-minute midnight margin from the adjacent dates.",
        },
        "dates_with_rows_in_every_sensor": [_date(day) for day in common],
        "probe_that_set_the_partition": PROBE,
        "limitations": list(LIMITATIONS),
        "processing_level": PROVENANCE,
        "sensors": sensors,
        "consistency_checks": [],
        "performance": {
            "load_seconds": load_seconds,
            "analysis_seconds": perf_counter() - started,
            "peak_python_bytes": int(peak),
            "current_python_bytes": int(current),
            "peak_working_set_bytes": _peak_working_set(),
        },
    }


def consistency_checks(report: dict[str, object]) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("same_fire", report.get("same_fire") == "not_assessed", str(report.get("same_fire")))
    add("no_harmonization_coefficient", report.get("harmonization_coefficient") is None, "null")
    add("xgboost_not_trained", report.get("xgboost_trained") is False, "false")
    expected = {
        "Terra": None,
        "Aqua": None,
        "SNPP": int(EXPECTED_ROWS["viirs_snpp"]),
        "N20": int(EXPECTED_ROWS["viirs_noaa20"]),
        "N21": int(EXPECTED_ROWS["viirs_noaa21"]),
    }
    modis_rows = 0
    for sensor in report["sensors"]:
        name = sensor["satellite"]
        add(f"{name}_rows_removed", sensor["rows_removed"] == 0, str(sensor["rows_removed"]))
        add(f"{name}_same_fire", sensor["same_fire"] == "not_assessed", sensor["same_fire"])
        delivered = sum(int(day["rows"]) for day in sensor["daily"] if day["rows"] is not None)
        add(f"{name}_daily_sums_to_rows", delivered == sensor["rows"], f"{delivered} vs {sensor['rows']}")
        isolated = sensor["characteristics"]["isolated_1km_30min"]["rows"]
        neighborhood = sensor["characteristics"]["neighborhood_1km_30min"]["rows"]
        add(f"{name}_isolation_partition", isolated + neighborhood == sensor["rows"], f"{isolated}+{neighborhood}")
        for item in sensor["dbscan_full_coverage"]:
            total = item["noise_rows"] + item["clustered_rows"]
            add(
                f"{name}_dbscan_{int(item['eps_m'])}_{item['window_min']}_{item['min_samples']}",
                total == sensor["rows"] and item["clusters_are_confirmed_fires"] is False,
                f"{total} vs {sensor['rows']}",
            )
        null_dates = [day["date"] for day in sensor["daily"] if day["rows"] is None]
        add(
            f"{name}_absent_dates_are_null",
            null_dates == sensor["dates_without_rows"] and all(day["zero_detections"] is False for day in sensor["daily"]),
            ",".join(null_dates) if null_dates else "none",
        )
        if name in {"Terra", "Aqua"}:
            modis_rows += int(sensor["rows"])
        elif expected[name] is not None:
            add(f"{name}_matches_manifest", sensor["rows"] == expected[name], str(sensor["rows"]))
    add("modis_matches_manifest", modis_rows == int(EXPECTED_ROWS["modis"]), str(modis_rows))
    snpp = next(sensor for sensor in report["sensors"] if sensor["satellite"] == "SNPP")
    known_gaps = [f"2024-07-{day:02d}" for day in (10, 11, 12, 13, 14, 15, 25, 26, 27, 28)]
    add(
        "snpp_known_empty_dates_stay_null",
        all(day in snpp["dates_without_rows"] for day in known_gaps) and all(day not in snpp["dates_with_rows"] for day in known_gaps),
        str(len(snpp["dates_without_rows"])),
    )
    return checks


def _plain(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, np.floating):
        if not np.isfinite(value):
            return None
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _count(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{int(value):,}"


def _pct(part: object, whole: object) -> str:
    if part is None or whole in (None, 0):
        return "n/a"
    return f"{100.0 * float(part) / float(whole):.1f}%"


def _num(value: object, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Within-sensor spatial-temporal analysis, July 2024",
        "",
        "This report describes archived rows inside each satellite. A nearest neighbor is not a confirmed fire. A DBSCAN component is not a confirmed fire. `same_fire` is `not_assessed`.",
        "",
        "## Method",
        "",
        "The five satellites are Terra, Aqua, S-NPP, NOAA-20, and NOAA-21. Terra and Aqua stay separate. Distances are great-circle lengths on the same sphere used for the earlier candidate-pair index. The search structure is a `cKDTree` of Earth-centered coordinates.",
        "",
        "Each UTC date is a partition. The unrestricted same-day nearest neighbor comes from a k-nearest query. The nearest returned index that is not the row itself is kept. k starts at 2 and widens only for rows whose returned indexes are all themselves. Neighborhood counts use pairs inside 5 km. A 180-minute margin from the previous and next dates is available to the windowed counts and to DBSCAN, and those margin rows are not counted a second time as reference rows.",
        "",
        "The windows are 0, 30, and 180 minutes. Zero minutes means the same archived `acq_time`. The radii are 375 m, 1 km, 2 km, and 5 km. The characteristic split uses 1 km and 30 minutes: a row is in a neighborhood when at least one other row of the same satellite falls inside both limits.",
        "",
        "DBSCAN uses that same neighborhood. `min_samples` includes the row. Core rows form connected components. A border row is assigned to the neighboring component whose lowest core index is smallest. The full month uses seven settings around 1 km, 30 minutes, and `min_samples` 4. The 27-cell factorial is limited to one representative date per satellite: the earliest date whose row count is closest to the median of dates that contain rows. Every delivered row is still labeled in the seven-setting pass. Empty dates are not given a cluster count of zero.",
        "",
        "A next-date neighbor is the closest row of the same satellite on the following UTC date, capped at 5 km. If that date has no rows, the comparison is null. It is not a zero.",
        "",
        PROVENANCE,
        "",
        "No harmonization coefficient is calculated. XGBoost is not trained. Original rows are retained.",
        "",
        "## Coverage",
        "",
        f"Rows analyzed: {_count(report['rows'])}.",
        "",
        "Dates with at least one row in every sensor: " + ", ".join(report["dates_with_rows_in_every_sensor"]) + ".",
        "",
        "| Satellite | Rows | Dates with rows | Dates without rows | Exact extra rows | Same coordinate and time, extra | Multi-epoch coordinates |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for sensor in report["sensors"]:
        lines.append(
            "| {display} | {rows} | {present} | {absent} | {exact} | {same} | {multi} |".format(
                display=sensor["display"],
                rows=_count(sensor["rows"]),
                present=len(sensor["dates_with_rows"]),
                absent=len(sensor["dates_without_rows"]),
                exact=_count(sensor["duplicates"]["extra_rows"]),
                same=_count(sensor["coordinates"]["same_coordinate_and_time_extra_rows"]),
                multi=_count(sensor["coordinates"]["multi_epoch_locations"]),
            )
        )
    lines.extend(
        [
            "",
            "Dates without rows are omitted from rates. S-NPP dates without rows are not zero detections.",
            "",
            "## Same-day nearest neighbor",
            "",
            "This neighbor can fall at any distance and any time on the same UTC date. The time gap is the absolute difference of archived minutes.",
            "",
            "| Satellite | With a neighbor | Without | Median distance (m) | Beyond 5 km | Same minute | 1–30 min | 31–180 min | More than 180 min |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in report["sensors"]:
        nearest = sensor["same_day_nearest"]
        gaps = nearest["time_gap_bins"]
        longer = gaps["181_to_720"] + gaps["721_or_more"]
        lines.append(
            "| {name} | {with_n} | {without} | {median} | {beyond} | {same} | {short} | {mid} | {long} |".format(
                name=sensor["display"],
                with_n=_count(nearest["rows_with_neighbor"]),
                without=_count(nearest["rows_without_neighbor"]),
                median=_num(nearest["distance"]["p50"], 1),
                beyond=_count(nearest["beyond_5km"]),
                same=_count(gaps["0_same_minute"]),
                short=_count(gaps["1_to_30"]),
                mid=_count(gaps["31_to_180"]),
                long=_count(longer),
            )
        )
    lines.extend(
        [
            "",
            "## Neighborhoods inside a radius and a time window",
            "",
            "A row with a neighbor is not a fire match. Counts exclude the row itself.",
            "",
            "| Satellite | Radius (m) | Window (min) | With neighbor | Without | Share | Median nearest distance (m) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in report["sensors"]:
        for item in sensor["neighborhoods"]:
            if item["max_delta_minutes"] not in (0, 30) or item["radius_m"] not in (375.0, 1_000.0, 5_000.0):
                continue
            lines.append(
                "| {name} | {radius:.0f} | {window} | {yes} | {no} | {share} | {median} |".format(
                    name=sensor["display"],
                    radius=item["radius_m"],
                    window=item["max_delta_minutes"],
                    yes=_count(item["rows_with_neighbor"]),
                    no=_count(item["rows_without_neighbor"]),
                    share=_pct(item["rows_with_neighbor"], sensor["rows"]),
                    median=_num(item["nearest_distance"]["p50"], 1),
                )
            )
    lines.extend(
        [
            "",
            "The JSON report contains the 2 km radius and the 180-minute window as well.",
            "",
            "## Next UTC date, capped at 5 km",
            "",
            "July 31 is excluded because 1 August is outside this extract. That exclusion is not a zero-detection day. Other exclusions are dates whose next July date has no delivered rows.",
            "",
            "| Satellite | Eligible rows | Next July date has no rows | Next date outside July | Within 1 km | Within 5 km |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in report["sensors"]:
        item = sensor["next_date_neighbor"]
        lines.append(
            "| {name} | {eligible} | {gap} | {outside} | {near} | {far} |".format(
                name=sensor["display"],
                eligible=_count(item["eligible_rows"]),
                gap=_count(item["excluded_because_next_date_has_no_rows"]),
                outside=_count(item["excluded_because_next_date_is_outside_july"]),
                near=_count(item["within_1km"]),
                far=_count(item["within_5km"]),
            )
        )
    lines.extend(
        [
            "",
            "## Characteristics at 1 km and 30 minutes",
            "",
            "Quantiles include non-positive FRP. VIIRS confidence is the native flag. MODIS confidence is the native 0–100 value.",
            "",
            "| Satellite | Group | Rows | FRP p50 | Brightness p50 | Scan p50 | Track p50 | Day | Night |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in report["sensors"]:
        for key, label in (
            ("all", "All delivered rows"),
            ("isolated_1km_30min", "No neighbor inside 1 km and 30 min"),
            ("neighborhood_1km_30min", "Neighbor inside 1 km and 30 min"),
        ):
            item = sensor["characteristics"][key]
            lines.append(
                "| {name} | {label} | {rows} | {frp} | {bright} | {scan} | {track} | {day} | {night} |".format(
                    name=sensor["display"],
                    label=label,
                    rows=_count(item["rows"]),
                    frp=_num(item["frp"]["p50"], 2),
                    bright=_num(item["brightness"]["p50"], 2),
                    scan=_num(item["scan"]["p50"], 2),
                    track=_num(item["track"]["p50"], 2),
                    day=_count(item["day_rows"]),
                    night=_count(item["night_rows"]),
                )
            )
    lines.extend(["", "### Native confidence", ""])
    for sensor in report["sensors"]:
        lines.append(f"{sensor['display']} ({sensor['confidence_scale']}):")
        for key, label in (
            ("all", "all"),
            ("isolated_1km_30min", "isolated"),
            ("neighborhood_1km_30min", "neighborhood"),
        ):
            counts = sensor["characteristics"][key]["confidence"]
            rendered = ", ".join(f"{flag} {_count(counts[flag])}" for flag in counts) if counts else "n/a"
            lines.append(f"- {label}: {rendered}")
        lines.append("")
    lines.extend(
        [
            "## Spatial distribution",
            "",
            "The common-date columns use only UTC dates on which Terra, Aqua, S-NPP, NOAA-20, and NOAA-21 each have at least one row. Empty S-NPP dates do not enter that comparison as zeros.",
            "",
            "| Satellite | Occupied 2° cells, all delivered dates | Max cell | Occupied 2° cells, common dates | Common-date rows | Latitude p50 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in report["sensors"]:
        whole = sensor["spatial_all_delivered_dates"]
        shared = sensor["spatial_on_dates_with_all_five_sensors"]
        lines.append(
            f"| {sensor['display']} | {_count(whole['occupied_2deg_cells'])} | {_count(whole['max_2deg_cell_rows'])} | {_count(shared['occupied_2deg_cells'])} | {_count(shared['rows'])} | {_num(whole['latitude']['p50'], 2)} |"
        )
    lines.extend(
        [
            "",
            "Equal-degree cells are not equal-area cells. Longitude is summarized in 90° sectors in the JSON file. Those sectors are cut at ±180 and are not fire regions.",
            "",
            "## DBSCAN",
            "",
            "Noise share below uses every delivered row once. The sum of partition cluster counts is shown only as a partition total. It is not a count of fires and it is not additive across dates.",
            "",
            "| Satellite | Setting | Noise rows | Noise share | Partition cluster-count sum | Median owned size | Max owned size |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in report["sensors"]:
        for item in sensor["dbscan_full_coverage"]:
            label = f"{item['eps_m']:.0f} m, {item['window_min']} min, min {item['min_samples']}"
            lines.append(
                f"| {sensor['display']} | {label} | {_count(item['noise_rows'])} | {_pct(item['noise_rows'], item['rows'])} | {_count(item['partition_cluster_count_sum'])} | {_num(item['median_owned_cluster_size'], 1)} | {_count(item['max_owned_cluster_size'])} |"
            )
    lines.extend(
        [
            "",
            "### Representative-date factorial",
            "",
            "Each column is that sensor's own representative date. The dates are not required to match.",
            "",
        ]
    )
    header = "| eps (m) | window | min_samples | " + " | ".join(sensor["display"] for sensor in report["sensors"]) + " |"
    align = "| ---: | ---: | ---: | " + " | ".join("---:" for _ in report["sensors"]) + " |"
    lines.extend([header, align])
    factorial = report["sensors"][0]["dbscan_representative_day"]["factorial"]
    for index, base in enumerate(factorial):
        shares = []
        for sensor in report["sensors"]:
            item = sensor["dbscan_representative_day"]["factorial"][index]
            shares.append(_pct(item["noise_rows"], item["rows"]))
        lines.append(
            f"| {base['eps_m']:.0f} | {base['window_min']} | {base['min_samples']} | " + " | ".join(shares) + " |"
        )
    lines.extend(["", "Representative dates:", ""])
    for sensor in report["sensors"]:
        chosen = sensor["dbscan_representative_day"]
        lines.append(f"- {sensor['display']}: {chosen['date']} ({_count(chosen['rows'])} rows)")
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "From `backend`, with the July CSVs already extracted under `data/raw/monthly_2024_07/`:",
            "",
            "```bash",
            ".venv\\Scripts\\python -m fire_data.within_sensor_analysis",
            ".venv\\Scripts\\python -m pytest",
            "```",
            "",
            "The CSVs stay gitignored. This command does not modify them.",
            "",
        ]
    )
    return "\n".join(lines)


def _finish(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=140)
    plt.close(fig)


def write_figures(report: dict[str, object], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = [
        _figure_nearest(report, output_dir / "same_day_nearest_distance.png"),
        _figure_time_gaps(report, output_dir / "same_day_nearest_time_gap.png"),
        _figure_neighborhood(report, output_dir / "neighborhood_share_by_radius.png"),
        _figure_next_date(report, output_dir / "next_date_neighbor_share.png"),
        _figure_frp(report, output_dir / "frp_median_isolated_vs_neighborhood.png"),
        _figure_dbscan(report, output_dir / "dbscan_noise_share.png"),
        _figure_latitude(report, output_dir / "latitude_band_shares.png"),
        _figure_daynight(report, output_dir / "daynight_by_neighborhood.png"),
    ]
    return [path.name for path in written]


def _figure_nearest(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 4.8), constrained_layout=True)
    centers = (DISTANCE_EDGES[:-1] + DISTANCE_EDGES[1:]) / 2.0
    for sensor in report["sensors"]:
        hist = np.asarray(sensor["same_day_nearest"]["distance_histogram_to_5km"], dtype=float)
        total = hist.sum()
        share = hist / total if total else hist
        ax.plot(centers, share, color=COLORS[sensor["satellite"]], label=sensor["display"], linewidth=1.4)
    ax.set_xlabel("Same-day nearest other row (m)")
    ax.set_ylabel("Share of neighbors inside 5 km")
    ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def _figure_time_gaps(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    keys = ("0_same_minute", "1_to_30", "31_to_180", "181_to_720", "721_or_more")
    labels = ("Same minute", "1–30 min", "31–180 min", "3–12 h", "More than 12 h")
    colors = ("#8c4a2f", "#c4894f", "#2f6f8f", "#3d8b7a", "#5c4d7a")
    bottoms = np.zeros(len(report["sensors"]))
    for key, label, color in zip(keys, labels, colors, strict=True):
        values = []
        for sensor in report["sensors"]:
            gaps = sensor["same_day_nearest"]["time_gap_bins"]
            total = sum(gaps.values()) or 1
            values.append(gaps[key] / total)
        ax.bar(np.arange(len(values)), values, bottom=bottoms, color=color, label=label)
        bottoms += np.asarray(values)
    ax.set_xticks(np.arange(len(report["sensors"])), [sensor["display"] for sensor in report["sensors"]], rotation=20, ha="right")
    ax.set_ylabel("Share of same-day nearest neighbors")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    _finish(fig, path)
    return path


def _figure_neighborhood(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.4, 4.8), constrained_layout=True)
    for sensor in report["sensors"]:
        rows = [item for item in sensor["neighborhoods"] if item["max_delta_minutes"] == 30]
        share = [item["rows_with_neighbor"] / sensor["rows"] if sensor["rows"] else np.nan for item in rows]
        ax.plot([item["radius_m"] for item in rows], share, marker="o", color=COLORS[sensor["satellite"]], label=sensor["display"])
    ax.set_xlabel("Radius (m)")
    ax.set_ylabel("Share of rows with another row inside 30 minutes")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def _figure_next_date(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 4.6), constrained_layout=True)
    names = [sensor["display"] for sensor in report["sensors"]]
    share_1 = []
    share_5 = []
    for sensor in report["sensors"]:
        item = sensor["next_date_neighbor"]
        eligible = item["eligible_rows"] or 1
        share_1.append(item["within_1km"] / eligible)
        share_5.append(item["within_5km"] / eligible)
    positions = np.arange(len(names))
    ax.bar(positions - 0.18, share_1, width=0.36, color="#8c4a2f", label="Within 1 km")
    ax.bar(positions + 0.18, share_5, width=0.36, color="#2f6f8f", label="Within 5 km")
    ax.set_xticks(positions, names, rotation=20, ha="right")
    ax.set_ylabel("Share of rows whose next date has rows")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def _figure_frp(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 4.8), constrained_layout=True)
    names = [sensor["display"] for sensor in report["sensors"]]
    isolated = [np.nan if sensor["characteristics"]["isolated_1km_30min"]["frp"]["p50"] is None else sensor["characteristics"]["isolated_1km_30min"]["frp"]["p50"] for sensor in report["sensors"]]
    neighborhood = [np.nan if sensor["characteristics"]["neighborhood_1km_30min"]["frp"]["p50"] is None else sensor["characteristics"]["neighborhood_1km_30min"]["frp"]["p50"] for sensor in report["sensors"]]
    positions = np.arange(len(names))
    ax.bar(positions - 0.18, isolated, width=0.36, color="#d9d0c7", label="No neighbor in 1 km and 30 min")
    ax.bar(positions + 0.18, neighborhood, width=0.36, color="#8c4a2f", label="Neighbor in 1 km and 30 min")
    ax.set_xticks(positions, names, rotation=20, ha="right")
    ax.set_ylabel("FRP median (MW)")
    ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def _figure_dbscan(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10.4, 5.0), constrained_layout=True)
    settings = report["sensors"][0]["dbscan_full_coverage"]
    positions = np.arange(len(settings))
    width = 0.15
    for offset, sensor in enumerate(report["sensors"]):
        shares = [item["noise_share"] for item in sensor["dbscan_full_coverage"]]
        ax.bar(positions + (offset - 2) * width, shares, width=width, color=COLORS[sensor["satellite"]], label=sensor["display"])
    labels = [f"{item['eps_m']:.0f} m\n{item['window_min']} min\nmin {item['min_samples']}" for item in settings]
    ax.set_xticks(positions, labels)
    ax.set_ylabel("Noise share of delivered rows")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, ncol=3)
    _finish(fig, path)
    return path


def _figure_latitude(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    bands = report["sensors"][0]["spatial_on_dates_with_all_five_sensors"]["latitude_bands_30deg"]
    labels = [f"{item['south']} to {item['north']}" for item in bands]
    positions = np.arange(len(labels))
    width = 0.15
    for offset, sensor in enumerate(report["sensors"]):
        shared = sensor["spatial_on_dates_with_all_five_sensors"]
        total = shared["rows"] or 1
        shares = [item["rows"] / total for item in shared["latitude_bands_30deg"]]
        ax.bar(positions + (offset - 2) * width, shares, width=width, color=COLORS[sensor["satellite"]], label=sensor["display"])
    ax.set_xticks(positions, labels, rotation=20, ha="right")
    ax.set_ylabel("Share of rows on dates with all five sensors")
    ax.legend(frameon=False, fontsize=8, ncol=3)
    _finish(fig, path)
    return path


def _figure_daynight(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    names = [sensor["display"] for sensor in report["sensors"]]
    positions = np.arange(len(names))
    night_isolated = []
    night_neighborhood = []
    for sensor in report["sensors"]:
        isolated = sensor["characteristics"]["isolated_1km_30min"]
        neighborhood = sensor["characteristics"]["neighborhood_1km_30min"]
        night_isolated.append(0 if not isolated["rows"] else isolated["night_rows"] / isolated["rows"])
        night_neighborhood.append(0 if not neighborhood["rows"] else neighborhood["night_rows"] / neighborhood["rows"])
    ax.bar(positions - 0.18, night_isolated, width=0.36, color="#d9d0c7", label="No neighbor in 1 km and 30 min")
    ax.bar(positions + 0.18, night_neighborhood, width=0.36, color="#5c4d7a", label="Neighbor in 1 km and 30 min")
    ax.set_xticks(positions, names, rotation=20, ha="right")
    ax.set_ylabel("Night share")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def render_execution_log(report: dict[str, object]) -> str:
    performance = report["performance"]
    lines = [
        "# Milestone 9 execution log",
        "",
        "Auditable decisions for the within-sensor analysis. This is not a private reasoning trace.",
        "",
        "## Initial approach",
        "",
        "Inspect the July candidate-pair and nearest-neighbor modules before any full scan. Reuse `ObservationTable`, the ECEF `cKDTree`, and the great-circle chord conversion. Keep Terra and Aqua separate. Keep native confidence. Leave `same_fire` as `not_assessed`. Do not calculate a harmonization coefficient and do not train XGBoost.",
        "",
        "The planned products were duplicate and same-coordinate inventories, within-sensor nearest neighbors, neighborhood density at several radii and time windows, temporally separated detections, and DBSCAN on spatial-temporal partitions with a sensitivity grid.",
        "",
        "## Problems encountered",
        "",
        f"A single in-memory pair list for a month is too large. The bounded probe on NOAA-20 {_date(25)} ({_count(PROBE['rows'])} rows) produced {_count(PROBE['sparse_directed_pairs_including_diagonal_at_5km'])} directed pairs inside 5 km, including the zero-distance diagonal, in {PROBE['sparse_seconds']} seconds and {PROBE['sparse_bytes']:,} bytes.",
        "",
        "The same probe showed a same-day nearest-neighbor median of "
        f"{PROBE['same_day_nearest_median_m']} m and a median time gap of {PROBE['same_day_nearest_median_minutes']} minutes. "
        f"About {100.0 * (1.0 - PROBE['share_of_nearest_within_m']['5000']):.1f}% of those nearest neighbors were beyond 5 km, so a 5 km graph alone would have hidden that tail.",
        "",
        "S-NPP has dates with no delivered rows. Those dates had to stay out of denominators. DBSCAN cluster counts on UTC-date partitions are not additive, because a component can touch the midnight margin.",
        "",
        "The first full run aborted on S-NPP. `query(k=2)` returned the same row in the second slot for at least one detection, which happens when another row has the same coordinate and the tree lists that other row first. No partial sensor result was written. The nearest-other rule was corrected and the full run was repeated. Rows were not dropped.",
        "",
        "After that run, the same-coordinate inventory was checked against a direct pass over the NOAA-20 CSV. The text key and the float64 key both had 1 extra NOAA-20 row, while the report had 2. The grouping had failed to start a new epoch when a coordinate's first minute matched the previous coordinate's last minute, so some different-minute coordinates were counted as same-minute copies. Neighborhood, nearest-neighbor, and DBSCAN results do not use that grouping. Only the coordinate inventory was recomputed after the fix.",
        "",
        "scikit-learn is not installed. A Euclidean DBSCAN would also be the wrong neighborhood, because the relation is a spatial radius combined with a time window.",
        "",
        "## Commands or experiments cancelled and why",
        "",
        "- The temporary probe script `_probe_nn.py` was deleted after the timing and degree sample were recorded. It was not a deliverable and it did not change the CSVs.",
        "- The first `python -m fire_data.within_sensor_analysis` process aborted on S-NPP and was then stopped. It had written no report. The corrected run is the one recorded below.",
        "- A month-global pair graph was not built. The busiest sampled date already held about 146 MB of 5 km pairs. Stacking that graph across the month would have been a memory spike without labeling any additional rows.",
        "- The probe was allowed to finish. The corrected full run was allowed to finish. The only process stopped was the already-aborted first full run.",
        "",
        "## Parameter changes and why",
        "",
        "| Item | Original | Changed to | Reason |",
        "| --- | --- | --- | --- |",
        "| Distance index | Candidate-pair tiles at 20° | One UTC date, optional 180-minute midnight margin | The probe showed a date of 127,817 rows builds a tree in 0.02 s and a 5 km pair list in 0.15 s. A date partition covers every row. |",
        "| Unrestricted nearest neighbor | Take it from the 5 km pair list | Separate nearest-other query on the same date | 7.9% of the probe's nearest neighbors were outside 5 km. The cap would have censored them. |",
        "| Nearest-other query | Assume `k=2` column 0 is the row and column 1 is the neighbor | Keep the nearest returned index that is not the row. Widen `k` only for rows whose first hits are all themselves | The first full S-NPP pass aborted because column 1 was the row itself when a coincident row occupied column 0. |",
        "| DBSCAN grid | Full factorial on every date | Seven one-factor settings on every delivered row, and the 3×3×3 factorial on the representative date | The seven settings label every row. The factorial answers the interaction question without a second full-month graph per cell. Coverage of the primary question was not reduced. |",
        "| Representative date | Unspecified | Earliest date closest to the median row count among dates with rows | A fixed rule, chosen before looking at cluster output. |",
        "| Empty S-NPP dates | Could have been stored as zero | `rows: null`, `zero_detections: false` | A missing delivered date is not zero fire activity. |",
        "| Same-coordinate epochs | A minute change was measured against the previous row, including the previous coordinate | The first row of each coordinate starts a new epoch | A direct NOAA-20 recount found 1 text extra and 1 float extra, not the 2 extras in the first report. The inventory was recomputed. Other results were left as calculated. |",
        "",
        "## Alternative approaches evaluated",
        "",
        "- scikit-learn DBSCAN: rejected. The package is not a project dependency, and the neighborhood is not a single Euclidean ball in scaled latitude, longitude, and time.",
        "- H3 aggregation: not used. Earlier reports left it unused, and this milestone does not ask for a grid index.",
        "- Dropping the 5 km radius after the probe mean degree of about 45: rejected. The date partition made 5 km affordable, so dropping it would have reduced coverage to save time that the probe showed was unnecessary.",
        "- Treating S-NPP empty dates as zeros in the five-sensor spatial comparison: rejected. A separate common-date profile uses only dates on which all five sensors have rows.",
        "",
        "## Final successful approach",
        "",
        "Load the four July CSVs through the existing reader. Check each sensor's row count against the ingestion manifest before interpreting anything. For each satellite and each UTC date with rows, compute the unrestricted same-day nearest neighbor, the 5 km pair list, the windowed neighborhood counts, the next-date neighbor when the next date has rows, and the DBSCAN labels. Write JSON, Markdown, and figures from that report.",
        "",
        f"Load time: {performance['load_seconds']:.1f} s. Analysis time: {performance['analysis_seconds']:.1f} s. Peak Python allocations traced: {performance['peak_python_bytes']:,} bytes.",
        "",
        "Internal consistency checks all passed."
        if all(item["passed"] for item in report["consistency_checks"])
        else "One or more internal consistency checks failed. See the validation note.",
        "",
        "## Remaining uncertainties",
        "",
        "- NOAA-20 and NOAA-21 processing level is still unresolved. The version column was not used as a processing stream.",
        "- DBSCAN components that cross midnight are split by the date partition. Owned-row noise shares are complete. Partition cluster counts are not a global inventory.",
        "- Same-coordinate counts use float64 bits. On these July files they matched a direct text-key recount after the epoch-boundary fix (NOAA-20 extra 1, NOAA-21 extra 4, others 0). A future file could still collide if two different coordinate strings parse to one float. The full-line scan remains the authority for exact CSV duplicates, which were 0.",
        "- A next-date neighbor farther than 5 km is uncounted. The cap is stated. It is not evidence that the next date has no nearby land feature.",
        "- Neighborhoods and components are not validated against burned area, imagery, or any fire inventory.",
        "",
    ]
    return "\n".join(lines)


def render_summary(report: dict[str, object]) -> str:
    lines = [
        "# Milestone 9 summary",
        "",
        "Within-sensor spatial-temporal structure of the July 2024 FIRMS archives. Five satellites, "
        f"{_count(report['rows'])} delivered rows. Neighbors and DBSCAN components are not confirmed fires. `same_fire` is `not_assessed`.",
        "",
        "## What was measured",
        "",
        "- Exact extra copies on the loaded analysis fields, without removing any row.",
        "- Repeated coordinates at the same acquisition minute, and repeated coordinates at different minutes.",
        "- The nearest other row on the same UTC date, at any distance.",
        "- Neighborhood counts at 375 m, 1 km, 2 km, and 5 km, and at 0, 30, and 180 minutes.",
        "- The closest row on the next UTC date, capped at 5 km, with empty next dates left null.",
        "- FRP, brightness, scan, track, day/night, and native confidence for all rows, for rows with a 1 km / 30 min neighbor, and for rows without one.",
        "- Spatial occupancy on all delivered dates and on dates when all five sensors have rows.",
        "- DBSCAN noise share for seven settings on every delivered row, plus a 27-cell factorial on one representative date per sensor.",
        "",
        "## What was not done",
        "",
        "- No harmonization coefficient.",
        "- No XGBoost model.",
        "- No repaired S-NPP dates and no zeros substituted for dates without rows.",
        "- No cluster was named as a physical fire.",
        "",
        "## Where the numbers are",
        "",
        "- `backend/reports/within_sensor_analysis_2024_07.md`",
        "- `backend/reports/within_sensor_analysis_2024_07.json`",
        "- `backend/reports/figures/within_sensor_2024_07/`",
        "",
        "Reproduce from `backend` with `.venv\\Scripts\\python -m fire_data.within_sensor_analysis`.",
        "",
    ]
    return "\n".join(lines)


def render_metrics(report: dict[str, object]) -> dict[str, object]:
    sensors = []
    for sensor in report["sensors"]:
        primary = next(item for item in sensor["dbscan_full_coverage"] if item["role"] == "primary")
        sensors.append(
            {
                "satellite": sensor["satellite"],
                "rows": sensor["rows"],
                "dates_without_rows": sensor["dates_without_rows"],
                "exact_extra_rows": sensor["duplicates"]["extra_rows"],
                "same_coordinate_and_time_extra_rows": sensor["coordinates"]["same_coordinate_and_time_extra_rows"],
                "multi_epoch_locations": sensor["coordinates"]["multi_epoch_locations"],
                "same_day_nearest_median_m": sensor["same_day_nearest"]["distance"]["p50"],
                "same_day_nearest_beyond_5km": sensor["same_day_nearest"]["beyond_5km"],
                "neighborhood_1km_30min_rows": sensor["characteristics"]["neighborhood_1km_30min"]["rows"],
                "isolated_1km_30min_rows": sensor["characteristics"]["isolated_1km_30min"]["rows"],
                "next_date_within_1km": sensor["next_date_neighbor"]["within_1km"],
                "next_date_excluded_rows": sensor["next_date_neighbor"]["excluded_because_next_date_has_no_rows"],
                "next_date_outside_july_rows": sensor["next_date_neighbor"]["excluded_because_next_date_is_outside_july"],
                "dbscan_primary_noise_share": primary["noise_share"],
                "dbscan_primary_partition_cluster_count_sum": primary["partition_cluster_count_sum"],
                "representative_date": sensor["dbscan_representative_day"]["date"],
                "same_fire": "not_assessed",
            }
        )
    return {
        "milestone": 9,
        "rows": report["rows"],
        "same_fire": "not_assessed",
        "harmonization_coefficient": None,
        "xgboost_trained": False,
        "clusters_are_confirmed_fires": False,
        "consistency_checks_passed": all(item["passed"] for item in report["consistency_checks"]),
        "performance": report["performance"],
        "sensors": sensors,
    }


def render_validation(report: dict[str, object], *, pytest_text: str | None) -> str:
    lines = [
        "# Milestone 9 validation",
        "",
        "Checks below are computed from the written report. A failed check is a failed milestone, not a scientific finding.",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for item in report["consistency_checks"]:
        lines.append(f"| {item['name']} | {str(item['passed']).lower()} | {item['detail']} |")
    lines.extend(
        [
            "",
            "## Scientific guards",
            "",
            "- `same_fire` is `not_assessed` on the report and on every sensor.",
            "- `harmonization_coefficient` is null. `xgboost_trained` is false.",
            "- DBSCAN summaries set `clusters_are_confirmed_fires` to false.",
            "- S-NPP dates 10–15 and 25–28 July have null row counts.",
            "- Daily delivered rows sum to the manifest totals. No row was removed.",
            "- Isolated rows plus neighborhood rows equal the sensor total at 1 km and 30 minutes.",
            "- Each full-coverage DBSCAN setting labels every delivered row as noise or clustered.",
            "",
            "## Tests",
            "",
        ]
    )
    if pytest_text:
        lines.append("```")
        lines.append(pytest_text.rstrip())
        lines.append("```")
    else:
        lines.append("The unit tests are run separately with `.venv\\Scripts\\python -m pytest` from `backend`. This file is updated after that command.")
    lines.extend(
        [
            "",
            "## Not claimed",
            "",
            "Passing these checks does not mean a cluster is a fire. It means the counts are internally consistent with the stated definitions and the archived rows.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict[str, object]) -> None:
    report["consistency_checks"] = consistency_checks(report)
    report["figures"] = write_figures(report, FIGURE_DIR)
    payload = _plain(report)
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    MILESTONE_DIR.mkdir(parents=True, exist_ok=True)
    (MILESTONE_DIR / "milestone_09_summary.md").write_text(render_summary(payload), encoding="utf-8")
    (MILESTONE_DIR / "milestone_09_execution_log.md").write_text(render_execution_log(payload), encoding="utf-8")
    (MILESTONE_DIR / "milestone_09_metrics.json").write_text(
        json.dumps(_plain(render_metrics(payload)), indent=2) + "\n",
        encoding="utf-8",
    )
    (MILESTONE_DIR / "milestone_09_validation.md").write_text(render_validation(payload, pytest_text=None), encoding="utf-8")


def main() -> int:
    tracemalloc.start()
    started = perf_counter()
    tables = load_tables()
    load_seconds = perf_counter() - started
    analysis_started = perf_counter()
    report = build_report(tables, load_seconds=load_seconds, started=analysis_started)
    write_outputs(report)
    checks = report["consistency_checks"]
    failed = [item["name"] for item in checks if not item["passed"]]
    print(
        f"rows={report['rows']} sensors={len(report['sensors'])} "
        f"load_s={report['performance']['load_seconds']:.1f} "
        f"analysis_s={report['performance']['analysis_seconds']:.1f} "
        f"checks_failed={len(failed)}",
        flush=True,
    )
    if failed:
        print("failed=" + ",".join(failed), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
