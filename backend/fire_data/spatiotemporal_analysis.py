"""July 2024 candidate pairs between MODIS and VIIRS detections.

A candidate pair is two archived rows, from two named sensors, whose great-circle
separation and acquisition-time difference fall inside a stated threshold.
It is not a confirmed fire and it is not a harmonization factor. Pair totals
are not fire totals: one row can belong to many pairs. A date with no rows is
left out of the pair total. It is not entered as zero.
"""

from __future__ import annotations

import json
import tracemalloc
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree

from fire_data.contract import COLUMNS
from fire_data.eda_figures import COLORS
from fire_data.eda_spatial import (
    EARTH_RADIUS_M,
    cell_area_km2,
    count_grid,
    lonlat_to_ecef,
)
from fire_data.fields import is_valid_acq_time
from fire_data.ingest import DESTINATION_DIR, period_dates
from fire_data.monthly_scan import ARCHIVES, EXPECTED_ROWS, ZERO_ROW_MEANING
from fire_data.readers import read_archive

RADII_M = (375.0, 750.0, 1_000.0, 2_000.0, 5_000.0)
WINDOWS_MIN = (5, 15, 30, 60)
PRIMARY = (1_000.0, 30)
TILE_DEGREES = 20.0
DISTANCE_EDGES = np.linspace(0.0, 5_000.0, 21)
TIME_EDGES = np.arange(0, 61, 1, dtype=np.float64)
FRP_EDGES = np.logspace(-1, 4, 25)
DAYNIGHT_LABELS = ("D-D", "D-N", "N-D", "N-N")
SENSOR_PAIRS = (
    ("Terra", "Aqua"),
    ("MODIS", "SNPP"),
    ("MODIS", "N20"),
    ("MODIS", "N21"),
    ("SNPP", "N20"),
    ("SNPP", "N21"),
    ("N20", "N21"),
)
DISPLAY = {
    "Terra": "Terra",
    "Aqua": "Aqua",
    "MODIS": "MODIS (Terra and Aqua)",
    "SNPP": "S-NPP",
    "N20": "NOAA-20",
    "N21": "NOAA-21",
}
VIIRS_FLAGS = ("l", "n", "h")
REPORT_JSON = Path(__file__).resolve().parents[1] / "reports" / "spatiotemporal_analysis_2024_07.json"
REPORT_MD = Path(__file__).resolve().parents[1] / "reports" / "spatiotemporal_analysis_2024_07.md"
FIGURE_DIR = Path(__file__).resolve().parents[1] / "reports" / "figures" / "spatiotemporal_2024_07"
PROVENANCE = (
    "NOAA-20 and NOAA-21 processing level is unresolved. The local filenames use fire_archive, "
    "while the FIRMS download readme says standard-quality data are not yet available for those sensors. "
    "The version column is not used as a processing stream."
)


class AnalysisError(ValueError):
    """The tables cannot support the requested candidate comparison."""


@dataclass
class ObservationTable:
    satellite: str
    instrument: str
    confidence_scale: str
    day: np.ndarray
    minute: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    frp: np.ndarray
    brightness: np.ndarray
    scan: np.ndarray
    track: np.ndarray
    daynight: np.ndarray
    confidence: np.ndarray

    def __post_init__(self) -> None:
        self.day = np.asarray(self.day, dtype=np.int8)
        self.minute = np.asarray(self.minute, dtype=np.int16)
        self.epoch = (self.day.astype(np.int32) - 1) * 1440 + self.minute.astype(np.int32)
        self.ecef = lonlat_to_ecef(self.latitude, self.longitude)
        self.confidence_labels = VIIRS_FLAGS if self.confidence_scale == "viirs_flag" else None

    @property
    def count(self) -> int:
        return int(self.day.size)

    def select(self, mask: np.ndarray) -> "ObservationTable":
        chosen = ObservationTable(
            satellite=self.satellite,
            instrument=self.instrument,
            confidence_scale=self.confidence_scale,
            day=self.day[mask],
            minute=self.minute[mask],
            latitude=self.latitude[mask],
            longitude=self.longitude[mask],
            frp=self.frp[mask],
            brightness=self.brightness[mask],
            scan=self.scan[mask],
            track=self.track[mask],
            daynight=self.daynight[mask],
            confidence=self.confidence[mask],
        )
        return chosen

    def on_days(self, days: list[int]) -> "ObservationTable":
        if not days or self.count == 0:
            return self.select(np.zeros(self.count, dtype=bool))
        return self.select(np.isin(self.day, np.asarray(days, dtype=np.int8)))

    def count_on(self, day: int) -> int:
        if self.count == 0:
            return 0
        return int(np.count_nonzero(self.day == day))


def geodesic_m_from_chord(chord_m: np.ndarray) -> np.ndarray:
    """Great-circle length from an ECEF chord on the same sphere as the tree."""

    ratio = np.clip(np.asarray(chord_m, dtype=np.float64) / (2.0 * EARTH_RADIUS_M), 0.0, 1.0)
    return 2.0 * EARTH_RADIUS_M * np.arcsin(ratio)


def chord_limit_m(geodesic_m: float) -> float:
    """ECEF chord whose great-circle length is ``geodesic_m``."""

    if geodesic_m <= 0:
        raise AnalysisError("Spatial threshold must be positive")
    return float(2.0 * EARTH_RADIUS_M * np.sin(float(geodesic_m) / (2.0 * EARTH_RADIUS_M)))


def _search_margin(south: float, north: float) -> tuple[float, float]:
    """Latitude and longitude padding that stays outside a 5 km great-circle search."""

    margin_lat = float(np.degrees(5_000.0 / EARTH_RADIUS_M) * 2.0)
    farthest = min(89.0, max(abs(south - margin_lat), abs(north + margin_lat)))
    cosine = max(float(np.cos(np.radians(farthest))), 0.05)
    return margin_lat, margin_lat / cosine


def _lon_in_window(longitude: np.ndarray, west: float, east: float) -> np.ndarray:
    span = east - west
    if span >= 360.0:
        return np.ones(longitude.shape, dtype=bool)
    lon360 = np.mod(longitude + 180.0, 360.0)
    start = np.mod(west + 180.0, 360.0)
    stop = np.mod(east + 180.0, 360.0)
    if start <= stop:
        return (lon360 >= start) & (lon360 <= stop)
    return (lon360 >= start) | (lon360 <= stop)


