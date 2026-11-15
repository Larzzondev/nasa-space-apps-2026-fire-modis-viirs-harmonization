"""Nearest-neighbor sensitivity for July 2024 MODIS and VIIRS detections.

A nearest neighbor is the closest archived row inside a stated distance and time
window. It is not a confirmed fire. A mutual nearest neighbor is not a confirmed
fire either. A one-to-one assignment only stops one row from being paired with
several partners. ``same_fire`` stays ``not_assessed``.
"""

from __future__ import annotations

import json
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import linear_sum_assignment

from fire_data.eda_figures import COLORS
from fire_data.spatiotemporal_analysis import (
    DAYNIGHT_LABELS,
    DISPLAY,
    PROVENANCE,
    RADII_M,
    VIIRS_FLAGS,
    AnalysisError,
    ObservationTable,
    _members,
    candidate_pairs,
    load_tables,
)

PAIR_WINDOWS = (
    (("Terra", "Aqua"), (30,)),
    (("MODIS", "SNPP"), (30,)),
    (("MODIS", "N20"), (30,)),
    (("MODIS", "N21"), (30,)),
    (("SNPP", "N20"), (30, 60)),
    (("SNPP", "N21"), (30, 60)),
    (("N20", "N21"), (60,)),
)
OFFSET = 10_000_000
SATELLITE_CODE = {"Terra": 1, "Aqua": 2, "SNPP": 3, "N20": 4, "N21": 5}
CODE_SATELLITE = {code: name for name, code in SATELLITE_CODE.items()}
DISTANCE_EDGES = np.linspace(0.0, 5_000.0, 21)
TIME_EDGES = np.arange(0, 61, dtype=np.float64)
RATIO_EDGES = np.logspace(-2, 2, 41)
DETAIL_RADIUS_M = 1_000.0
ASSIGNMENT_SENTINEL = 1.0e12
ASSIGNMENT_REFERENCE_LIMIT = 80
ASSIGNMENT_PARTNER_LIMIT = 120
MODIS_CLASS_LABELS = ("low_0_29", "nominal_30_79", "high_80_100")
REPORT_JSON = Path(__file__).resolve().parents[1] / "reports" / "nearest_neighbor_analysis_2024_07.json"
REPORT_MD = Path(__file__).resolve().parents[1] / "reports" / "nearest_neighbor_analysis_2024_07.md"
FIGURE_DIR = Path(__file__).resolve().parents[1] / "reports" / "figures" / "nearest_neighbor_2024_07"
PAIR_COLORS = ("#b86b2a", "#8c4a2f", "#2f6f8f", "#3d8b7a", "#5c4d7a", "#6b7c3a", "#a33b4a")


def detail_window(windows: tuple[int, ...]) -> int:
    """Window used for the main tables. Thirty minutes is used when this pair has it."""

    return 30 if 30 in windows else int(windows[0])


def pack_ids(name: str, index: np.ndarray) -> np.ndarray:
    return SATELLITE_CODE[name] * OFFSET + np.asarray(index, dtype=np.int64)


def _view(tables: dict[str, ObservationTable], names: tuple[str, ...], days: list[int]) -> dict[str, np.ndarray] | None:
    """Slice named satellites to the requested UTC days without copying the source files."""

    wanted = np.asarray(days, dtype=np.int8)
    ecef, epoch, latitude, longitude, packed = [], [], [], [], []
    for name in names:
        table = tables[name]
        if table.count == 0:
            continue
        chosen = np.flatnonzero(np.isin(table.day, wanted))
        if chosen.size == 0:
            continue
        ecef.append(table.ecef[chosen])
        epoch.append(table.epoch[chosen])
        latitude.append(table.latitude[chosen])
        longitude.append(table.longitude[chosen])
        packed.append(pack_ids(name, chosen))
    if not packed:
        return None
    return {
        "ecef": np.concatenate(ecef),
        "epoch": np.concatenate(epoch),
        "latitude": np.concatenate(latitude),
        "longitude": np.concatenate(longitude),
        "packed": np.concatenate(packed),
    }


def _count_on(tables: dict[str, ObservationTable], names: tuple[str, ...], day: int) -> int:
    return sum(tables[name].count_on(day) for name in names if name in tables)


def unique_pairs(
    a_id: np.ndarray,
    b_id: np.ndarray,
    distance: np.ndarray,
    delta: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Keep the shortest copy when a tile boundary reports the same two rows twice."""

    if a_id.size == 0:
        return a_id, b_id, distance, delta
    order = np.lexsort((distance, b_id, a_id))
    a_id = a_id[order]
    b_id = b_id[order]
    distance = distance[order]
    delta = delta[order]
    duplicate = np.zeros(a_id.size, dtype=bool)
    duplicate[1:] = (a_id[1:] == a_id[:-1]) & (b_id[1:] == b_id[:-1])
    keep = ~duplicate
    return a_id[keep], b_id[keep], distance[keep], delta[keep]


def group_nearest(
    a_id: np.ndarray,
    b_id: np.ndarray,
    distance: np.ndarray,
    delta: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Nearest and second-nearest partner for each reference id.

    Equal distances keep the smaller partner id, so the choice is repeatable.
    """

    empty = (
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.float64),
        np.empty(0, dtype=np.int32),
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.float64),
    )
    if a_id.size == 0:
        return empty
    order = np.lexsort((b_id, distance, a_id))
    a_id = a_id[order]
    b_id = b_id[order]
    distance = distance[order]
    delta = delta[order]
    starts = np.flatnonzero(np.diff(a_id, prepend=a_id[0] - 1))
    counts = np.diff(np.append(starts, a_id.size))
    second = np.full(starts.size, np.nan, dtype=np.float64)
    has_second = counts >= 2
    second[has_second] = distance[starts[has_second] + 1]
    return a_id[starts], b_id[starts], distance[starts], delta[starts], counts, second


def greedy_indices(
    a_id: np.ndarray,
    b_id: np.ndarray,
    distance: np.ndarray,
    used: dict[int, np.ndarray],
) -> np.ndarray:
    """Calendar-day greedy assignment. Each packed id is used at most once.

    ``used`` persists across dates. Dates must be supplied in calendar order.
    Inside a date, shorter separations are assigned first. This is not a global
    optimum and it is not evidence that the two rows are the same fire.
    """

    if a_id.size == 0:
        return np.empty(0, dtype=np.int64)
    order = np.lexsort((b_id, a_id, distance))
    ordered_a = a_id[order]
    ordered_b = b_id[order]
    taken: list[int] = []
    append = taken.append
    for position in range(ordered_a.size):
        left_code, left_index = divmod(int(ordered_a[position]), OFFSET)
        right_code, right_index = divmod(int(ordered_b[position]), OFFSET)
        left = used[left_code]
        right = used[right_code]
        if left[left_index] or right[right_index]:
            continue
        left[left_index] = True
        right[right_index] = True
        append(int(order[position]))
    if not taken:
        return np.empty(0, dtype=np.int64)
    return np.asarray(taken, dtype=np.int64)


