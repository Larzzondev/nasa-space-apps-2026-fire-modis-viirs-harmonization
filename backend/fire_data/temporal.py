"""Temporal validation against the archives that are actually on disk.

The module records processing-level provenance, repeats the VIIRS 367 K and
MODIS FRP summaries for every acquisition date present, and counts
cross-satellite proximity inside configurable distance and time windows.
It does not assign standard or NRT processing from a filename or a version
field, does not treat a proximity pair as the same fire, and does not
calculate a harmonization coefficient.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from itertools import combinations
from pathlib import Path

import numpy as np

from fire_data.contract import BACKEND_ROOT, COLUMNS, RAW_DIR, SOURCES, SourceContract
from fire_data.eda_spatial import EARTH_RADIUS_M, lonlat_to_ecef
from fire_data.readers import read_archive

REPORTS_DIR = BACKEND_ROOT / "reports"
CEILING = Decimal("367")
TAIL_START = Decimal("360")
GAP_START = Decimal("366")
EXTREME_QUANTILE = 0.999
DEFAULT_RADII_M = (375.0, 1_000.0, 5_000.0)
DEFAULT_WINDOWS_MIN = (0, 30, 180)
SATELLITE_ORDER = ("Terra", "Aqua", "N20", "N21", "SNPP")
VIIRS_SATELLITES = frozenset({"N20", "N21", "SNPP"})
MODIS_SATELLITES = frozenset({"Terra", "Aqua"})
RETRIEVED = "2026-11-14"

DOCUMENT_STATEMENTS: tuple[dict[str, str], ...] = (
    {
        "source_id": "firms_download_readme",
        "url": "https://firms.modaps.eosdis.nasa.gov/download/Readme.txt",
        "retrieved": RETRIEVED,
        "text": (
            "The FIRMS download readme says a request can return near-real-time files, "
            "standard-quality files, or both, and that NRT data are replaced when standard "
            "data are available, after approximately three months. It defines "
            "fire_nrt_M-C61 as MCD14DL, fire_archive_M-C61 as standard-quality MCD14ML, "
            "fire_nrt_SV-C2 as VNP14IMGTDL, and fire_archive_SV-C2 as standard-quality "
            "VNP14IMGTML. It defines fire_nrt_J1V-C2 as VJ114IMGDL and fire_nrt_J2V-C2 as "
            "VJ214IMGDL. It does not define fire_archive_J1V-C2 or fire_archive_J2V-C2. "
            "It states: standard quality data is not yet available from FIRMS for NOAA-20 and NOAA-21. "
            "The characters after the product code are the download request id. "
            "The Collection / Version field is described as the way to distinguish MODIS from VIIRS "
            "when the files are combined, not as an NRT-versus-standard flag."
        ),
    },
    {
        "source_id": "firms_api_availability",
        "url": "https://firms.modaps.eosdis.nasa.gov/api/data_availability/",
        "retrieved": RETRIEVED,
        "text": (
            "The FIRMS API data-availability page lists separate sensor codes for near-real-time "
            "and standard processing, including VIIRS_NOAA20_NRT, VIIRS_NOAA20_SP, "
            "VIIRS_NOAA21_NRT, VIIRS_NOAA21_SP, VIIRS_SNPP_NRT, VIIRS_SNPP_SP, MODIS_NRT, and MODIS_SP. "
            "Those codes are catalog labels. They are not columns in the local CSV files."
        ),
    },
)


def determine_processing_level(
    *,
    filename: str,
    version_values: tuple[str, ...],
    columns: tuple[str, ...],
) -> dict[str, object]:
    """Record filename and version without treating either as a processing level.

    The arguments are part of the recorded evidence. The returned level stays
    unresolved unless a column in the file itself is named as a processing level
    and every data row carries a value. These archives have no such column.
    """

    level_names = {"processing_level", "product_level", "processing_stream"}
    present = [column for column in columns if column.strip().lower() in level_names]
    return {
        "processing_level": "unresolved",
        "determined": False,
        "filename_recorded": filename,
        "version_values_recorded": list(version_values),
        "processing_level_column_present": bool(present),
        "reason": (
            "No processing-level column is present, so standard processing and near-real-time "
            "processing are not assigned. The filename and the version field are stored as "
            "file facts and are not used as that assignment."
        ),
    }


def temporal_repeat_status(dates: list[str]) -> str:
    return "available" if len(dates) >= 2 else "unavailable"


def epoch_minutes(acq_date: str, acq_time: str) -> int:
    day = datetime.strptime(acq_date, "%Y-%m-%d").toordinal()
    return day * 1440 + int(acq_time[:2]) * 60 + int(acq_time[2:])


def _decimal(text: str) -> Decimal | None:
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    return value


def _column_index() -> dict[str, int]:
    return {name: index for index, name in enumerate(COLUMNS)}


class _BrightnessBin:
    def __init__(self) -> None:
        self.detection_count = 0
        self.invalid_brightness = 0
        self.numeric_equal_367 = 0
        self.exact_text_367 = 0
        self.above_367 = 0
        self.from_360_below_367 = 0
        self.from_366_below_367 = 0
        self.highest_below: Decimal | None = None
        self.highest_texts: Counter[str] = Counter()

    def add(self, text: str) -> None:
        self.detection_count += 1
        value = _decimal(text)
        if value is None:
            self.invalid_brightness += 1
            return
        if value > CEILING:
            self.above_367 += 1
            return
        if value == CEILING:
            self.numeric_equal_367 += 1
            if text == "367":
                self.exact_text_367 += 1
            return
        if value >= TAIL_START:
            self.from_360_below_367 += 1
        if value >= GAP_START:
            self.from_366_below_367 += 1
        if self.highest_below is None or value > self.highest_below:
            self.highest_below = value
            self.highest_texts = Counter({text: 1})
        elif value == self.highest_below:
            self.highest_texts[text] += 1

    def record(self, satellite: str, acq_date: str) -> dict[str, object]:
        count = self.detection_count
        share = None if count == 0 else self.numeric_equal_367 / count
        if not self.highest_texts:
            highest_text, highest_count = None, 0
        else:
            highest_text, highest_count = sorted(self.highest_texts.items(), key=lambda item: (-item[1], item[0]))[0]
        return {
            "satellite": satellite,
            "acq_date": acq_date,
            "detection_count": count,
            "invalid_brightness": self.invalid_brightness,
            "numeric_equal_367": self.numeric_equal_367,
            "exact_text_367": self.exact_text_367,
            "share_equal_367": share,
            "above_367": self.above_367,
            "from_360_below_367": self.from_360_below_367,
            "from_366_below_367": self.from_366_below_367,
            "highest_below_367_text": highest_text,
            "highest_below_367_count": highest_count,
            "confirmed_saturated_count": 0,
            "saturation_flag_present": False,
        }


def _empty_cluster() -> dict[str, object]:
    return {
        "extreme_threshold": None,
        "extreme_count": 0,
        "extreme_cell_count": 0,
        "densest_cell_count": 0,
        "densest_cell_share": None,
        "densest_cell_lat_floor": None,
        "densest_cell_lon_floor": None,
        "extreme_acq_time_count": 0,
        "extreme_modal_acq_time": None,
        "extreme_modal_acq_time_count": 0,
    }


def cluster_extremes(
    latitude: np.ndarray,
    longitude: np.ndarray,
    acq_time: np.ndarray,
    selected: np.ndarray,
) -> dict[str, object]:
    """Describe where the selected rows sit in 1° cells and in acquisition minute.

    A cell count is a count of archived rows. It is not a fire count.
    """

    chosen = np.asarray(selected, dtype=bool)
    count = int(chosen.sum())
    if count == 0:
        return _empty_cluster()
    lat_floor = np.floor(latitude[chosen]).astype(np.int32)
    lon_floor = np.floor(longitude[chosen]).astype(np.int32)
    cells: Counter[tuple[int, int]] = Counter(zip(lat_floor.tolist(), lon_floor.tolist(), strict=True))
    (cell_lat, cell_lon), cell_count = sorted(cells.items(), key=lambda item: (-item[1], item[0]))[0]
    times: Counter[str] = Counter(acq_time[chosen].tolist())
    modal_time, modal_count = sorted(times.items(), key=lambda item: (-item[1], item[0]))[0]
    return {
        "extreme_cell_count": len(cells),
        "densest_cell_count": cell_count,
        "densest_cell_share": cell_count / count,
        "densest_cell_lat_floor": int(cell_lat),
        "densest_cell_lon_floor": int(cell_lon),
        "extreme_acq_time_count": len(times),
        "extreme_modal_acq_time": modal_time,
        "extreme_modal_acq_time_count": modal_count,
    }


def _quantile_row(
    *,
    satellite: str,
    acq_date: str,
    daynight: str,
    frp: np.ndarray,
    frp_text: np.ndarray,
    confidence: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    acq_time: np.ndarray,
    brightness: np.ndarray,
    scan: np.ndarray,
    track: np.ndarray,
    line_number: np.ndarray,
) -> dict[str, object]:
    count = int(frp.size)
    if count == 0:
        record = {
            "satellite": satellite,
            "acq_date": acq_date,
            "daynight": daynight,
            "detection_count": 0,
            "minimum": None,
            "p50": None,
            "p90": None,
            "p99": None,
            "p999": None,
            "maximum_text": None,
            "maximum_row_count": 0,
            "confidence_at_maximum": [],
            "confidence_min": None,
            "confidence_median": None,
            "confidence_max": None,
            "extreme_confidence_min": None,
            "extreme_confidence_median": None,
            "extreme_confidence_max": None,
            "maxima": [],
        }
        record.update(_empty_cluster())
        return record
    quantiles = np.quantile(frp, [0.5, 0.9, 0.99, EXTREME_QUANTILE], method="linear")
    threshold = float(quantiles[3])
    selected = frp >= threshold
    max_text = max(frp_text.tolist(), key=Decimal)
    at_max = np.flatnonzero(frp_text == max_text)
    conf_values = confidence[at_max].tolist()
    conf_int = np.array([int(value) for value in confidence.tolist()], dtype=np.int16)
    extreme_conf = conf_int[selected]
    cluster = cluster_extremes(latitude, longitude, acq_time, selected)
    maxima = []
    for index in at_max[:20]:
        position = int(index)
        maxima.append(
            {
                "line_number": int(line_number[position]),
                "latitude": latitude[position],
                "longitude": longitude[position],
                "acq_time": str(acq_time[position]),
                "frp": str(frp_text[position]),
                "confidence": str(confidence[position]),
                "brightness": str(brightness[position]),
                "scan": str(scan[position]),
                "track": str(track[position]),
                "daynight": daynight if daynight in {"D", "N"} else str(daynight),
            }
        )
    return {
        "satellite": satellite,
        "acq_date": acq_date,
        "daynight": daynight,
        "detection_count": count,
        "minimum": float(np.min(frp)),
        "p50": float(quantiles[0]),
        "p90": float(quantiles[1]),
        "p99": float(quantiles[2]),
        "p999": threshold,
        "maximum_text": max_text,
        "maximum_row_count": int(at_max.size),
        "confidence_at_maximum": sorted(set(conf_values), key=lambda item: int(item)),
        "confidence_min": int(conf_int.min()),
        "confidence_median": float(np.median(conf_int)),
        "confidence_max": int(conf_int.max()),
        "extreme_confidence_min": int(extreme_conf.min()),
        "extreme_confidence_median": float(np.median(extreme_conf)),
        "extreme_confidence_max": int(extreme_conf.max()),
        "extreme_threshold": threshold,
        "extreme_count": int(selected.sum()),
        **cluster,
        "maxima": maxima,
    }


def frp_by_group(rows: dict[str, np.ndarray]) -> list[dict[str, object]]:
    """FRP distributions for each Terra/Aqua date, split by day, night, and both."""

    if rows["satellite"].size == 0:
        return []
    records = []
    satellites = [name for name in SATELLITE_ORDER if name in set(rows["satellite"].tolist())]
    dates = sorted(set(rows["acq_date"].tolist()))
    for satellite in satellites:
        for acq_date in dates:
            base = (rows["satellite"] == satellite) & (rows["acq_date"] == acq_date)
            if not np.any(base):
                continue
            strata = ("D", "N", "all")
            for stratum in strata:
                chosen = base if stratum == "all" else base & (rows["daynight"] == stratum)
                records.append(
                    _quantile_row(
                        satellite=satellite,
                        acq_date=acq_date,
                        daynight=stratum,
                        frp=rows["frp"][chosen],
                        frp_text=rows["frp_text"][chosen],
                        confidence=rows["confidence"][chosen],
                        latitude=rows["latitude"][chosen],
                        longitude=rows["longitude"][chosen],
                        acq_time=rows["acq_time"][chosen],
                        brightness=rows["brightness"][chosen],
                        scan=rows["scan"][chosen],
                        track=rows["track"][chosen],
                        line_number=rows["line_number"][chosen],
                    )
                )
    return records


def proximity_counts(
    satellite: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    epoch_min: np.ndarray,
    radii_m: tuple[float, ...],
    windows_min: tuple[int, ...],
) -> list[dict[str, object]]:
    """Count cross-satellite pairs inside each radius and time window.

    ``same_fire`` is always ``not_assessed``. Pair totals are not fire totals:
    one detection can contribute to several pairs.
    """

    from scipy.spatial import cKDTree

    names = [name for name in SATELLITE_ORDER if np.any(satellite == name)]
    extras = sorted(set(satellite.tolist()) - set(names))
    names.extend(extras)
    grouped = {
        name: {
            "latitude": latitude[satellite == name],
            "longitude": longitude[satellite == name],
            "epoch_min": epoch_min[satellite == name],
        }
        for name in names
    }
    ecef = {
        name: lonlat_to_ecef(values["latitude"], values["longitude"])
        for name, values in grouped.items()
        if values["latitude"].size
    }
    windows = tuple(sorted(int(window) for window in windows_min))
    radii = tuple(sorted(float(radius) for radius in radii_m))
    max_radius = radii[-1] if radii else 0.0
    rows: list[dict[str, object]] = []
    for name_a, name_b in combinations(names, 2):
        points_a = ecef.get(name_a)
        points_b = ecef.get(name_b)
        epoch_a = grouped[name_a]["epoch_min"]
        epoch_b = grouped[name_b]["epoch_min"]
        keys = [(radius, window) for radius in radii for window in windows]
        pair_counts = {key: 0 for key in keys}
        hit_a = {key: np.zeros(epoch_a.size, dtype=bool) for key in keys}
        hit_b = {key: np.zeros(epoch_b.size, dtype=bool) for key in keys}
        if points_a is not None and points_b is not None and points_a.size and points_b.size and max_radius > 0:
            neighbors = cKDTree(points_b).query_ball_point(points_a, r=max_radius, workers=1)
            for index_a, indices in enumerate(neighbors):
                if not indices:
                    continue
                idx = np.asarray(indices, dtype=np.int64)
                diff = points_b[idx] - points_a[index_a]
                distance = np.sqrt(np.einsum("ij,ij->i", diff, diff))
                delta = np.abs(epoch_b[idx] - epoch_a[index_a])
                for radius, window in keys:
                    mask = (distance <= radius) & (delta <= window)
                    if not np.any(mask):
                        continue
                    pair_counts[(radius, window)] += int(mask.sum())
                    hit_a[(radius, window)][index_a] = True
                    hit_b[(radius, window)][idx[mask]] = True
        for radius, window in keys:
            rows.append(
                {
                    "satellite_a": name_a,
                    "satellite_b": name_b,
                    "radius_m": radius,
                    "max_delta_minutes": window,
                    "proximity_pairs": pair_counts[(radius, window)],
                    "detections_a_with_neighbor": int(hit_a[(radius, window)].sum()),
                    "detections_b_with_neighbor": int(hit_b[(radius, window)].sum()),
                    "same_fire": "not_assessed",
                }
            )
    return rows


def calibration_variables() -> list[dict[str, str]]:
    """Variables that can enter a later calibration, and variables that cannot yet.

    No numeric coefficient is attached to either list.
    """

    return [
        {
            "variable": "frp",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": (
                "FRP is stored in MW for Terra, Aqua, NOAA-20, NOAA-21, and S-NPP. "
                "It can be stratified by satellite and by the stored day/night flag. "
                "A coefficient is not estimated. The retrievals are sensor-specific, "
                "and this extract has one acquisition date."
            ),
        },
        {
            "variable": "scan",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": "Stored along-scan pixel size in km. Usable as an observation-geometry covariate, not as a fire attribute to rescale.",
        },
        {
            "variable": "track",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": "Stored along-track pixel size in km. Usable as an observation-geometry covariate.",
        },
        {
            "variable": "daynight",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": "Stored day/night flag. Usable as a stratum. It is not recomputed from solar zenith angle in this pass.",
        },
        {
            "variable": "latitude",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": "Match coordinate only. It is not a quantity to harmonize across sensors.",
        },
        {
            "variable": "longitude",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": "Match coordinate only. It is not a quantity to harmonize across sensors.",
        },
        {
            "variable": "acq_date",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": "Match time key. Only 2024-07-07 is present, so the key cannot yet support a temporal repeat.",
        },
        {
            "variable": "acq_time",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": "UTC HHMM match key within the dates that are present. Several minutes occur on 2024-07-07.",
        },
        {
            "variable": "satellite",
            "disposition": "calibration_candidate",
            "support": "single_date_only",
            "rationale": "Sensor stratum. Detections from different satellites are not additive fire counts.",
        },
        {
            "variable": "brightness",
            "disposition": "special_treatment",
            "support": "needs_metadata",
            "rationale": (
                "VIIRS brightness has an exact stored value at 367 K and no values above it in this extract. "
                "The CSV has no Level-1 saturation flag, so those rows are not confirmed saturated. "
                "MODIS brightness is a different stored temperature and reaches above 367 K."
            ),
        },
        {
            "variable": "confidence",
            "disposition": "special_treatment",
            "support": "needs_metadata",
            "rationale": (
                "MODIS confidence is an integer from 0 through 100. VIIRS confidence is l, n, or h. "
                "The scales are not interchangeable. A MODIS value of 0 is a stored confidence, including on large FRP rows."
            ),
        },
        {
            "variable": "version",
            "disposition": "special_treatment",
            "support": "needs_metadata",
            "rationale": "The version field records the collection identifier seen in the file. It does not identify NRT versus standard processing.",
        },
        {
            "variable": "instrument",
            "disposition": "special_treatment",
            "support": "needs_metadata",
            "rationale": "The S-NPP archive stores instrument as SNPP. The NOAA-20 and NOAA-21 archives store VIIRS. The token is not a processing level.",
        },
        {
            "variable": "bright_t31",
            "disposition": "special_treatment",
            "support": "needs_metadata",
            "rationale": "The column is present and numeric. The files do not state whether it is MODIS channel 31 or VIIRS I-5.",
        },
        {
            "variable": "type",
            "disposition": "special_treatment",
            "support": "needs_metadata",
            "rationale": "Stored codes include 0, 1, 2, and 3. This pass does not drop a class and does not treat every row as the same fire type.",
        },
        {
            "variable": "processing_level",
            "disposition": "special_treatment",
            "support": "needs_metadata",
            "rationale": "Absent from every local archive. NOAA-20 and NOAA-21 in particular cannot be pooled under a standard-product assumption.",
        },
        {
            "variable": "proximity_pairs",
            "disposition": "special_treatment",
            "support": "single_date_only",
            "rationale": "A pair inside a distance and time window is a proximity match. It is not a confirmed same-fire match and the pairs are not summed across sensors as fires.",
        },
    ]


def _archive_arrays() -> dict[str, list]:
    return {
        "satellite": [],
        "acq_date": [],
        "daynight": [],
        "frp": [],
        "frp_text": [],
        "confidence": [],
        "latitude": [],
        "longitude": [],
        "acq_time": [],
        "brightness": [],
        "scan": [],
        "track": [],
        "line_number": [],
    }


def _as_modis_arrays(rows: dict[str, list]) -> dict[str, np.ndarray]:
    return {
        "satellite": np.asarray(rows["satellite"], dtype=object),
        "acq_date": np.asarray(rows["acq_date"], dtype=object),
        "daynight": np.asarray(rows["daynight"], dtype=object),
        "frp": np.asarray(rows["frp"], dtype=np.float64),
        "frp_text": np.asarray(rows["frp_text"], dtype=object),
        "confidence": np.asarray(rows["confidence"], dtype=object),
        "latitude": np.asarray(rows["latitude"], dtype=np.float64),
        "longitude": np.asarray(rows["longitude"], dtype=np.float64),
        "acq_time": np.asarray(rows["acq_time"], dtype=object),
        "brightness": np.asarray(rows["brightness"], dtype=object),
        "scan": np.asarray(rows["scan"], dtype=object),
        "track": np.asarray(rows["track"], dtype=object),
        "line_number": np.asarray(rows["line_number"], dtype=np.int64),
    }


def scan_archives(
    sources: tuple[SourceContract, ...] = SOURCES,
    paths: dict[str, Path] | None = None,
) -> dict[str, object]:
    index = _column_index()
    archives = []
    brightness: dict[tuple[str, str], _BrightnessBin] = defaultdict(_BrightnessBin)
    modis_rows = _archive_arrays()
    point_satellite: list[str] = []
    point_lat: list[float] = []
    point_lon: list[float] = []
    point_epoch: list[int] = []
    acq_times: dict[str, set[str]] = defaultdict(set)

    for source in sources:
        path = paths[source.source_id] if paths and source.source_id in paths else source.path
        dates: Counter[str] = Counter()
        versions: Counter[str] = Counter()
        satellites: Counter[str] = Counter()
        instruments: Counter[str] = Counter()
        invalid_rows = 0
        row_count = 0
        with read_archive(path) as (header, rows):
            if tuple(header) != COLUMNS:
                raise ValueError(f"{path.name} header does not match the observed 15-column contract")
            for line_number, row in rows:
                row_count += 1
                if len(row) != len(COLUMNS):
                    invalid_rows += 1
                    continue
                acq_date = row[index["acq_date"]]
                dates[acq_date] += 1
                versions[row[index["version"]]] += 1
                satellite = row[index["satellite"]]
                satellites[satellite] += 1
                instruments[row[index["instrument"]]] += 1
                acq_time = row[index["acq_time"]]
                try:
                    latitude = float(row[index["latitude"]])
                    longitude = float(row[index["longitude"]])
                    epoch = epoch_minutes(acq_date, acq_time)
                except ValueError:
                    invalid_rows += 1
                    continue
                if not np.isfinite(latitude) or not np.isfinite(longitude):
                    invalid_rows += 1
                    continue
                acq_times[satellite].add(acq_time)
                point_satellite.append(satellite)
                point_lat.append(latitude)
                point_lon.append(longitude)
                point_epoch.append(epoch)
                if satellite in VIIRS_SATELLITES:
                    brightness[(satellite, acq_date)].add(row[index["brightness"]])
                if satellite in MODIS_SATELLITES:
                    frp_text = row[index["frp"]]
                    frp_value = _decimal(frp_text)
                    if frp_value is None:
                        invalid_rows += 1
                        continue
                    modis_rows["satellite"].append(satellite)
                    modis_rows["acq_date"].append(acq_date)
                    modis_rows["daynight"].append(row[index["daynight"]])
                    modis_rows["frp"].append(float(frp_value))
                    modis_rows["frp_text"].append(frp_text)
                    modis_rows["confidence"].append(row[index["confidence"]])
                    modis_rows["latitude"].append(latitude)
                    modis_rows["longitude"].append(longitude)
                    modis_rows["acq_time"].append(acq_time)
                    modis_rows["brightness"].append(row[index["brightness"]])
                    modis_rows["scan"].append(row[index["scan"]])
                    modis_rows["track"].append(row[index["track"]])
                    modis_rows["line_number"].append(line_number)
        level = determine_processing_level(
            filename=path.name,
            version_values=tuple(sorted(versions)),
            columns=tuple(header),
        )
        archives.append(
            {
                "source_id": source.source_id,
                "relative_path": source.relative_path.as_posix(),
                "filename": path.name,
                "row_count": row_count,
                "invalid_rows": invalid_rows,
                "columns": list(header),
                "dates": dict(sorted(dates.items())),
                "versions": dict(sorted(versions.items())),
                "satellites": dict(sorted(satellites.items())),
                "instruments": dict(sorted(instruments.items())),
                "distinct_acq_time": {name: len(times) for name, times in sorted(acq_times.items()) if name in satellites},
                **level,
            }
        )

    date_counts: Counter[str] = Counter()
    for archive in archives:
        date_counts.update(archive["dates"])
    dates = sorted(date_counts)
    brightness_rows = [
        brightness[(satellite, acq_date)].record(satellite, acq_date)
        for satellite in SATELLITE_ORDER
        if satellite in VIIRS_SATELLITES
        for acq_date in dates
        if (satellite, acq_date) in brightness
    ]
    return {
        "archives": archives,
        "dates": dates,
        "date_counts": dict(sorted(date_counts.items())),
        "brightness": brightness_rows,
        "modis": _as_modis_arrays(modis_rows),
        "points": {
            "satellite": np.asarray(point_satellite, dtype=object),
            "latitude": np.asarray(point_lat, dtype=np.float64),
            "longitude": np.asarray(point_lon, dtype=np.float64),
            "epoch_min": np.asarray(point_epoch, dtype=np.int64),
        },
    }


def build_temporal_validation(
    sources: tuple[SourceContract, ...] = SOURCES,
    paths: dict[str, Path] | None = None,
    radii_m: tuple[float, ...] = DEFAULT_RADII_M,
    windows_min: tuple[int, ...] = DEFAULT_WINDOWS_MIN,
) -> dict[str, object]:
    scanned = scan_archives(sources, paths)
    dates = list(scanned["dates"])
    status = temporal_repeat_status(dates)
    missing = []
    if status == "unavailable":
        present = ", ".join(dates) if dates else "none"
        missing.append(
            f"A second acquisition date is absent. Dates present: {present}. "
            "Cross-date counts, proportions, FRP distributions, and geographic persistence were not computed, "
            "and no dates were added."
        )
    missing.extend(
        [
            "The local data directory has no FIRMS zip Readme, request manifest, HDF granule, or netCDF granule beside the four CSV files.",
            "No CSV column identifies NRT versus standard processing, and no column carries an I4 saturation quality flag.",
            "The FIRMS FAQ page linked from the download readme returned HTTP 403 in this pass, so its NRT-versus-standard comparison is not quoted.",
        ]
    )
    frp_rows = frp_by_group(scanned["modis"])
    points = scanned["points"]
    proximity = proximity_counts(
        points["satellite"],
        points["latitude"],
        points["longitude"],
        points["epoch_min"],
        radii_m,
        windows_min,
    )
    return {
        "scope": {
            "label": "temporal validation of the local FIRMS extracts",
            "multi_date_validation": status,
            "dates": dates,
            "date_counts": scanned["date_counts"],
            "radii_m": list(radii_m),
            "windows_min": list(windows_min),
            "extreme_quantile": EXTREME_QUANTILE,
            "earth_radius_m": EARTH_RADIUS_M,
        },
        "missing": missing,
        "archives": scanned["archives"],
        "document_statements": list(DOCUMENT_STATEMENTS),
        "brightness": scanned["brightness"],
        "modis_frp": [{key: value for key, value in row.items() if key != "maxima"} for row in frp_rows],
        "modis_maxima": [
            {**item, "satellite": row["satellite"], "acq_date": row["acq_date"], "daynight": row["daynight"]}
            for row in frp_rows
            if row["daynight"] in {"D", "N"}
            for item in row["maxima"]
        ],
        "proximity": proximity,
        "variables": calibration_variables(),
    }


def assert_output_allowed(path: Path) -> None:
    resolved = path.resolve()
    raw = RAW_DIR.resolve()
    if resolved == raw or raw in resolved.parents:
        raise ValueError(f"{path} is inside the raw archive directory")


def _parse_floats(text: str) -> tuple[float, ...]:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        raise SystemExit("At least one value is required")
    return tuple(float(part) for part in parts)


def _parse_ints(text: str) -> tuple[int, ...]:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        raise SystemExit("At least one window is required")
    return tuple(int(part) for part in parts)


def main(argv: list[str] | None = None) -> int:
    from fire_data.temporal_report import write_temporal

    parser = argparse.ArgumentParser(description="Validate provenance and the single available acquisition date.")
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--radii-m", default="375,1000,5000")
    parser.add_argument("--windows-min", default="0,30,180")
    args = parser.parse_args(argv)
    summary = build_temporal_validation(radii_m=_parse_floats(args.radii_m), windows_min=_parse_ints(args.windows_min))
    written = write_temporal(summary, args.output_dir)
    scope = summary["scope"]
    print(
        f"multi_date_validation={scope['multi_date_validation']} "
        f"dates={','.join(scope['dates']) or 'none'} proximity_rows={len(summary['proximity'])}"
    )
    print(f"Wrote {written[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