def _tile_index(latitude: np.ndarray, longitude: np.ndarray, tile: float) -> tuple[np.ndarray, np.ndarray]:
    lat = np.clip(latitude, -90.0, 90.0 - 1e-9)
    lon = np.clip(longitude, -180.0, 180.0 - 1e-9)
    lat_i = np.floor((lat + 90.0) / tile).astype(np.int16)
    lon_i = np.floor((lon + 180.0) / tile).astype(np.int16)
    return lat_i, lon_i


def candidate_pairs(
    ecef_a: np.ndarray,
    epoch_a: np.ndarray,
    latitude_a: np.ndarray,
    longitude_a: np.ndarray,
    ecef_b: np.ndarray,
    epoch_b: np.ndarray,
    latitude_b: np.ndarray,
    longitude_b: np.ndarray,
    *,
    max_geodesic_m: float,
    max_delta_minutes: int,
    tile_degrees: float = TILE_DEGREES,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Pairs inside the maximum great-circle radius and absolute time window.

    Indices refer to the arrays passed in. The tree stores only neighbors inside
    the chord for ``max_geodesic_m``. It does not build a full distance matrix.
    """

    count_a = int(len(epoch_a))
    count_b = int(len(epoch_b))
    empty = (
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.int64),
        np.empty(0, dtype=np.float64),
        np.empty(0, dtype=np.int32),
    )
    if count_a == 0 or count_b == 0 or max_geodesic_m <= 0 or max_delta_minutes < 0:
        return empty
    chord_limit = chord_limit_m(max_geodesic_m)
    lat_i, lon_i = _tile_index(latitude_a, longitude_a, tile_degrees)
    keys = np.unique(lat_i.astype(np.int32) * 1000 + lon_i.astype(np.int32))
    parts_a: list[np.ndarray] = []
    parts_b: list[np.ndarray] = []
    parts_distance: list[np.ndarray] = []
    parts_delta: list[np.ndarray] = []
    lat_bins = int(round(180.0 / tile_degrees))
    lon_bins = int(round(360.0 / tile_degrees))
    for key in keys:
        lat_bin = int(key // 1000)
        lon_bin = int(key % 1000)
        if lat_bin < 0 or lat_bin >= lat_bins or lon_bin < 0 or lon_bin >= lon_bins:
            continue
        south = -90.0 + lat_bin * tile_degrees
        north = south + tile_degrees
        west = -180.0 + lon_bin * tile_degrees
        east = west + tile_degrees
        margin_lat, margin_lon = _search_margin(south, north)
        owned = np.flatnonzero((lat_i == lat_bin) & (lon_i == lon_bin))
        if owned.size == 0:
            continue
        near_b = np.flatnonzero(
            (latitude_b >= south - margin_lat)
            & (latitude_b <= north + margin_lat)
            & _lon_in_window(longitude_b, west - margin_lon, east + margin_lon)
        )
        if near_b.size == 0:
            continue
        found = cKDTree(ecef_b[near_b]).sparse_distance_matrix(
            cKDTree(ecef_a[owned]),
            max_distance=chord_limit,
            output_type="ndarray",
        )
        if found.size == 0:
            continue
        delta = np.abs(epoch_a[owned][found["j"]] - epoch_b[near_b][found["i"]]).astype(np.int32)
        keep = delta <= max_delta_minutes
        if not np.any(keep):
            continue
        distance = geodesic_m_from_chord(found["v"][keep])
        inside = distance <= max_geodesic_m + 1e-6
        if not np.any(inside):
            continue
        parts_a.append(owned[found["j"][keep][inside]].astype(np.int64, copy=False))
        parts_b.append(near_b[found["i"][keep][inside]].astype(np.int64, copy=False))
        parts_distance.append(distance[inside])
        parts_delta.append(delta[keep][inside])
    if not parts_a:
        return empty
    return (
        np.concatenate(parts_a),
        np.concatenate(parts_b),
        np.concatenate(parts_distance),
        np.concatenate(parts_delta),
    )


def _members(name: str) -> tuple[str, ...]:
    if name == "MODIS":
        return ("Terra", "Aqua")
    return (name,)


def _confidence_counts(table: ObservationTable, mask: np.ndarray) -> dict[str, int]:
    """Native confidence labels. VIIRS flags are not turned into scores."""

    if table.count == 0 or not np.any(mask):
        return {}
    codes = table.confidence[mask]
    if table.confidence_scale == "viirs_flag":
        hist = np.bincount(codes, minlength=len(VIIRS_FLAGS))
        return {flag: int(hist[index]) for index, flag in enumerate(VIIRS_FLAGS) if hist[index]}
    hist = np.bincount(codes, minlength=101)
    return {str(index): int(hist[index]) for index in range(hist.size) if hist[index]}


def _pair_grid(lat_a: np.ndarray, lon_a: np.ndarray, lat_b: np.ndarray, lon_b: np.ndarray) -> np.ndarray:
    lat = (lat_a + lat_b) / 2.0
    lon = np.degrees(
        np.arctan2(
            np.sin(np.radians(lon_a)) + np.sin(np.radians(lon_b)),
            np.cos(np.radians(lon_a)) + np.cos(np.radians(lon_b)),
        )
    )
    lat_bin = np.clip(np.floor((lat + 90.0) / 2.0).astype(np.int32), 0, 89)
    lon_bin = np.clip(np.floor((np.clip(lon, -180.0, 179.999999) + 180.0) / 2.0).astype(np.int32), 0, 179)
    grid = np.zeros((90, 180), dtype=np.int64)
    np.add.at(grid, (lat_bin, lon_bin), 1)
    return grid


def match_sensor_pair(
    tables: dict[str, ObservationTable],
    pair: tuple[str, str],
    day: int,
    *,
    radii_m: tuple[float, ...] = RADII_M,
    windows_min: tuple[int, ...] = WINDOWS_MIN,
) -> dict[str, object]:
    """Compare one UTC date. Absent sides stay out of the candidate total."""

    reference, other = pair
    radii = tuple(sorted(float(radius) for radius in radii_m))
    windows = tuple(sorted(int(window) for window in windows_min))
    keys = [(radius, window) for radius in radii for window in windows]
    reference_rows = sum(tables[name].count_on(day) for name in _members(reference) if name in tables)
    other_rows = tables[other].count_on(day) if other in tables else 0
    date = f"2024-07-{day:02d}"
    if reference_rows == 0 or other_rows == 0:
        if reference_rows == 0 and other_rows == 0:
            status = "both_absent"
        elif reference_rows == 0:
            status = "reference_absent"
        else:
            status = "other_absent"
        return {
            "date": date,
            "status": status,
            "candidate_pairs": None,
            "reference_rows": reference_rows,
            "other_rows": other_rows,
            "thresholds": {f"{int(radius)}_{window}": None for radius, window in keys},
            "zero_detections": False,
        }
    neighbor_days = [value for value in (day - 1, day, day + 1) if 1 <= value <= 31]
    other_view = tables[other].on_days(neighbor_days)
    max_radius = radii[-1]
    max_window = windows[-1]
    counts = {key: 0 for key in keys}
    unique_reference = {key: 0 for key in keys}
    unique_other = {key: np.zeros(other_view.count, dtype=bool) for key in keys}
    daynight = {key: np.zeros(4, dtype=np.int64) for key in keys}
    joint = np.zeros((DISTANCE_EDGES.size - 1, TIME_EDGES.size - 1), dtype=np.int64)
    frp_hist = np.zeros((FRP_EDGES.size - 1, FRP_EDGES.size - 1), dtype=np.int64)
    pair_grid = np.zeros((90, 180), dtype=np.int64)
    reference_confidence: Counter[str] = Counter()
    nonpositive_frp_pairs = 0
    for name in _members(reference):
        reference_view = tables[name].on_days([day])
        if reference_view.count == 0:
            continue
        idx_a, idx_b, distance, delta = candidate_pairs(
            reference_view.ecef,
            reference_view.epoch,
            reference_view.latitude,
            reference_view.longitude,
            other_view.ecef,
            other_view.epoch,
            other_view.latitude,
            other_view.longitude,
            max_geodesic_m=max_radius,
            max_delta_minutes=max_window,
        )
        if idx_a.size == 0:
            continue
        joint += np.histogram2d(
            np.minimum(distance, DISTANCE_EDGES[-1]),
            np.minimum(delta, TIME_EDGES[-1]),
            bins=[DISTANCE_EDGES, TIME_EDGES],
        )[0].astype(np.int64)
        for radius, window in keys:
            mask = (distance <= radius) & (delta <= window)
            if not np.any(mask):
                continue
            counts[(radius, window)] += int(mask.sum())
            seen = np.zeros(reference_view.count, dtype=bool)
            seen[idx_a[mask]] = True
            unique_reference[(radius, window)] += int(seen.sum())
            unique_other[(radius, window)][idx_b[mask]] = True
            code = reference_view.daynight[idx_a[mask]].astype(np.int16) * 2 + other_view.daynight[idx_b[mask]]
            daynight[(radius, window)] += np.bincount(code, minlength=4)
            if (radius, window) == PRIMARY or (PRIMARY not in keys and (radius, window) == (max_radius, max_window)):
                frp_a = reference_view.frp[idx_a[mask]]
                frp_b = other_view.frp[idx_b[mask]]
                positive = (frp_a > 0) & (frp_b > 0)
                nonpositive_frp_pairs += int(np.count_nonzero(~positive))
                if np.any(positive):
                    frp_hist += np.histogram2d(frp_a[positive], frp_b[positive], bins=[FRP_EDGES, FRP_EDGES])[0].astype(np.int64)
                pair_grid += _pair_grid(
                    reference_view.latitude[idx_a[mask]],
                    reference_view.longitude[idx_a[mask]],
                    other_view.latitude[idx_b[mask]],
                    other_view.longitude[idx_b[mask]],
                )
                reference_confidence.update(_confidence_counts(reference_view, seen))
    same_day_other = other_view.day == day
    primary_key = PRIMARY if PRIMARY in unique_other else (max_radius, max_window)
    other_confidence = _confidence_counts(other_view, unique_other[primary_key] & same_day_other)
    thresholds = {}
    for radius, window in keys:
        key = (radius, window)
        thresholds[f"{int(radius)}_{window}"] = {
            "radius_m": radius,
            "max_delta_minutes": window,
            "candidate_pairs": counts[key],
            "reference_detections_with_candidate": unique_reference[key],
            "other_detections_on_this_date_with_candidate": int(np.count_nonzero(unique_other[key] & same_day_other)),
            "daynight_pairs": {label: int(daynight[key][index]) for index, label in enumerate(DAYNIGHT_LABELS)},
        }
    return {
        "date": date,
        "status": "compared",
        "candidate_pairs": counts.get(PRIMARY, counts[(max_radius, max_window)]),
        "reference_rows": reference_rows,
        "other_rows": other_rows,
        "thresholds": thresholds,
        "joint_distance_time": joint,
        "frp_histogram": frp_hist,
        "pair_grid": pair_grid,
        "reference_confidence": dict(reference_confidence),
        "other_confidence": other_confidence,
        "nonpositive_frp_pairs": nonpositive_frp_pairs,
        "zero_detections": False,
        "same_fire": "not_assessed",
    }


def _clock(minute: int | None) -> str | None:
    if minute is None:
        return None
    hour, rest = divmod(int(minute), 60)
    return f"{hour:02d}{rest:02d}"


def _quantile(values: np.ndarray) -> dict[str, float | int | None]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"count": 0, "minimum": None, "p50": None, "p90": None, "maximum": None}
    qs = np.quantile(finite, [0.0, 0.5, 0.9, 1.0], method="linear")
    return {"count": int(finite.size), "minimum": float(qs[0]), "p50": float(qs[1]), "p90": float(qs[2]), "maximum": float(qs[3])}


def _top_cells(latitude: np.ndarray, longitude: np.ndarray, limit: int = 8) -> list[dict[str, object]]:
    if latitude.size == 0:
        return []
    grid, lat_edges, lon_edges = count_grid(latitude, longitude, 1.0)
    area = cell_area_km2(lat_edges, lon_edges)
    flat = np.argsort(grid.ravel())[::-1]
    cells = []
    for position in flat[:limit]:
        count = int(grid.ravel()[position])
        if count == 0:
            break
        row, column = divmod(int(position), grid.shape[1])
        cells.append(
            {
                "latitude_floor": int(lat_edges[row]),
                "longitude_floor": int(lon_edges[column]),
                "detection_rows": count,
                "rows_per_1000_km2": float(count / area[row] * 1000.0),
            }
        )
    return cells


def load_tables() -> dict[str, ObservationTable]:
    """Read the July CSVs into one table per satellite. Files are not modified."""

    needed = (
        "latitude",
        "longitude",
        "brightness",
        "scan",
        "track",
        "acq_date",
        "acq_time",
        "satellite",
        "instrument",
        "confidence",
        "frp",
        "daynight",
    )
    index = {name: COLUMNS.index(name) for name in needed}
    tables: dict[str, ObservationTable] = {}
    for spec in ARCHIVES:
        path = DESTINATION_DIR / spec["relative_csv"]
        if not path.is_file():
            raise AnalysisError(f"Monthly archive is not available: {path}")
        capacity = int(EXPECTED_ROWS[str(spec["sensor"])])
        day = np.empty(capacity, dtype=np.int8)
        minute = np.empty(capacity, dtype=np.int16)
        latitude = np.empty(capacity, dtype=np.float64)
        longitude = np.empty(capacity, dtype=np.float64)
        frp = np.empty(capacity, dtype=np.float64)
        brightness = np.empty(capacity, dtype=np.float64)
        scan = np.empty(capacity, dtype=np.float64)
        track = np.empty(capacity, dtype=np.float64)
        daynight = np.empty(capacity, dtype=np.int8)
        confidence = np.empty(capacity, dtype=np.int16)
        satellite_code = np.empty(capacity, dtype=np.int8)
        instrument_by_satellite: dict[str, str] = {}
        scale = str(spec["confidence"])
        satellite_index = {name: code for code, name in enumerate(sorted(spec["satellites"]))}
        written = 0
        with read_archive(path) as (header, rows):
            if tuple(header) != COLUMNS:
                raise AnalysisError(f"{path.name} header does not match the local contract")
            for line_number, row in rows:
                if len(row) != len(COLUMNS):
                    raise AnalysisError(f"{path.name} line {line_number} does not have {len(COLUMNS)} fields")
                if written >= capacity:
                    raise AnalysisError(f"{path.name} has more rows than the ingestion manifest")
                date_text = row[index["acq_date"]]
                clock = row[index["acq_time"]]
                if not date_text.startswith("2024-07-") or not is_valid_acq_time(clock):
                    raise AnalysisError(f"{path.name} line {line_number} has an unexpected acquisition time")
                day_number = int(date_text[8:10])
                hour = int(clock[:2])
                minute_part = int(clock[2:])
                satellite = row[index["satellite"]]
                if satellite not in spec["satellites"]:
                    raise AnalysisError(f"{path.name} line {line_number} has satellite {satellite}")
                flag = row[index["confidence"]]
                if scale == "viirs_lnh":
                    if flag not in VIIRS_FLAGS:
                        raise AnalysisError(f"{path.name} line {line_number} has an unexpected VIIRS flag")
                    confidence_code = VIIRS_FLAGS.index(flag)
                else:
                    if not flag.isdigit() or not 0 <= int(flag) <= 100:
                        raise AnalysisError(f"{path.name} line {line_number} has an unexpected MODIS confidence")
                    confidence_code = int(flag)
                night = row[index["daynight"]]
                if night not in {"D", "N"}:
                    raise AnalysisError(f"{path.name} line {line_number} has an unexpected day/night flag")
                day[written] = day_number
                minute[written] = hour * 60 + minute_part
                latitude[written] = float(row[index["latitude"]])
                longitude[written] = float(row[index["longitude"]])
                frp[written] = float(row[index["frp"]])
                brightness[written] = float(row[index["brightness"]])
                scan[written] = float(row[index["scan"]])
                track[written] = float(row[index["track"]])
                daynight[written] = 0 if night == "D" else 1
                confidence[written] = confidence_code
                satellite_code[written] = satellite_index[satellite]
                instrument_by_satellite.setdefault(satellite, row[index["instrument"]])
                written += 1
        if written != capacity:
            raise AnalysisError(f"{path.name} has {written} rows; the manifest records {capacity}")
        ordered = sorted(spec["satellites"])
        confidence_scale = "viirs_flag" if scale == "viirs_lnh" else "modis_0_100"
        for code, satellite in enumerate(ordered):
            mask = satellite_code == code
            tables[satellite] = _masked_table(
                satellite,
                instrument_by_satellite[satellite],
                confidence_scale,
                day,
                minute,
                latitude,
                longitude,
                frp,
                brightness,
                scan,
                track,
                daynight,
                confidence,
                mask,
            )
    return tables


def _masked_table(
    satellite: str,
    instrument: str,
    scale: str,
    day: np.ndarray,
    minute: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    frp: np.ndarray,
    brightness: np.ndarray,
    scan: np.ndarray,
    track: np.ndarray,
    daynight: np.ndarray,
    confidence: np.ndarray,
    mask: np.ndarray,
) -> ObservationTable:
    return ObservationTable(
        satellite=satellite,
        instrument=instrument,
        confidence_scale=scale,
        day=day[mask],
        minute=minute[mask],
        latitude=latitude[mask],
        longitude=longitude[mask],
        frp=frp[mask],
        brightness=brightness[mask],
        scan=scan[mask],
        track=track[mask],
        daynight=daynight[mask],
        confidence=confidence[mask],
    )


def _threshold_keys(radii_m: tuple[float, ...], windows_min: tuple[int, ...]) -> list[tuple[float, int]]:
    return [(float(radius), int(window)) for radius in sorted(radii_m) for window in sorted(windows_min)]


def _histogram_bin(counts: np.ndarray, edges: np.ndarray) -> dict[str, float | int | None]:
    total = int(counts.sum())
    if total == 0:
        return {"count": 0, "bin_start": None, "bin_end": None}
    cumulative = np.cumsum(counts)
    index = int(np.searchsorted(cumulative, (total + 1) // 2, side="left"))
    index = min(index, counts.size - 1)
    return {"count": total, "bin_start": float(edges[index]), "bin_end": float(edges[index + 1])}


def summarize_days(pair: tuple[str, str], days: list[dict[str, object]]) -> dict[str, object]:
    """Sum compared dates only. An absent date stays null and is not added as zero."""

    compared = [day for day in days if day["status"] == "compared"]
    excluded = [{"date": day["date"], "status": day["status"]} for day in days if day["status"] != "compared"]
    sample = compared[0]["thresholds"] if compared else {}
    thresholds = []
    for key in sample:
        pair_count = sum(int(day["thresholds"][key]["candidate_pairs"]) for day in compared)
        reference_with = sum(int(day["thresholds"][key]["reference_detections_with_candidate"]) for day in compared)
        other_with = sum(int(day["thresholds"][key]["other_detections_on_this_date_with_candidate"]) for day in compared)
        daynight = {label: 0 for label in DAYNIGHT_LABELS}
        for day in compared:
            for label in DAYNIGHT_LABELS:
                daynight[label] += int(day["thresholds"][key]["daynight_pairs"][label])
        thresholds.append(
            {
                "radius_m": sample[key]["radius_m"],
                "max_delta_minutes": sample[key]["max_delta_minutes"],
                "candidate_pairs": pair_count,
                "reference_detections_with_candidate": reference_with,
                "other_detections_on_this_date_with_candidate": other_with,
                "reference_rows_on_compared_dates": sum(int(day["reference_rows"]) for day in compared),
                "other_rows_on_compared_dates": sum(int(day["other_rows"]) for day in compared),
                "daynight_pairs": daynight,
                "same_fire": "not_assessed",
                "candidate_pairs_are_unique_fires": False,
            }
        )
    return {
        "satellite_a": pair[0],
        "satellite_b": pair[1],
        "label": f"{DISPLAY[pair[0]]} and {DISPLAY[pair[1]]}",
        "same_fire": "not_assessed",
        "candidate_pairs_are_unique_fires": False,
        "compared_dates": len(compared),
        "excluded_dates": excluded,
        "thresholds": thresholds,
        "daily": [
            {
                "date": day["date"],
                "status": day["status"],
                "candidate_pairs_1km_30min": day["candidate_pairs"],
                "candidate_pairs_5km_60min": None
                if day["status"] != "compared"
                else day["thresholds"]["5000_60"]["candidate_pairs"],
                "reference_rows": day["reference_rows"],
                "other_rows": day["other_rows"],
                "zero_detections": False,
            }
            for day in days
        ],
    }


def sensor_profile(table: ObservationTable) -> dict[str, object]:
    days = []
    absent = []
    for day in range(1, 32):
        mask = table.day == day
        count = int(np.count_nonzero(mask))
        date = f"2024-07-{day:02d}"
        if count == 0:
            absent.append(date)
            days.append({"date": date, "rows": 0, "absent": True, "acq_time_min": None, "acq_time_max": None, "zero_detections": False})
            continue
        minutes = table.minute[mask]
        days.append(
            {
                "date": date,
                "rows": count,
                "absent": False,
                "acq_time_min": _clock(int(minutes.min())),
                "acq_time_max": _clock(int(minutes.max())),
                "zero_detections": False,
            }
        )
    confidence = _confidence_counts(table, np.ones(table.count, dtype=bool))
    return {
        "satellite": table.satellite,
        "display_name": DISPLAY[table.satellite],
        "instrument": table.instrument,
        "rows": table.count,
        "confidence_scale": table.confidence_scale,
        "confidence_counts": confidence,
        "confidence_comparable_across_sensors": False,
        "daynight_rows": {"D": int(np.count_nonzero(table.daynight == 0)), "N": int(np.count_nonzero(table.daynight == 1))},
        "frp": _quantile(table.frp),
        "brightness_k": _quantile(table.brightness),
        "scan_km": _quantile(table.scan),
        "track_km": _quantile(table.track),
        "absent_dates": absent,
        "absent_date_meaning": ZERO_ROW_MEANING,
        "daily": days,
        "geographic_concentration": _top_cells(table.latitude, table.longitude),
    }


def _merge_counts(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    merged = dict(left)
    for key, value in right.items():
        merged[key] = merged.get(key, 0) + int(value)
    return merged


def analyze(
    tables: dict[str, ObservationTable],
    *,
    radii_m: tuple[float, ...] = RADII_M,
    windows_min: tuple[int, ...] = WINDOWS_MIN,
) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    sensors = {name: sensor_profile(table) for name, table in tables.items()}
    pair_reports = []
    pair_grids: dict[str, np.ndarray] = {}
    for pair in SENSOR_PAIRS:
        print(f"pair {pair[0]} {pair[1]}", flush=True)
        days = []
        joint = np.zeros((DISTANCE_EDGES.size - 1, TIME_EDGES.size - 1), dtype=np.int64)
        frp_hist = np.zeros((FRP_EDGES.size - 1, FRP_EDGES.size - 1), dtype=np.int64)
        grid = np.zeros((90, 180), dtype=np.int64)
        reference_confidence: dict[str, int] = {}
        other_confidence: dict[str, int] = {}
        nonpositive = 0
        for day in range(1, 32):
            result = match_sensor_pair(tables, pair, day, radii_m=radii_m, windows_min=windows_min)
            if result["status"] == "compared":
                joint += result["joint_distance_time"]
                frp_hist += result["frp_histogram"]
                grid += result["pair_grid"]
                reference_confidence = _merge_counts(reference_confidence, result["reference_confidence"])
                other_confidence = _merge_counts(other_confidence, result["other_confidence"])
                nonpositive += int(result["nonpositive_frp_pairs"])
            days.append(
                {
                    "date": result["date"],
                    "status": result["status"],
                    "candidate_pairs": result["candidate_pairs"],
                    "reference_rows": result["reference_rows"],
                    "other_rows": result["other_rows"],
                    "thresholds": result["thresholds"],
                    "zero_detections": False,
                }
            )
        summary = summarize_days(pair, days)
        summary["distance_histogram_5km_60min"] = {
            "edges_m": [float(edge) for edge in DISTANCE_EDGES],
            "counts": [int(value) for value in joint.sum(axis=1)],
            "median_bin_m": _histogram_bin(joint.sum(axis=1), DISTANCE_EDGES),
        }
        summary["time_histogram_5km_60min"] = {
            "edges_minutes": [float(edge) for edge in TIME_EDGES],
            "counts": [int(value) for value in joint.sum(axis=0)],
            "median_bin_minutes": _histogram_bin(joint.sum(axis=0), TIME_EDGES),
        }
        summary["frp_histogram_1km_30min"] = {
            "edges_mw": [float(edge) for edge in FRP_EDGES],
            "counts": [[int(value) for value in row] for row in frp_hist],
            "nonpositive_frp_pairs_excluded": nonpositive,
            "counts_are_candidate_pairs": True,
        }
        summary["reference_confidence_for_unique_detections_1km_30min"] = reference_confidence
        summary["other_confidence_for_unique_detections_1km_30min"] = other_confidence
        summary["pair_concentration_top_cells_2deg"] = _top_pair_cells(grid)
        pair_reports.append(summary)
        pair_grids[f"{pair[0]}_{pair[1]}"] = grid
    return {"sensors": sensors, "pairs": pair_reports}, pair_grids


def _top_pair_cells(grid: np.ndarray, limit: int = 6) -> list[dict[str, object]]:
    cells = []
    order = np.argsort(grid.ravel())[::-1]
    for position in order[:limit]:
        count = int(grid.ravel()[position])
        if count == 0:
            break
        row, column = divmod(int(position), grid.shape[1])
        cells.append(
            {
                "latitude_floor": int(-90 + row * 2),
                "longitude_floor": int(-180 + column * 2),
                "candidate_pairs_1km_30min": count,
                "candidate_pairs_are_unique_fires": False,
            }
        )
    return cells


def _finish(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=140)
    plt.close(fig)


def write_figures(
    report: dict[str, object],
    tables: dict[str, ObservationTable],
    pair_grids: dict[str, np.ndarray],
    output_dir: Path,
) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = [
        _figure_daily_rows(report, output_dir / "daily_detection_rows.png"),
        _figure_daily_pairs(report, output_dir / "daily_candidate_pairs_1km_30min.png"),
        _figure_radius_bars(report, output_dir / "candidate_pairs_by_radius_30min.png"),
        _figure_distance_time(report, output_dir / "distance_time_5km_60min.png"),
        _figure_frp(report, output_dir / "frp_candidate_pairs_1km_30min.png"),
        _figure_daynight(report, output_dir / "daynight_candidate_pairs_1km_30min.png"),
        _figure_density(tables, output_dir / "detection_density_1deg.png"),
        _figure_concentration(pair_grids, output_dir / "candidate_pair_concentration_2deg.png"),
    ]
    return [path.name for path in written]


def _figure_daily_rows(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11.5, 5.0), constrained_layout=True)
    days = np.arange(1, 32)
    for name in ("Terra", "Aqua", "SNPP", "N20", "N21"):
        values = []
        for item in report["sensors"][name]["daily"]:
            values.append(np.nan if item["absent"] else item["rows"])
        ax.plot(days, values, color=COLORS[name], label=DISPLAY[name], linewidth=1.4)
    ax.set_xlabel("July 2024 day (UTC)")
    ax.set_ylabel("Detection rows")
    ax.set_title("Detection rows by acquisition date")
    ax.set_xticks(days[::2])
    ax.legend(frameon=False, ncol=5)
    ax.text(0.0, -0.2, "A break is a date with no row. It is not a zero-fire measurement.", transform=ax.transAxes, fontsize=8)
    _finish(fig, path)
    return path


def _figure_daily_pairs(report: dict[str, object], path: Path) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.2), sharex=True, constrained_layout=True)
    days = np.arange(1, 32)
    specs = (
        (axes[0], "candidate_pairs_1km_30min", "Candidate pairs at 1 km and 30 minutes"),
        (axes[1], "candidate_pairs_5km_60min", "Candidate pairs at 5 km and 60 minutes"),
    )
    for ax, field, title in specs:
        for item in report["pairs"]:
            values = [np.nan if row["status"] != "compared" else row[field] for row in item["daily"]]
            ax.plot(days, values, label=item["label"], linewidth=1.3)
        ax.set_ylabel("Candidate pairs")
        ax.set_title(title)
    axes[1].set_xlabel("July 2024 day (UTC)")
    axes[1].set_xticks(days[::2])
    axes[0].legend(frameon=False, fontsize=8, ncol=2)
    axes[1].text(
        0.0,
        -0.28,
        "A break means one sensor has no rows that date, so no candidate total is entered. A plotted zero means both sensors have rows and no pair met the threshold.",
        transform=axes[1].transAxes,
        fontsize=8,
    )
    _finish(fig, path)
    return path


def _figure_radius_bars(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11.5, 5.2), constrained_layout=True)
    radii = [375, 750, 1000, 2000, 5000]
    x = np.arange(len(radii))
    width = 0.11
    for index, item in enumerate(report["pairs"]):
        heights = []
        for radius in radii:
            match = next(row for row in item["thresholds"] if row["radius_m"] == radius and row["max_delta_minutes"] == 30)
            heights.append(match["candidate_pairs"])
        ax.bar(x + (index - 3) * width, heights, width=width, label=item["label"])
    ax.set_xticks(x, [str(radius) for radius in radii])
    ax.set_xlabel("Great-circle threshold (m)")
    ax.set_ylabel("Candidate pairs")
    ax.set_title("Candidate pairs within 30 minutes")
    ax.legend(frameon=False, fontsize=7, ncol=2)
    _finish(fig, path)
    return path


def _figure_distance_time(report: dict[str, object], path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    chosen = [item for item in report["pairs"] if item["satellite_a"] in {"Terra", "MODIS", "N20"} and item["satellite_b"] in {"Aqua", "SNPP", "N21"}]
    for item in chosen:
        distance = item["distance_histogram_5km_60min"]
        centers = (np.asarray(distance["edges_m"][:-1]) + np.asarray(distance["edges_m"][1:])) / 2.0
        total = sum(distance["counts"]) or 1
        axes[0].plot(centers, np.asarray(distance["counts"]) / total, label=item["label"], linewidth=1.3)
        time_hist = item["time_histogram_5km_60min"]
        time_centers = (np.asarray(time_hist["edges_minutes"][:-1]) + np.asarray(time_hist["edges_minutes"][1:])) / 2.0
        time_total = sum(time_hist["counts"]) or 1
        axes[1].plot(time_centers, np.asarray(time_hist["counts"]) / time_total, label=item["label"], linewidth=1.3)
    axes[0].set_xlabel("Great-circle separation (m)")
    axes[1].set_xlabel("Absolute acquisition-time difference (minutes)")
    axes[0].set_ylabel("Share of candidate pairs")
    axes[0].set_title("Inside 5 km and 60 minutes")
    axes[1].set_title("Inside 5 km and 60 minutes")
    axes[1].legend(frameon=False, fontsize=7)
    _finish(fig, path)
    return path


def _figure_frp(report: dict[str, object], path: Path) -> Path:
    chosen = []
    for item in report["pairs"]:
        total = sum(sum(row) for row in item["frp_histogram_1km_30min"]["counts"])
        if total > 0:
            chosen.append(item)
        if len(chosen) == 2:
            break
    if not chosen:
        chosen = report["pairs"][:1]
    fig, axes = plt.subplots(1, len(chosen), figsize=(11.0, 4.4), constrained_layout=True)
    if len(chosen) == 1:
        axes = [axes]
    for ax, item in zip(axes, chosen):
        hist = np.asarray(item["frp_histogram_1km_30min"]["counts"], dtype=np.float64)
        edges = np.asarray(item["frp_histogram_1km_30min"]["edges_mw"])
        show = np.log10(hist + 1.0)
        mesh = ax.pcolormesh(edges, edges, show.T, shading="auto")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(f"{DISPLAY[item['satellite_a']]} FRP (MW)")
        ax.set_ylabel(f"{DISPLAY[item['satellite_b']]} FRP (MW)")
        ax.set_title(item["label"])
        fig.colorbar(mesh, ax=ax, fraction=0.046, pad=0.04)
    _finish(fig, path)
    return path


def _figure_daynight(report: dict[str, object], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11.5, 5.0), constrained_layout=True)
    labels = [item["label"] for item in report["pairs"]]
    bottoms = np.zeros(len(labels))
    colors = ["#d4a017", "#7a6a4f", "#4d6d8a", "#243044"]
    for index, name in enumerate(DAYNIGHT_LABELS):
        heights = []
        for item in report["pairs"]:
            row = next(entry for entry in item["thresholds"] if entry["radius_m"] == 1000 and entry["max_delta_minutes"] == 30)
            heights.append(row["daynight_pairs"][name])
        ax.bar(np.arange(len(labels)), heights, bottom=bottoms, color=colors[index], label=name)
        bottoms += np.asarray(heights)
    ax.set_xticks(np.arange(len(labels)), labels, rotation=25, ha="right")
    ax.set_ylabel("Candidate pairs")
    ax.set_title("Day/night composition at 1 km and 30 minutes")
    ax.legend(frameon=False, ncol=4, title="Reference–other")
    _finish(fig, path)
    return path


def _figure_density(tables: dict[str, ObservationTable], path: Path) -> Path:
    fig, axes = plt.subplots(2, 3, figsize=(12.0, 6.4), constrained_layout=True)
    order = ("Terra", "Aqua", "SNPP", "N20", "N21")
    for ax, name in zip(axes.ravel(), order):
        table = tables[name]
        grid, _, _ = count_grid(table.latitude, table.longitude, 1.0)
        image = ax.imshow(np.log10(grid + 1.0), origin="lower", extent=(-180, 180, -90, 90), aspect="auto", cmap="inferno")
        ax.set_title(DISPLAY[name])
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    axes.ravel()[-1].axis("off")
    fig.suptitle("log10(detection rows + 1) in 1-degree cells")
    _finish(fig, path)
    return path


def _figure_concentration(pair_grids: dict[str, np.ndarray], path: Path) -> Path:
    keys = [key for key in ("MODIS_SNPP", "N20_N21", "Terra_Aqua") if key in pair_grids]
    fig, axes = plt.subplots(1, len(keys), figsize=(12.0, 3.8), constrained_layout=True)
    if len(keys) == 1:
        axes = [axes]
    for ax, key in zip(axes, keys):
        grid = pair_grids[key]
        image = ax.imshow(np.log10(grid + 1.0), origin="lower", extent=(-180, 180, -90, 90), aspect="auto", cmap="viridis")
        ax.set_title(key.replace("_", " / "))
        ax.set_xlabel("Longitude")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    _finish(fig, path)
    return path


def _primary_row(pair: dict[str, object]) -> dict[str, object]:
    return next(row for row in pair["thresholds"] if row["radius_m"] == 1000 and row["max_delta_minutes"] == 30)


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Spatial-temporal candidate pairs, July 2024",
        "",
        "This is an exploratory proximity analysis of archived MODIS and VIIRS detections. A candidate pair is not a confirmed common fire, and the pair count is not a fire count.",
        "",
        "## Method",
        "",
        "Each sensor is kept separate. MODIS in a cross-sensor pair means Terra and Aqua together, with each row keeping its own satellite name. Terra versus Aqua is a separate pair.",
        "",
        f"Coordinates are converted to Earth-centered Cartesian positions on a sphere of radius {EARTH_RADIUS_M:.1f} m, the same sphere used by the one-day proximity count. A `cKDTree` returns neighbors inside the chord length that corresponds to a 5 km great circle. The reported separation is the great-circle length recovered from that chord. The search is partitioned into 20-degree tiles so the full distance matrix is not built. Pairs are then kept for 375 m, 750 m, 1 km, 2 km, and 5 km, and for 5, 15, 30, and 60 minutes.",
        "",
        "The date of the reference sensor owns the pair. The other sensor may fall up to 60 minutes earlier or later, including across UTC midnight. One detection can enter many pairs. Thresholds are search radii, not sensor footprints. VIIRS I-band pixels are about 375 m at nadir and grow with scan angle. MODIS pixels are about 1 km at nadir. Those sizes are not applied as a match rule.",
        "",
        "A date is compared only when both sides have at least one row that UTC date. A date with no rows is excluded. It is not stored as zero candidate pairs and it is not a measurement of zero fire activity. S-NPP dates that do contain rows are compared only for those rows. The coverage investigation found incomplete S-NPP delivery on 16, 24, and 29 July; this analysis does not fill those intervals.",
        "",
        PROVENANCE,
        "",
        "No MODIS-to-VIIRS scaling factor is calculated. XGBoost is not trained. H3 is not applied. `same_fire` remains `not_assessed`.",
        "",
        "## Sensors",
        "",
        "| Satellite | Rows | Absent UTC dates | Scan median (km) | FRP median (MW) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name in ("Terra", "Aqua", "SNPP", "N20", "N21"):
        sensor = report["sensors"][name]
        absent = ", ".join(sensor["absent_dates"]) if sensor["absent_dates"] else "none"
        lines.append(
            f"| {DISPLAY[name]} | {sensor['rows']} | {absent} | {sensor['scan_km']['p50']:.3f} | {sensor['frp']['p50']:.3f} |"
        )
    lines.extend(
        [
            "",
            "MODIS confidence remains the stored 0–100 value. VIIRS confidence remains `l`, `n`, or `h`. Those scales are not converted into one score.",
            "",
            "Geographic concentration in the JSON is the 1-degree cells with the most detection rows. Equal-degree cells are not equal-area cells. The row count is not a fire count.",
            "",
            "## Candidate pairs at 1 km and 30 minutes",
            "",
            "| Pair | Compared dates | Excluded dates | Candidate pairs | Reference rows with a candidate | Other rows on the date with a candidate |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in report["pairs"]:
        primary = _primary_row(item)
        lines.append(
            "| {label} | {compared} | {excluded} | {pairs} | {reference} | {other} |".format(
                label=item["label"],
                compared=item["compared_dates"],
                excluded=len(item["excluded_dates"]),
                pairs=primary["candidate_pairs"],
                reference=primary["reference_detections_with_candidate"],
                other=primary["other_detections_on_this_date_with_candidate"],
            )
        )
    lines.extend(["", "## Patterns", ""])
    for item in report["pairs"]:
        primary = _primary_row(item)
        wide = next(row for row in item["thresholds"] if row["radius_m"] == 5000 and row["max_delta_minutes"] == 60)
        distance_bin = item["distance_histogram_5km_60min"]["median_bin_m"]
        time_bin = item["time_histogram_5km_60min"]["median_bin_minutes"]
        if distance_bin["count"]:
            distance_text = (
                f"Among pairs inside 5 km and 60 minutes, the median separation falls in "
                f"{distance_bin['bin_start']:.0f}–{distance_bin['bin_end']:.0f} m and the median time difference falls in "
                f"{time_bin['bin_start']:.0f}–{time_bin['bin_end']:.0f} minutes."
            )
        else:
            distance_text = "No candidate pairs fall inside 5 km and 60 minutes on the compared dates."
        excluded = ", ".join(row["date"] for row in item["excluded_dates"]) or "none"
        lines.append(
            f"{item['label']}: {primary['candidate_pairs']} candidate pairs at 1 km and 30 minutes "
            f"across {item['compared_dates']} compared dates, and {wide['candidate_pairs']} at 5 km and 60 minutes. "
            f"{primary['reference_detections_with_candidate']} reference rows on compared dates have at least one candidate, "
            f"out of {primary['reference_rows_on_compared_dates']} reference rows. "
            f"{distance_text} Excluded dates: {excluded}."
        )
        lines.append("")
    distance_bins = []
    for item in report["pairs"]:
        distance_bin = item["distance_histogram_5km_60min"]["median_bin_m"]
        if distance_bin["bin_start"] is not None:
            distance_bins.append((distance_bin["bin_start"], distance_bin["bin_end"]))
    if distance_bins and all(bin_ == distance_bins[0] for bin_ in distance_bins):
        area = (
            f"The median separation inside the 5 km window falls in {distance_bins[0][0]:.0f}–{distance_bins[0][1]:.0f} m for every pair. "
            "A 5 km disk contains more ground toward its outer edge, so that shared bin is not evidence of a preferred separation."
        )
    else:
        area = "A 5 km disk contains more ground toward its outer edge, so a median separation inside that disk is not a preferred match distance."
    n20_n21 = next(item for item in report["pairs"] if item["satellite_a"] == "N20" and item["satellite_b"] == "N21")
    n20_time = n20_n21["time_histogram_5km_60min"]["median_bin_minutes"]
    n20_primary = _primary_row(n20_n21)
    if n20_time["bin_start"] is None:
        offset = "NOAA-20 and NOAA-21 have no candidate pairs inside the 5 km and 60 minute window."
    elif n20_primary["candidate_pairs"] == 0:
        offset = (
            "NOAA-20 and NOAA-21 have no candidate pairs inside 30 minutes. "
            "Inside 5 km and 60 minutes, their median time difference falls in "
            f"{n20_time['bin_start']:.0f}–{n20_time['bin_end']:.0f} minutes. "
            "The shorter windows are empty because those acquisitions are farther apart than 30 minutes, not because the rows are far apart on the ground."
        )
    else:
        offset = (
            "Inside 5 km and 60 minutes, the NOAA-20 and NOAA-21 median time difference falls in "
            f"{n20_time['bin_start']:.0f}–{n20_time['bin_end']:.0f} minutes."
        )
    lines.extend(
        [
            area,
            "",
            offset,
            "",
            "Day/night labels on a pair are the stored flags of the two rows. They describe the observations, not a shared fire.",
            "",
            "FRP histograms count candidate pairs, so a row in several pairs is counted more than once. FRP is not fire size. Non-positive FRP values are left out of the log histogram and counted separately.",
            "",
            "## Performance",
            "",
            f"Load time: {report['performance']['load_seconds']:.1f} s. Match and summary time: {report['performance']['match_seconds']:.1f} s. "
            f"Peak Python allocations traced: {report['performance']['peak_python_bytes']} bytes. "
            "The Windows working-set counter was not returned. The traced allocation peak is the memory figure for this run. "
            "Tracing allocations slows the CSV load.",
            "",
            "## Reproducibility",
            "",
            "From `backend/`, with the July CSVs already extracted:",
            "",
            "```bash",
            ".venv\\Scripts\\python -m fire_data.spatiotemporal_analysis",
            "```",
            "",
            "The command reads the four monthly archives, writes this report, and writes the figures under `backend/reports/figures/spatiotemporal_2024_07/`. It does not modify the CSVs.",
            "",
            "## Limitations",
            "",
            "- A candidate pair does not prove that the two rows observe the same fire.",
            "- Pair counts are not unique fires. One detection can belong to many pairs.",
            "- Raw detection totals are not a measure of which sensor performs better. The sensors differ in pixel size, scan growth, and overpass time.",
            "- Missing S-NPP dates are excluded. They are not zeros.",
            "- Incomplete S-NPP intervals on 16, 24, and 29 July are not repaired.",
            "- " + PROVENANCE,
            "- No global scaling factor, XGBoost model, or H3 aggregation is produced.",
            "",
        ]
    )
    return "\n".join(lines)


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

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    if not ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        return None
    return int(counters.PeakWorkingSetSize)


def build_report(tables: dict[str, ObservationTable], *, load_seconds: float, match_started: float) -> dict[str, object]:
    body, grids = analyze(tables)
    current, peak = tracemalloc.get_traced_memory()
    body.update(
        {
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "parameters": {
                "radii_m": list(RADII_M),
                "windows_min": list(WINDOWS_MIN),
                "primary_radius_m": PRIMARY[0],
                "primary_window_minutes": PRIMARY[1],
                "earth_radius_m": EARTH_RADIUS_M,
                "tile_degrees": TILE_DEGREES,
                "index": "scipy.spatial.cKDTree on ECEF coordinates",
                "separation": "great-circle length recovered from the ECEF chord",
            },
            "processing_level": PROVENANCE,
            "modis_to_viirs_scaling_factor": None,
            "xgboost_trained": False,
            "h3_aggregation": False,
            "same_fire": "not_assessed",
            "performance": {
                "load_seconds": load_seconds,
                "match_seconds": perf_counter() - match_started,
                "peak_python_bytes": int(peak),
                "current_python_bytes": int(current),
                "peak_working_set_bytes": _peak_working_set(),
            },
        }
    )
    return body, grids


def write_outputs(report: dict[str, object], tables: dict[str, ObservationTable], grids: dict[str, np.ndarray]) -> None:
    figures = write_figures(report, tables, grids, FIGURE_DIR)
    report["figures"] = figures
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    tracemalloc.start()
    started = perf_counter()
    tables = load_tables()
    load_seconds = perf_counter() - started
    report, grids = build_report(tables, load_seconds=load_seconds, match_started=perf_counter())
    write_outputs(report, tables, grids)
    print(
        f"pairs={len(report['pairs'])} load_s={load_seconds:.1f} match_s={report['performance']['match_seconds']:.1f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