def assignment_comparison(
    a_id: np.ndarray,
    b_id: np.ndarray,
    distance: np.ndarray,
    *,
    reference_limit: int = ASSIGNMENT_REFERENCE_LIMIT,
    partner_limit: int = ASSIGNMENT_PARTNER_LIMIT,
) -> dict[str, object]:
    """Compare greedy assignment with the Hungarian method on one small graph.

    The subset is deterministic: the reference rows with the shortest nearest
    neighbor, then the partners connected to those rows. It is not a sample of
    the whole month and it is not a fire match.
    """

    base = {
        "algorithm": "scipy.optimize.linear_sum_assignment",
        "same_fire": "not_assessed",
        "one_to_one_is_physical_truth": False,
        "subset_is_the_full_month": False,
    }
    if a_id.size == 0:
        return {**base, "status": "no_edges", "reference_rows": 0, "partner_rows": 0, "edges": 0}
    nearest_a, nearest_b, nearest_d, _, _, _ = group_nearest(a_id, b_id, distance, np.zeros(a_id.size, dtype=np.int32))
    order = np.lexsort((nearest_a, nearest_d))
    chosen_a = nearest_a[order][:reference_limit]
    selected = np.isin(a_id, chosen_a)
    if not np.any(selected):
        return {**base, "status": "no_edges", "reference_rows": 0, "partner_rows": 0, "edges": 0}
    sub_a = a_id[selected]
    sub_b = b_id[selected]
    sub_d = distance[selected]
    partner_order = np.lexsort((sub_b, sub_d))
    partner_ids = []
    seen: set[int] = set()
    for partner in sub_b[partner_order]:
        key = int(partner)
        if key in seen:
            continue
        seen.add(key)
        partner_ids.append(key)
        if len(partner_ids) >= partner_limit:
            break
    partner_ids_array = np.asarray(partner_ids, dtype=np.int64)
    keep = np.isin(sub_b, partner_ids_array)
    sub_a = sub_a[keep]
    sub_b = sub_b[keep]
    sub_d = sub_d[keep]
    reference_ids = np.unique(sub_a)
    row_index = {int(value): index for index, value in enumerate(reference_ids)}
    column_index = {int(value): index for index, value in enumerate(partner_ids_array)}
    cost = np.full((reference_ids.size, partner_ids_array.size), ASSIGNMENT_SENTINEL, dtype=np.float64)
    for left, right, separation in zip(sub_a, sub_b, sub_d, strict=True):
        row = row_index[int(left)]
        column = column_index[int(right)]
        if separation < cost[row, column]:
            cost[row, column] = float(separation)
    fresh = _masks_for(np.concatenate((sub_a, sub_b)))
    greedy_pos = greedy_indices(sub_a, sub_b, sub_d, fresh)
    greedy_distance = float(sub_d[greedy_pos].sum()) if greedy_pos.size else 0.0
    rows, columns = linear_sum_assignment(cost)
    accepted = cost[rows, columns] < ASSIGNMENT_SENTINEL
    hungarian_distance = float(cost[rows, columns][accepted].sum()) if np.any(accepted) else 0.0
    return {
        **base,
        "status": "compared",
        "reference_rows": int(reference_ids.size),
        "partner_rows": int(partner_ids_array.size),
        "edges": int(sub_a.size),
        "greedy_assigned_pairs": int(greedy_pos.size),
        "greedy_distance_sum_m": greedy_distance,
        "hungarian_assigned_pairs": int(np.count_nonzero(accepted)),
        "hungarian_distance_sum_m": hungarian_distance,
    }


def _masks_for(packed: np.ndarray) -> dict[int, np.ndarray]:
    masks = {code: np.zeros(1, dtype=np.bool_) for code in SATELLITE_CODE.values()}
    if packed.size == 0:
        return masks
    codes, indices = np.divmod(packed, OFFSET)
    for code in np.unique(codes):
        masks[int(code)] = np.zeros(int(indices[codes == code].max()) + 1, dtype=np.bool_)
    return masks


def _blank_maps(tables: dict[str, ObservationTable], names: tuple[str, ...]) -> dict[str, dict[str, np.ndarray]]:
    maps = {}
    for name in names:
        count = tables[name].count
        maps[name] = {
            "code": np.full(count, -1, dtype=np.int8),
            "index": np.full(count, -1, dtype=np.int32),
            "distance": np.full(count, np.inf, dtype=np.float64),
        }
    return maps


def _store_nearest(maps: dict[str, dict[str, np.ndarray]], a_id: np.ndarray, b_id: np.ndarray, distance: np.ndarray) -> None:
    if a_id.size == 0:
        return
    left_code, left_index = np.divmod(a_id, OFFSET)
    right_code, right_index = np.divmod(b_id, OFFSET)
    for code, name in CODE_SATELLITE.items():
        if name not in maps:
            continue
        chosen = left_code == code
        if not np.any(chosen):
            continue
        slot = maps[name]
        rows = left_index[chosen]
        slot["code"][rows] = right_code[chosen]
        slot["index"][rows] = right_index[chosen]
        slot["distance"][rows] = distance[chosen]


def _lookup(tables: dict[str, ObservationTable], packed: np.ndarray, field: str) -> np.ndarray:
    values = np.empty(packed.size, dtype=np.float64)
    codes, indices = np.divmod(packed, OFFSET)
    for code, name in CODE_SATELLITE.items():
        chosen = codes == code
        if np.any(chosen):
            values[chosen] = np.asarray(getattr(tables[name], field)[indices[chosen]], dtype=np.float64)
    return values


def _confidence_labels(name: str, values: np.ndarray) -> np.ndarray:
    if name in {"Terra", "Aqua"}:
        labels = np.zeros(values.size, dtype=np.int8)
        labels[values >= 30] = 1
        labels[values >= 80] = 2
        return labels
    return values.astype(np.int8)


def _class_names(name: str) -> tuple[str, ...]:
    return MODIS_CLASS_LABELS if name in {"Terra", "Aqua"} else VIIRS_FLAGS


def mutual_mask(
    forward: dict[str, dict[str, np.ndarray]],
    reverse: dict[str, dict[str, np.ndarray]],
    names: tuple[str, ...],
    radius_m: float,
) -> dict[str, np.ndarray]:
    """Rows whose nearest partner also has this row as its nearest partner."""

    masks = {}
    for name in names:
        slot = forward[name]
        matched = (slot["index"] >= 0) & (slot["distance"] <= radius_m)
        accepted = np.zeros(slot["index"].size, dtype=bool)
        rows = np.flatnonzero(matched)
        if rows.size:
            partner_code = slot["code"][rows]
            partner_index = slot["index"][rows]
            my_code = SATELLITE_CODE[name]
            for code, other in CODE_SATELLITE.items():
                if other not in reverse:
                    continue
                chosen = partner_code == code
                if not np.any(chosen):
                    continue
                other_rows = partner_index[chosen]
                back = reverse[other]
                same = (
                    (back["code"][other_rows] == my_code)
                    & (back["index"][other_rows] == rows[chosen])
                    & (back["distance"][other_rows] <= radius_m)
                )
                accepted[rows[chosen][same]] = True
        masks[name] = accepted
    return masks


def _new_used(tables: dict[str, ObservationTable], names: tuple[str, ...]) -> dict[int, np.ndarray]:
    return {SATELLITE_CODE[name]: np.zeros(tables[name].count, dtype=np.bool_) for name in names}


def _quantile(values: np.ndarray) -> dict[str, float | int | None]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"count": 0, "p10": None, "p25": None, "p50": None, "p75": None, "p90": None}
    qs = np.quantile(finite, [0.1, 0.25, 0.5, 0.75, 0.9], method="linear")
    return {
        "count": int(finite.size),
        "p10": float(qs[0]),
        "p25": float(qs[1]),
        "p50": float(qs[2]),
        "p75": float(qs[3]),
        "p90": float(qs[4]),
    }


def _histogram_median(counts: np.ndarray, edges: np.ndarray) -> dict[str, float | int | None]:
    total = int(counts.sum())
    if total == 0:
        return {"count": 0, "bin_start": None, "bin_end": None}
    index = int(np.searchsorted(np.cumsum(counts), (total + 1) // 2, side="left"))
    index = min(index, counts.size - 1)
    return {"count": total, "bin_start": float(edges[index]), "bin_end": float(edges[index + 1])}


def _count_quantile(histogram: np.ndarray, overflow: int) -> dict[str, float | int | None]:
    total = int(histogram.sum())
    if total == 0:
        return {"count": 0, "p50": None, "p90": None, "maximum": None}
    cumulative = np.cumsum(histogram)
    p50 = int(np.searchsorted(cumulative, (total + 1) // 2, side="left"))
    p90 = int(np.searchsorted(cumulative, max(1, int(np.ceil(0.9 * total))), side="left"))
    return {"count": total, "p50": p50, "p90": p90, "maximum": int(overflow)}


class _WindowAccumulator:
    def __init__(self, radii: tuple[float, ...], tables: dict[str, ObservationTable], involved: tuple[str, ...]) -> None:
        self.radii = radii
        self.reference_rows = 0
        self.reference_rows_by_satellite = {name: 0 for name in involved}
        self.matched = {radius: 0 for radius in radii}
        self.matched_by_satellite = {radius: {name: 0 for name in involved} for radius in radii}
        self.eligible_pairs = {radius: 0 for radius in radii}
        self.assigned = {radius: 0 for radius in radii}
        self.ambiguity = {radius: np.zeros(4, dtype=np.int64) for radius in radii}
        self.count_hist = {radius: np.zeros(65, dtype=np.int64) for radius in radii}
        self.count_max = {radius: 0 for radius in radii}
        self.nearest_hist = {radius: np.zeros(DISTANCE_EDGES.size - 1, dtype=np.int64) for radius in radii}
        self.second_hist = {radius: np.zeros(DISTANCE_EDGES.size - 1, dtype=np.int64) for radius in radii}
        self.gap_hist = {radius: np.zeros(DISTANCE_EDGES.size - 1, dtype=np.int64) for radius in radii}
        self.time_hist = {radius: np.zeros(TIME_EDGES.size - 1, dtype=np.int64) for radius in radii}
        self.daynight = {radius: np.zeros(4, dtype=np.int64) for radius in radii}
        self.partner_seen = {
            radius: {name: np.zeros(tables[name].count, dtype=np.bool_) for name in involved} for radius in radii
        }
        self.used = {radius: _new_used(tables, involved) for radius in radii}
        self.ratio_parts = {radius: [] for radius in radii}
        self.ratio_daynight = {radius: [] for radius in radii}
        self.ratio_reference_class = {radius: [] for radius in radii}
        self.ratio_partner_class = {radius: [] for radius in radii}
        self.excluded_nonpositive = {radius: 0 for radius in radii}
        self.reference_nonpositive = {radius: 0 for radius in radii}
        self.partner_nonpositive = {radius: 0 for radius in radii}
        self.assigned_ratio_parts = []
        self.assigned_nonpositive = 0
        self.scan_reference = []
        self.scan_partner = []
        self.frp_reference = []
        self.frp_partner = []

    def add_reference_rows(self, counts: dict[str, int]) -> None:
        for name, count in counts.items():
            self.reference_rows += count
            self.reference_rows_by_satellite[name] = self.reference_rows_by_satellite.get(name, 0) + count

    def add_directed(
        self,
        tables: dict[str, ObservationTable],
        radius: float,
        a_id: np.ndarray,
        b_id: np.ndarray,
        distance: np.ndarray,
        delta: np.ndarray,
        counts: np.ndarray,
        second: np.ndarray,
        reference_count: int,
    ) -> None:
        self.eligible_pairs[radius] += int(a_id.size and counts.sum())
        self.matched[radius] += int(counts.size)
        zeros = reference_count - int(counts.size)
        if zeros < 0:
            raise AnalysisError("Nearest-neighbor groups exceeded the reference rows on this date")
        bins = self.ambiguity[radius]
        bins[0] += zeros
        bins[1] += int(np.count_nonzero(counts == 1))
        bins[2] += int(np.count_nonzero((counts >= 2) & (counts <= 5)))
        bins[3] += int(np.count_nonzero(counts > 5))
        clipped = np.minimum(counts, 64)
        self.count_hist[radius] += np.bincount(clipped, minlength=65)
        if counts.size:
            self.count_max[radius] = max(self.count_max[radius], int(counts.max()))
        if a_id.size == 0:
            return
        self.nearest_hist[radius] += np.histogram(distance, bins=DISTANCE_EDGES)[0].astype(np.int64)
        self.time_hist[radius] += np.histogram(np.minimum(delta, TIME_EDGES[-1]), bins=TIME_EDGES)[0].astype(np.int64)
        has_second = np.isfinite(second)
        if np.any(has_second):
            self.second_hist[radius] += np.histogram(second[has_second], bins=DISTANCE_EDGES)[0].astype(np.int64)
            gap = second[has_second] - distance[has_second]
            self.gap_hist[radius] += np.histogram(np.clip(gap, 0.0, DISTANCE_EDGES[-1]), bins=DISTANCE_EDGES)[0].astype(np.int64)
        left_code, left_index = np.divmod(a_id, OFFSET)
        right_code, right_index = np.divmod(b_id, OFFSET)
        for code, name in CODE_SATELLITE.items():
            chosen = left_code == code
            if np.any(chosen) and name in self.matched_by_satellite[radius]:
                self.matched_by_satellite[radius][name] += int(np.count_nonzero(chosen))
            partners = right_code == code
            if np.any(partners) and name in self.partner_seen[radius]:
                self.partner_seen[radius][name][right_index[partners]] = True
        daynight = _lookup(tables, a_id, "daynight").astype(np.int16) * 2 + _lookup(tables, b_id, "daynight").astype(np.int16)
        self.daynight[radius] += np.bincount(daynight, minlength=4)
        frp_a = _lookup(tables, a_id, "frp")
        frp_b = _lookup(tables, b_id, "frp")
        positive = (frp_a > 0.0) & (frp_b > 0.0)
        self.excluded_nonpositive[radius] += int(np.count_nonzero(~positive))
        self.reference_nonpositive[radius] += int(np.count_nonzero(frp_a <= 0.0))
        self.partner_nonpositive[radius] += int(np.count_nonzero(frp_b <= 0.0))
        if np.any(positive):
            ratio = frp_b[positive] / frp_a[positive]
            self.ratio_parts[radius].append(ratio.astype(np.float64, copy=False))
            self.ratio_daynight[radius].append(daynight[positive].astype(np.int8, copy=False))
            self.ratio_reference_class[radius].append(_confidence_class(tables, a_id[positive]))
            self.ratio_partner_class[radius].append(_confidence_class(tables, b_id[positive]))
        if radius == DETAIL_RADIUS_M:
            self.scan_reference.append(_lookup(tables, a_id, "scan"))
            self.scan_partner.append(_lookup(tables, b_id, "scan"))
            self.frp_reference.append(frp_a)
            self.frp_partner.append(frp_b)

    def add_assigned(self, tables: dict[str, ObservationTable], radius: float, a_id: np.ndarray, b_id: np.ndarray) -> None:
        self.assigned[radius] += int(a_id.size)
        if radius != DETAIL_RADIUS_M or a_id.size == 0:
            return
        frp_a = _lookup(tables, a_id, "frp")
        frp_b = _lookup(tables, b_id, "frp")
        positive = (frp_a > 0.0) & (frp_b > 0.0)
        self.assigned_nonpositive += int(np.count_nonzero(~positive))
        if np.any(positive):
            self.assigned_ratio_parts.append((frp_b[positive] / frp_a[positive]).astype(np.float64, copy=False))


def _confidence_class(tables: dict[str, ObservationTable], packed: np.ndarray) -> np.ndarray:
    labels = np.zeros(packed.size, dtype=np.int8)
    codes, indices = np.divmod(packed, OFFSET)
    for code, name in CODE_SATELLITE.items():
        chosen = codes == code
        if not np.any(chosen):
            continue
        values = np.asarray(tables[name].confidence[indices[chosen]], dtype=np.float64)
        labels[chosen] = _confidence_labels(name, values)
    return labels


def _concat(parts: list[np.ndarray], dtype: np.dtype) -> np.ndarray:
    if not parts:
        return np.empty(0, dtype=dtype)
    return np.concatenate(parts)


def _ratio_record(values: np.ndarray) -> dict[str, object]:
    quantiles = _quantile(values)
    quantiles["histogram"] = np.histogram(values, bins=RATIO_EDGES)[0].astype(int).tolist() if values.size else [0] * (RATIO_EDGES.size - 1)
    quantiles["ratio_edges"] = RATIO_EDGES.tolist()
    quantiles["ratio_is_a_harmonization_coefficient"] = False
    quantiles["pairs_are_independent"] = False
    return quantiles


def _stratum_ratios(values: np.ndarray, labels: np.ndarray, names: tuple[str, ...]) -> list[dict[str, object]]:
    rows = []
    for code, name in enumerate(names):
        chosen = labels == code
        record = _quantile(values[chosen])
        record["class"] = name
        record["ratio_is_a_harmonization_coefficient"] = False
        rows.append(record)
    return rows


def _threshold_payload(
    accumulator: _WindowAccumulator,
    radius: float,
    mutual: int,
    mutual_ratio: dict[str, object],
) -> dict[str, object]:
    matched = int(accumulator.matched[radius])
    assigned = int(accumulator.assigned[radius])
    ambiguity = accumulator.ambiguity[radius]
    unique_partners = sum(int(np.count_nonzero(mask)) for mask in accumulator.partner_seen[radius].values())
    ratios = _concat(accumulator.ratio_parts[radius], np.float64)
    return {
        "radius_m": radius,
        "reference_rows_on_compared_dates": int(accumulator.reference_rows),
        "matched_reference_detections": matched,
        "unmatched_reference_detections": int(accumulator.reference_rows - matched),
        "eligible_candidate_pairs": int(accumulator.eligible_pairs[radius]),
        "unique_directed_nearest_neighbors": matched,
        "unique_partner_detections": unique_partners,
        "mutual_nearest_neighbors": int(mutual),
        "mutual_proportion_of_directed": None if matched == 0 else float(mutual / matched),
        "assigned_one_to_one_pairs": assigned,
        "ambiguity": {
            "zero_candidates": int(ambiguity[0]),
            "one_candidate": int(ambiguity[1]),
            "two_to_five_candidates": int(ambiguity[2]),
            "more_than_five_candidates": int(ambiguity[3]),
            "ambiguous_rate": None if accumulator.reference_rows == 0 else float((ambiguity[2] + ambiguity[3]) / accumulator.reference_rows),
            "candidate_count_among_matched": _count_quantile(accumulator.count_hist[radius], accumulator.count_max[radius]),
        },
        "matched_by_satellite": {name: int(count) for name, count in accumulator.matched_by_satellite[radius].items()},
        "daynight_directed": {label: int(accumulator.daynight[radius][index]) for index, label in enumerate(DAYNIGHT_LABELS)},
        "nearest_distance_m": _histogram_median(accumulator.nearest_hist[radius], DISTANCE_EDGES),
        "second_nearest_distance_m": _histogram_median(accumulator.second_hist[radius], DISTANCE_EDGES),
        "nearest_minus_second_gap_m": _histogram_median(accumulator.gap_hist[radius], DISTANCE_EDGES),
        "nearest_time_difference_minutes": _histogram_median(accumulator.time_hist[radius], TIME_EDGES),
        "nearest_distance_histogram": accumulator.nearest_hist[radius].astype(int).tolist(),
        "second_distance_histogram": accumulator.second_hist[radius].astype(int).tolist(),
        "gap_histogram": accumulator.gap_hist[radius].astype(int).tolist(),
        "time_histogram": accumulator.time_hist[radius].astype(int).tolist(),
        "frp_directed": {
            "ratio_other_over_reference": _ratio_record(ratios),
            "excluded_nonpositive_frp_pairs": int(accumulator.excluded_nonpositive[radius]),
            "reference_nonpositive_frp": int(accumulator.reference_nonpositive[radius]),
            "partner_nonpositive_frp": int(accumulator.partner_nonpositive[radius]),
            "zero_frp_rows_removed_from_source": False,
        },
        "mutual_frp": mutual_ratio,
        "same_fire": "not_assessed",
        "nearest_neighbor_is_same_fire": False,
        "mutual_nearest_neighbor_is_same_fire": False,
        "one_to_one_is_physical_truth": False,
        "candidate_pairs_are_unique_fires": False,
    }


def _search(left: dict[str, np.ndarray] | None, right: dict[str, np.ndarray] | None, radius_m: float, window: int):
    empty = (
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.float64),
        np.empty(0, dtype=np.int32),
    )
    if left is None or right is None:
        return empty
    idx_a, idx_b, distance, delta = candidate_pairs(
        left["ecef"],
        left["epoch"],
        left["latitude"],
        left["longitude"],
        right["ecef"],
        right["epoch"],
        right["latitude"],
        right["longitude"],
        max_geodesic_m=radius_m,
        max_delta_minutes=window,
    )
    if idx_a.size == 0:
        return empty
    return left["packed"][idx_a], right["packed"][idx_b], distance, delta


def analyze_pair(
    tables: dict[str, ObservationTable],
    pair: tuple[str, str],
    windows: tuple[int, ...],
    *,
    radii_m: tuple[float, ...] = RADII_M,
    days: list[int] | None = None,
    compare_assignment: bool = True,
) -> dict[str, object]:
    """Directed, mutual, and one-to-one summaries for one sensor pair."""

    reference, other = pair
    reference_names = _members(reference)
    other_names = _members(other)
    radii = tuple(sorted(float(radius) for radius in radii_m))
    windows = tuple(sorted(int(window) for window in windows))
    max_radius = radii[-1]
    day_list = list(range(1, 32) if days is None else days)
    involved = tuple(dict.fromkeys((*reference_names, *other_names)))
    accumulators = {window: _WindowAccumulator(radii, tables, involved) for window in windows}
    forward = {window: _blank_maps(tables, reference_names) for window in windows}
    reverse = {window: _blank_maps(tables, other_names) for window in windows}
    daily = []
    excluded = []
    assignment = None
    focus = detail_window(windows)
    for day in day_list:
        reference_counts = {name: tables[name].count_on(day) for name in reference_names}
        reference_rows = sum(reference_counts.values())
        other_rows = _count_on(tables, other_names, day)
        date = f"2024-07-{day:02d}"
        neighbors = [value for value in (day - 1, day, day + 1) if 1 <= value <= 31]
        max_window = windows[-1]
        if other_rows > 0:
            reverse_ids = _search(
                _view(tables, other_names, [day]),
                _view(tables, reference_names, neighbors),
                max_radius,
                max_window,
            )
            for window in windows:
                ra, rb, rd, rdelta = reverse_ids
                if ra.size == 0:
                    continue
                keep = rdelta <= window
                ra, rb, rd, _ = unique_pairs(ra[keep], rb[keep], rd[keep], rdelta[keep])
                rna, rnb, rnd, _, _, _ = group_nearest(ra, rb, rd, np.zeros(ra.size, dtype=np.int32))
                _store_nearest(reverse[window], rna, rnb, rnd)
        if reference_rows == 0 or other_rows == 0:
            if reference_rows == 0 and other_rows == 0:
                status = "both_absent"
            elif reference_rows == 0:
                status = "reference_absent"
            else:
                status = "other_absent"
            excluded.append({"date": date, "status": status})
            daily.append(
                {
                    "date": date,
                    "status": status,
                    "matched_reference_detections": None,
                    "assigned_one_to_one_pairs": None,
                    "zero_detections": False,
                }
            )
            continue
        for accumulator in accumulators.values():
            accumulator.add_reference_rows(reference_counts)
        reference_view = _view(tables, reference_names, [day])
        other_view = _view(tables, other_names, neighbors)
        forward_ids = _search(reference_view, other_view, max_radius, max_window)
        focus_matched = None
        focus_assigned = None
        for window in windows:
            accumulator = accumulators[window]
            a_id, b_id, distance, delta = forward_ids
            if a_id.size:
                keep = delta <= window
                a_id, b_id, distance, delta = unique_pairs(a_id[keep], b_id[keep], distance[keep], delta[keep])
            grouped = {}
            for radius in radii:
                if a_id.size:
                    near = distance <= radius
                    grouped[radius] = group_nearest(a_id[near], b_id[near], distance[near], delta[near])
                else:
                    grouped[radius] = group_nearest(a_id, b_id, distance, delta)
                ga, gb, gd, gt, counts, second = grouped[radius]
                accumulator.add_directed(tables, radius, ga, gb, gd, gt, counts, second, reference_rows)
                chosen = greedy_indices(a_id[distance <= radius] if a_id.size else a_id, b_id[distance <= radius] if b_id.size else b_id, distance[distance <= radius] if distance.size else distance, accumulator.used[radius])
                if a_id.size and chosen.size:
                    near = distance <= radius
                    selected_a = a_id[near][chosen]
                    selected_b = b_id[near][chosen]
                else:
                    selected_a = np.empty(0, dtype=np.int64)
                    selected_b = np.empty(0, dtype=np.int64)
                accumulator.add_assigned(tables, radius, selected_a, selected_b)
                if window == focus and radius == DETAIL_RADIUS_M:
                    focus_matched = int(counts.size)
                    focus_assigned = int(selected_a.size)
            ga, gb, gd, _, _, _ = grouped[max_radius]
            _store_nearest(forward[window], ga, gb, gd)
            if compare_assignment and assignment is None and window == focus and a_id.size:
                near = distance <= DETAIL_RADIUS_M
                if int(np.count_nonzero(near)) >= 15:
                    assignment = assignment_comparison(a_id[near], b_id[near], distance[near])
                    assignment["date"] = date
                    assignment["radius_m"] = DETAIL_RADIUS_M
                    assignment["max_delta_minutes"] = window
        daily.append(
            {
                "date": date,
                "status": "compared",
                "matched_reference_detections": focus_matched,
                "assigned_one_to_one_pairs": focus_assigned,
                "zero_detections": False,
            }
        )
    thresholds = []
    for window in windows:
        accumulator = accumulators[window]
        for radius in radii:
            masks = mutual_mask(forward[window], reverse[window], reference_names, radius)
            mutual = sum(int(np.count_nonzero(mask)) for mask in masks.values())
            mutual_values = []
            for name, mask in masks.items():
                rows = np.flatnonzero(mask)
                if rows.size == 0:
                    continue
                partner_code = forward[window][name]["code"][rows]
                partner_index = forward[window][name]["index"][rows]
                frp_a = np.asarray(tables[name].frp[rows], dtype=np.float64)
                frp_b = np.empty(rows.size, dtype=np.float64)
                for code, partner_name in CODE_SATELLITE.items():
                    chosen = partner_code == code
                    if np.any(chosen):
                        frp_b[chosen] = tables[partner_name].frp[partner_index[chosen]]
                positive = (frp_a > 0.0) & (frp_b > 0.0)
                if np.any(positive):
                    mutual_values.append(frp_b[positive] / frp_a[positive])
            payload = _threshold_payload(accumulator, radius, mutual, _ratio_record(_concat(mutual_values, np.float64)))
            payload["max_delta_minutes"] = window
            if radius == DETAIL_RADIUS_M:
                payload["frp_directed"]["by_daynight"] = _stratum_ratios(
                    _concat(accumulator.ratio_parts[radius], np.float64),
                    _concat(accumulator.ratio_daynight[radius], np.int8),
                    DAYNIGHT_LABELS,
                )
                payload["frp_directed"]["by_reference_confidence"] = _confidence_strata(
                    tables, reference_names, accumulator, radius, "reference"
                )
                payload["frp_directed"]["by_partner_confidence"] = _confidence_strata(
                    tables, other_names, accumulator, radius, "partner"
                )
                payload["frp_directed"]["reference_frp_mw"] = _quantile(_concat(accumulator.frp_reference, np.float64))
                payload["frp_directed"]["partner_frp_mw"] = _quantile(_concat(accumulator.frp_partner, np.float64))
                payload["frp_directed"]["reference_scan_km"] = _quantile(_concat(accumulator.scan_reference, np.float64))
                payload["frp_directed"]["partner_scan_km"] = _quantile(_concat(accumulator.scan_partner, np.float64))
                payload["one_to_one_frp"] = {
                    "ratio_other_over_reference": _ratio_record(_concat(accumulator.assigned_ratio_parts, np.float64)),
                    "excluded_nonpositive_frp_pairs": int(accumulator.assigned_nonpositive),
                    "zero_frp_rows_removed_from_source": False,
                    "one_to_one_is_physical_truth": False,
                }
            thresholds.append(payload)
    return {
        "satellite_a": reference,
        "satellite_b": other,
        "label": f"{DISPLAY[reference]} and {DISPLAY[other]}",
        "windows_minutes": list(windows),
        "detail_window_minutes": focus,
        "compared_dates": sum(1 for row in daily if row["status"] == "compared"),
        "excluded_dates": excluded,
        "reference_rows_by_satellite": accumulators[windows[0]].reference_rows_by_satellite,
        "daily": daily,
        "thresholds": thresholds,
        "assignment_comparison": assignment or {"status": "not_run", "same_fire": "not_assessed", "subset_is_the_full_month": False},
        "same_fire": "not_assessed",
        "zero_detections": False,
        "missing_dates_filled": False,
    }


def _confidence_strata(tables, names, accumulator, radius: float, side: str) -> list[dict[str, object]]:
    values = _concat(accumulator.ratio_parts[radius], np.float64)
    labels = _concat(accumulator.ratio_reference_class[radius] if side == "reference" else accumulator.ratio_partner_class[radius], np.int8)
    if len(names) == 1:
        return _stratum_ratios(values, labels, _class_names(names[0]))
    # MODIS keeps Terra and Aqua on the published classes. The class codes match.
    return _stratum_ratios(values, labels, _class_names(names[0]))


def analyze_tables(
    tables: dict[str, ObservationTable],
    *,
    pairs: tuple[tuple[tuple[str, str], tuple[int, ...]], ...] = PAIR_WINDOWS,
    radii_m: tuple[float, ...] = RADII_M,
    days: list[int] | None = None,
    compare_assignment: bool = True,
) -> list[dict[str, object]]:
    results = []
    for pair, windows in pairs:
        print(f"pair {pair[0]} {pair[1]}", flush=True)
        results.append(
            analyze_pair(
                tables,
                pair,
                windows,
                radii_m=radii_m,
                days=days,
                compare_assignment=compare_assignment,
            )
        )
    return results


def _sensor_rows(tables: dict[str, ObservationTable]) -> list[dict[str, object]]:
    rows = []
    for name in ("Terra", "Aqua", "SNPP", "N20", "N21"):
        table = tables[name]
        positive = table.frp[table.frp > 0]
        rows.append(
            {
                "satellite": name,
                "label": DISPLAY[name],
                "rows": table.count,
                "median_frp_mw": None if positive.size == 0 else float(np.median(positive)),
                "nonpositive_frp_rows": int(np.count_nonzero(table.frp <= 0)),
                "nonpositive_rows_removed": False,
            }
        )
    return rows


def _peak_working_set() -> int | None:
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_process = kernel32.GetCurrentProcess
    get_process.restype = wintypes.HANDLE
    query = kernel32.K32GetProcessMemoryInfo
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    query.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    if not query(get_process(), ctypes.byref(counters), counters.cb):
        return None
    return int(counters.PeakWorkingSetSize)


def build_report(tables: dict[str, ObservationTable], *, load_seconds: float) -> dict[str, object]:
    started = perf_counter()
    pairs = analyze_tables(tables)
    current, peak = tracemalloc.get_traced_memory()
    return {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sensors": _sensor_rows(tables),
        "pairs": pairs,
        "parameters": {
            "radii_m": list(RADII_M),
            "pair_windows_minutes": {f"{pair[0]}-{pair[1]}": list(windows) for pair, windows in PAIR_WINDOWS},
            "detail_radius_m": DETAIL_RADIUS_M,
            "index": "scipy.spatial.cKDTree on ECEF coordinates, reused from the candidate-pair search",
            "separation": "great-circle length recovered from the ECEF chord",
            "one_to_one": "greedy by increasing distance within each UTC date, dates in calendar order, with a lock that persists across dates",
            "assignment_subset": "Hungarian assignment on at most 80 reference rows and 120 partners",
        },
        "processing_level": PROVENANCE,
        "modis_to_viirs_scaling_factor": None,
        "xgboost_trained": False,
        "h3_aggregation": False,
        "same_fire": "not_assessed",
        "missing_dates_filled": False,
        "performance": {
            "load_seconds": load_seconds,
            "analysis_seconds": perf_counter() - started,
            "peak_python_bytes": int(peak),
            "current_python_bytes": int(current),
            "peak_working_set_bytes": _peak_working_set(),
        },
    }


def _row(pair: dict[str, object], radius: float, window: int) -> dict[str, object]:
    return next(
        item
        for item in pair["thresholds"]
        if item["radius_m"] == radius and item["max_delta_minutes"] == window
    )


def _fmt(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Nearest-neighbor sensitivity, July 2024",
        "",
        "This report counts nearest archived rows inside stated distance and time limits. A nearest neighbor is not a confirmed common fire. A mutual nearest neighbor is not a confirmed common fire. A one-to-one assignment is a bookkeeping constraint, not a physical fire identity.",
        "",
        "## Method",
        "",
        "The search reuses the July candidate-pair index: Earth-centered coordinates on the same sphere, a `cKDTree`, and the great-circle length recovered from the chord. The reference sensor owns the UTC date. The other sensor may fall up to the pair's time window across midnight. One row is not copied into a second date.",
        "",
        "Directed nearest neighbor: for each reference row on a compared date, the closest other-sensor row inside the radius and the window. Rows with no such partner are unmatched.",
        "",
        "Mutual nearest neighbor: the partner's own nearest reference row is the same detection. The proportion uses the directed matches in the stated direction as the denominator.",
        "",
        "One-to-one assignment: within each UTC date, eligible pairs are taken in order of increasing separation. A detection already used on an earlier date is left out. Dates run from 1 July through 31 July, so a later, closer pair can lose to an earlier, longer pair. On one deterministic subset of at most 80 reference rows, that greedy rule is compared with a Hungarian assignment. The Hungarian result is not expanded to the full month.",
        "",
        "The windows are exploratory. Terra–Aqua and every MODIS–VIIRS pair use 30 minutes. S-NPP against NOAA-20 and NOAA-21 uses 30 and 60 minutes. NOAA-20 against NOAA-21 uses 60 minutes because those overpasses are about 50 minutes apart. None of these windows means the sensors observed at the same instant.",
        "",
        "A date is compared only when both sides have at least one row that UTC date. A date with no rows is excluded. It is not stored as zero matches and it is not zero fire activity. S-NPP dates that do contain rows are used only for those rows. Incomplete S-NPP delivery on 16, 24, and 29 July is not repaired.",
        "",
        PROVENANCE,
        "",
        "No MODIS-to-VIIRS scaling factor is calculated. FRP ratios use the other sensor divided by the reference sensor, and only when both values are positive. Zero and negative FRP rows stay in the source tables and in the match counts. They are left out of the ratio only. XGBoost is not trained. H3 is not applied. `same_fire` remains `not_assessed`.",
        "",
        "## Directed nearest neighbors at 1 km",
        "",
        "| Pair | Window (minutes) | Compared dates | Matched reference rows | Unmatched | Mutual | Mutual share | One-to-one | Ambiguous share |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for pair in report["pairs"]:
        window = int(pair["detail_window_minutes"])
        item = _row(pair, DETAIL_RADIUS_M, window)
        share = item["mutual_proportion_of_directed"]
        ambiguous = item["ambiguity"]["ambiguous_rate"]
        lines.append(
            f"| {pair['label']} | {window} | {pair['compared_dates']} | {item['matched_reference_detections']} | "
            f"{item['unmatched_reference_detections']} | {item['mutual_nearest_neighbors']} | "
            f"{_fmt(None if share is None else share * 100)}% | {item['assigned_one_to_one_pairs']} | "
            f"{_fmt(None if ambiguous is None else ambiguous * 100)}% |"
        )
    lines.extend(["", "## Sensitivity", ""])
    for pair in report["pairs"]:
        lines.append(f"### {pair['label']}")
        lines.append("")
        lines.append("| Window | Radius | Matched | Unmatched | Eligible pairs | Unique partners | Mutual | One-to-one | Ambiguous share | Nearest-distance bin (m) | Gap bin (m) |")
        lines.append("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
        for item in pair["thresholds"]:
            nearest = item["nearest_distance_m"]
            gap = item["nearest_minus_second_gap_m"]
            nearest_text = "n/a" if nearest["bin_start"] is None else f"{nearest['bin_start']:.0f}–{nearest['bin_end']:.0f}"
            gap_text = "n/a" if gap["bin_start"] is None else f"{gap['bin_start']:.0f}–{gap['bin_end']:.0f}"
            ambiguous = item["ambiguity"]["ambiguous_rate"]
            lines.append(
                f"| {item['max_delta_minutes']} | {item['radius_m']:.0f} | {item['matched_reference_detections']} | "
                f"{item['unmatched_reference_detections']} | {item['eligible_candidate_pairs']} | {item['unique_partner_detections']} | "
                f"{item['mutual_nearest_neighbors']} | {item['assigned_one_to_one_pairs']} | "
                f"{_fmt(None if ambiguous is None else ambiguous * 100)}% | {nearest_text} | {gap_text} |"
            )
        lines.append("")
        excluded = ", ".join(row["date"] for row in pair["excluded_dates"]) or "none"
        lines.append(f"Excluded dates: {excluded}.")
        lines.append("")
    lines.extend(
        [
            "Ambiguous share is the fraction of reference rows on compared dates that have two or more eligible partners. A single eligible partner is still not proof of one fire. Eligible-pair totals count every pair, so they are larger than the number of detections.",
            "",
            "The gap is the second-nearest distance minus the nearest distance, for reference rows that have at least two partners. A small gap means another archived row is nearly as close.",
            "",
            "## One-to-one comparison on a subset",
            "",
        ]
    )
    for pair in report["pairs"]:
        comparison = pair["assignment_comparison"]
        if comparison.get("status") != "compared":
            lines.append(f"{pair['label']}: no subset was compared.")
            continue
        lines.append(
            f"{pair['label']} on {comparison['date']} at {comparison['radius_m']:.0f} m and {comparison['max_delta_minutes']} minutes: "
            f"{comparison['reference_rows']} reference rows, {comparison['partner_rows']} partners, {comparison['edges']} edges. "
            f"Greedy assigned {comparison['greedy_assigned_pairs']} pairs totaling {comparison['greedy_distance_sum_m']:.1f} m. "
            f"Hungarian assigned {comparison['hungarian_assigned_pairs']} pairs totaling {comparison['hungarian_distance_sum_m']:.1f} m."
        )
    lines.extend(["", "## FRP ratios", ""])
    lines.append("The ratio is the other sensor's FRP divided by the reference sensor's FRP. It is calculated only when both values are positive. The quantiles describe this candidate sample. The rows are clustered, so the quantiles are not a confidence interval and not a harmonization coefficient.")
    lines.append("")
    lines.append("| Pair | Window | Radius | Positive pairs | Excluded non-positive | Median ratio | p10 | p90 |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for pair in report["pairs"]:
        for item in pair["thresholds"]:
            if item["radius_m"] not in {375.0, 1_000.0, 5_000.0}:
                continue
            ratio = item["frp_directed"]["ratio_other_over_reference"]
            lines.append(
                f"| {pair['label']} | {item['max_delta_minutes']} | {item['radius_m']:.0f} | {ratio['count']} | "
                f"{item['frp_directed']['excluded_nonpositive_frp_pairs']} | {_fmt(ratio['p50'], 3)} | {_fmt(ratio['p10'], 3)} | {_fmt(ratio['p90'], 3)} |"
            )
    lines.extend(["", "Day/night and confidence splits below use the 1 km directed nearest neighbors and the pair's detail window. MODIS classes are the published 0–29, 30–79, and 80–100 classes. VIIRS flags stay `l`, `n`, and `h`.", ""])
    for pair in report["pairs"]:
        item = _row(pair, DETAIL_RADIUS_M, int(pair["detail_window_minutes"]))
        frp = item["frp_directed"]
        lines.append(f"### {pair['label']}")
        lines.append("")
        lines.append(
            f"Median FRP among directed nearest neighbors, including non-positive values in the sample count: "
            f"reference {_fmt(frp['reference_frp_mw']['p50'])} MW (n={frp['reference_frp_mw']['count']}), "
            f"partner {_fmt(frp['partner_frp_mw']['p50'])} MW (n={frp['partner_frp_mw']['count']}). "
            f"Median scan { _fmt(frp['reference_scan_km']['p50'], 2)} km and {_fmt(frp['partner_scan_km']['p50'], 2)} km."
        )
        lines.append("")
        for title, key in (("Day/night", "by_daynight"), ("Reference confidence", "by_reference_confidence"), ("Partner confidence", "by_partner_confidence")):
            lines.append(f"{title}:")
            lines.append("")
            for stratum in frp[key]:
                lines.append(f"- {stratum['class']}: n={stratum['count']}, median ratio {_fmt(stratum['p50'], 3)}")
            lines.append("")
    performance = report["performance"]
    working = performance["peak_working_set_bytes"]
    lines.extend(
        [
            "## Performance",
            "",
            f"Load time: {performance['load_seconds']:.1f} s. Analysis time: {performance['analysis_seconds']:.1f} s. "
            f"Peak Python allocations traced: {performance['peak_python_bytes']} bytes. "
            f"Peak process working set: {working if working is not None else 'not returned'} bytes. "
            "Allocation tracing slows the CSV load.",
            "",
            "## Reproducibility",
            "",
            "From `backend/`, with the July CSVs already extracted:",
            "",
            "```bash",
            ".venv\\Scripts\\python -m fire_data.nearest_neighbor_analysis",
            "```",
            "",
            "The command reads the four monthly archives, writes this report, and writes the figures under `backend/reports/figures/nearest_neighbor_2024_07/`. It does not modify the CSVs.",
            "",
            "## Limitations",
            "",
            "- A nearest neighbor does not prove that the two rows observe the same fire.",
            "- A mutual nearest neighbor does not prove that the two rows observe the same fire.",
            "- One-to-one assignment is a computational constraint. Calendar order can keep an earlier pair and drop a later, closer pair that shares a detection.",
            "- The Hungarian comparison covers a small subset, not the 8 million rows.",
            "- Eligible-pair totals are not unique fires. One detection can have many partners.",
            "- Raw detection totals are not a measure of which sensor performs better.",
            "- Missing S-NPP dates are excluded. They are not zeros. Incomplete intervals on 16, 24, and 29 July are not repaired.",
            "- " + PROVENANCE,
            "- FRP ratios are not a scaling coefficient. Non-positive FRP values are excluded from the ratio and retained everywhere else.",
            "- No XGBoost model or H3 aggregation is produced.",
            "",
        ]
    )
    return "\n".join(lines)


def _finish(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _detail_rows(report: dict[str, object], radius: float) -> list[dict[str, object]]:
    rows = []
    for pair in report["pairs"]:
        rows.append(_row(pair, radius, int(pair["detail_window_minutes"])))
    return rows


def write_figures(report: dict[str, object], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = [
        _figure_matched_fraction(report, output_dir / "matched_fraction_by_radius.png"),
        _figure_ambiguity(report, output_dir / "ambiguity_1km.png"),
        _figure_distances(report, output_dir / "nearest_and_second_distance.png"),
        _figure_mutual_assignment(report, output_dir / "mutual_and_one_to_one.png"),
        _figure_ratios(report, output_dir / "frp_ratio_directed_1km.png"),
        _figure_daily(report, output_dir / "daily_directed_1km.png"),
        _figure_time(report, output_dir / "nearest_time_difference.png"),
    ]
    return [path.name for path in written]


def _figure_matched_fraction(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.4, 4.8), constrained_layout=True)
    for color, pair in zip(PAIR_COLORS, report["pairs"], strict=True):
        window = int(pair["detail_window_minutes"])
        rows = [item for item in pair["thresholds"] if item["max_delta_minutes"] == window]
        rows = sorted(rows, key=lambda item: item["radius_m"])
        population = rows[0]["reference_rows_on_compared_dates"] or 1
        fraction = [item["matched_reference_detections"] / population for item in rows]
        ax.plot([item["radius_m"] for item in rows], fraction, marker="o", color=color, label=pair["label"])
    ax.set_xlabel("Search radius (m)")
    ax.set_ylabel("Share of reference rows with a nearest neighbor")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def _figure_ambiguity(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 4.8), constrained_layout=True)
    labels = [pair["label"] for pair in report["pairs"]]
    keys = ("zero_candidates", "one_candidate", "two_to_five_candidates", "more_than_five_candidates")
    names = ("0 partners", "1 partner", "2–5 partners", "More than 5")
    colors = ("#d9d0c7", "#8c4a2f", "#2f6f8f", "#a33b4a")
    bottoms = np.zeros(len(report["pairs"]))
    rows = _detail_rows(report, DETAIL_RADIUS_M)
    for key, name, color in zip(keys, names, colors, strict=True):
        values = np.array([item["ambiguity"][key] for item in rows], dtype=float)
        ax.bar(np.arange(len(rows)), values, bottom=bottoms, color=color, label=name)
        bottoms += values
    ax.set_xticks(np.arange(len(labels)), labels, rotation=25, ha="right")
    ax.set_ylabel("Reference rows on compared dates")
    ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def _figure_distances(report: dict[str, object], path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), constrained_layout=True)
    chosen = [pair for pair in report["pairs"] if pair["satellite_a"] in {"Terra", "N20"}]
    centers = (DISTANCE_EDGES[:-1] + DISTANCE_EDGES[1:]) / 2.0
    for ax, pair in zip(axes, chosen, strict=False):
        item = _row(pair, 5_000.0, int(pair["detail_window_minutes"]))
        ax.step(centers, item["nearest_distance_histogram"], where="mid", label="Nearest", color="#8c4a2f")
        ax.step(centers, item["second_distance_histogram"], where="mid", label="Second nearest", color="#2f6f8f")
        ax.set_title(pair["label"])
        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Reference rows")
        ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def _figure_mutual_assignment(report: dict[str, object], path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), constrained_layout=True)
    for color, pair in zip(PAIR_COLORS, report["pairs"], strict=True):
        window = int(pair["detail_window_minutes"])
        rows = sorted((item for item in pair["thresholds"] if item["max_delta_minutes"] == window), key=lambda item: item["radius_m"])
        radii = [item["radius_m"] for item in rows]
        mutual = [0 if item["mutual_proportion_of_directed"] is None else item["mutual_proportion_of_directed"] for item in rows]
        axes[0].plot(radii, mutual, marker="o", color=color, label=pair["label"])
        axes[1].plot(radii, [item["assigned_one_to_one_pairs"] for item in rows], marker="o", color=color, label=pair["label"])
    axes[0].set_ylabel("Mutual share of directed nearest neighbors")
    axes[0].set_ylim(0, 1)
    axes[1].set_ylabel("One-to-one assigned pairs")
    for ax in axes:
        ax.set_xlabel("Search radius (m)")
    axes[1].legend(frameon=False, fontsize=7)
    _finish(fig, path)
    return path


def _figure_ratios(report: dict[str, object], path: Path) -> Path:
    chosen = []
    for pair in report["pairs"]:
        item = _row(pair, DETAIL_RADIUS_M, int(pair["detail_window_minutes"]))
        if item["frp_directed"]["ratio_other_over_reference"]["count"]:
            chosen.append((pair, item))
        if len(chosen) == 3:
            break
    if not chosen:
        chosen = [(report["pairs"][0], _row(report["pairs"][0], DETAIL_RADIUS_M, int(report["pairs"][0]["detail_window_minutes"])))]
    fig, axes = plt.subplots(1, len(chosen), figsize=(11.2, 4.2), constrained_layout=True)
    if len(chosen) == 1:
        axes = [axes]
    centers = np.sqrt(RATIO_EDGES[:-1] * RATIO_EDGES[1:])
    for ax, (pair, item) in zip(axes, chosen, strict=True):
        hist = item["frp_directed"]["ratio_other_over_reference"]["histogram"]
        ax.step(centers, hist, where="mid", color=COLORS["N20"])
        ax.set_xscale("log")
        ax.set_xlabel("Other FRP / reference FRP")
        ax.set_ylabel("Directed pairs")
        ax.set_title(pair["label"])
    _finish(fig, path)
    return path


def _figure_daily(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11.2, 4.8), constrained_layout=True)
    days = np.arange(1, 32)
    for color, pair in zip(PAIR_COLORS, report["pairs"], strict=True):
        by_date = {row["date"]: row for row in pair["daily"]}
        values = []
        for day in days:
            row = by_date.get(f"2024-07-{day:02d}")
            if row is None or row["status"] != "compared":
                values.append(np.nan)
            else:
                values.append(row["matched_reference_detections"])
        ax.plot(days, values, color=color, label=pair["label"], linewidth=1.3)
    ax.set_xlabel("July 2024 day (UTC)")
    ax.set_ylabel("Directed nearest neighbors at 1 km")
    ax.set_xticks(days[::2])
    ax.legend(frameon=False, fontsize=8, ncol=2)
    _finish(fig, path)
    return path


def _figure_time(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 4.6), constrained_layout=True)
    centers = (TIME_EDGES[:-1] + TIME_EDGES[1:]) / 2.0
    for color, pair in zip(PAIR_COLORS, report["pairs"], strict=True):
        item = _row(pair, 5_000.0, int(pair["detail_window_minutes"]))
        total = sum(item["time_histogram"]) or 1
        share = np.asarray(item["time_histogram"], dtype=float) / total
        ax.plot(centers, share, color=color, label=pair["label"])
    ax.set_xlabel("Time difference of the nearest neighbor (minutes)")
    ax.set_ylabel("Share of directed nearest neighbors")
    ax.legend(frameon=False, fontsize=8)
    _finish(fig, path)
    return path


def write_outputs(report: dict[str, object]) -> None:
    report["figures"] = write_figures(report, FIGURE_DIR)
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    tracemalloc.start()
    started = perf_counter()
    tables = load_tables()
    load_seconds = perf_counter() - started
    report = build_report(tables, load_seconds=load_seconds)
    write_outputs(report)
    print(
        f"pairs={len(report['pairs'])} load_s={report['performance']['load_seconds']:.1f} "
        f"analysis_s={report['performance']['analysis_seconds']:.1f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
