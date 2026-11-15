"""Scan the July 2024 FIRMS extracts without changing them.

A date with no stored row is a zero delivered-row count inside a present file.
That count is not a measurement of fire activity. A missing file is recorded
separately and has no delivered-row count.
"""

from __future__ import annotations

import hashlib
import math
from array import array
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np

from fire_data.contract import COLUMNS, NUMERIC_COLUMNS
from fire_data.eda_summary import summarize_confidence, summarize_numeric
from fire_data.fields import (
    is_valid_acq_date,
    is_valid_acq_time,
    is_valid_daynight,
    is_valid_fire_type,
    is_valid_modis_confidence,
    is_valid_viirs_confidence,
    parse_float,
)
from fire_data.ingest import DESTINATION_DIR, INCOMING_DIR, period_dates
from fire_data.readers import read_archive

PERIOD_START = date(2024, 7, 1)
PERIOD_END = date(2024, 7, 31)
SATELLITE_ORDER = ("Terra", "Aqua", "N20", "N21", "SNPP")
SENSOR_FOR_SATELLITE = {
    "Terra": "modis",
    "Aqua": "modis",
    "N20": "viirs_noaa20",
    "N21": "viirs_noaa21",
    "SNPP": "viirs_snpp",
}
EXPECTED_ROWS = {
    "modis": 676_636,
    "viirs_noaa20": 2_902_597,
    "viirs_noaa21": 2_771_214,
    "viirs_snpp": 1_635_020,
}
JULY7_SAMPLE_ROWS = {
    "Terra": 7_044,
    "Aqua": 13_366,
    "N20": 82_372,
    "N21": 87_637,
    "SNPP": 86_840,
}
SNPP_WINDOWS = (
    ("2024-07-10", "2024-07-16"),
    ("2024-07-25", "2024-07-28"),
)
WEEK_BINS = (
    ("2024-07-01", "2024-07-07"),
    ("2024-07-08", "2024-07-14"),
    ("2024-07-15", "2024-07-21"),
    ("2024-07-22", "2024-07-28"),
    ("2024-07-29", "2024-07-31"),
)
ZERO_ROW_MEANING = (
    "The source CSV is present and contains no row with this acquisition date. "
    "The delivered-row count is zero. That is not a measurement of zero fire activity."
)
MISSING_FILE_MEANING = "The source CSV is not present, so this date has no delivered-row count."

ARCHIVES = (
    {
        "sensor": "modis",
        "relative_csv": Path("modis") / "fire_archive_M-C61_850319.csv",
        "zip_filename": "DL_FIRE_M-C61_850319.zip",
        "satellites": frozenset({"Terra", "Aqua"}),
        "confidence": "modis_0_100",
    },
    {
        "sensor": "viirs_snpp",
        "relative_csv": Path("viirs_snpp") / "fire_archive_SV-C2_850322.csv",
        "zip_filename": "DL_FIRE_SV-C2_850322.zip",
        "satellites": frozenset({"SNPP"}),
        "confidence": "viirs_lnh",
    },
    {
        "sensor": "viirs_noaa20",
        "relative_csv": Path("viirs_noaa20") / "fire_archive_J1V-C2_850320.csv",
        "zip_filename": "DL_FIRE_J1V-C2_850320.zip",
        "satellites": frozenset({"N20"}),
        "confidence": "viirs_lnh",
    },
    {
        "sensor": "viirs_noaa21",
        "relative_csv": Path("viirs_noaa21") / "fire_archive_J2V-C2_850321.csv",
        "zip_filename": "DL_FIRE_J2V-C2_850321.zip",
        "satellites": frozenset({"N21"}),
        "confidence": "viirs_lnh",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dates_inclusive(start: str, end: str) -> list[str]:
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    count = (last - first).days + 1
    return [(first + timedelta(days=offset)).isoformat() for offset in range(count)]


def week_label(day: str) -> str:
    for start, end in WEEK_BINS:
        if start <= day <= end:
            return f"{start} to {end}"
    raise ValueError(f"{day} is outside July 2024")


def coverage_cell(source_present: bool, delivered_rows: int | None) -> dict[str, object]:
    if not source_present:
        return {
            "source_file": "missing",
            "delivered_rows": None,
            "status": "source_file_missing",
            "meaning": MISSING_FILE_MEANING,
        }
    if delivered_rows is None:
        raise ValueError("A present source file needs a delivered-row count")
    if delivered_rows == 0:
        return {
            "source_file": "present",
            "delivered_rows": 0,
            "status": "zero_rows_delivered",
            "meaning": ZERO_ROW_MEANING,
        }
    return {
        "source_file": "present",
        "delivered_rows": delivered_rows,
        "status": "rows_delivered",
        "meaning": "The source CSV contains this many rows with this acquisition date.",
    }


def build_coverage(delivered: dict[str, dict[str, int]], present: dict[str, bool]) -> list[dict[str, object]]:
    rows = []
    for day in period_dates():
        satellites = {}
        for satellite in SATELLITE_ORDER:
            source_present = present[SENSOR_FOR_SATELLITE[satellite]]
            count = delivered.get(satellite, {}).get(day, 0) if source_present else None
            satellites[satellite] = coverage_cell(source_present, count)
        rows.append({"date": day, "satellites": satellites})
    return rows


def investigate_snpp(delivered: dict[str, dict[str, int]], present: dict[str, bool]) -> list[dict[str, object]]:
    windows = []
    for start, end in SNPP_WINDOWS:
        days = []
        for day in dates_inclusive(start, end):
            cell = coverage_cell(present["viirs_snpp"], delivered.get("SNPP", {}).get(day, 0) if present["viirs_snpp"] else None)
            others = {
                satellite: coverage_cell(
                    present[SENSOR_FOR_SATELLITE[satellite]],
                    delivered.get(satellite, {}).get(day, 0) if present[SENSOR_FOR_SATELLITE[satellite]] else None,
                )
                for satellite in ("Terra", "Aqua", "N20", "N21")
            }
            days.append({"date": day, "snpp": cell, "other_archives": others})
        zero_days = [item["date"] for item in days if item["snpp"]["status"] == "zero_rows_delivered"]
        delivered_days = [item["date"] for item in days if item["snpp"]["status"] == "rows_delivered"]
        windows.append(
            {
                "window": {"start": start, "end": end},
                "dates": days,
                "snpp_zero_rows_delivered": zero_days,
                "snpp_dates_with_rows": delivered_days,
                "inference": (
                    "These dates describe rows stored in the local S-NPP CSV. "
                    "A date with zero delivered rows is not evidence of zero fire activity, "
                    "and rows in the other archives are not evidence of an S-NPP outage."
                ),
            }
        )
    return windows


def count_sorted_duplicates(buf: bytearray) -> int:
    """Count extra copies among 16-byte digests stored in ``buf``."""

    if len(buf) % 16 != 0:
        raise ValueError("Digest buffer length is not a multiple of 16 bytes")
    count = len(buf) // 16
    if count < 2:
        return 0
    pairs = np.frombuffer(buf, dtype=np.uint64).reshape(count, 2).copy()
    order = np.lexsort((pairs[:, 1], pairs[:, 0]))
    ordered = pairs[order]
    same = np.all(ordered[1:] == ordered[:-1], axis=1)
    return int(np.count_nonzero(same))


def _digest(text: str) -> bytes:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()


def _numeric_block(values: array) -> dict[str, object] | None:
    if len(values) == 0:
        return None
    sample = np.frombuffer(values, dtype=np.float64).copy()
    summary = summarize_numeric(sample)
    summary["values_in_distribution"] = int(sample.size)
    return summary


class _Extreme:
    def __init__(self) -> None:
        self.value: Decimal | None = None
        self.row: dict[str, str] | None = None
        self.matching_rows = 0

    def observe(self, text: str, row: dict[str, str]) -> None:
        try:
            value = Decimal(text)
        except InvalidOperation:
            return
        if not value.is_finite():
            return
        if self.value is None or value > self.value:
            self.value = value
            self.row = row
            self.matching_rows = 1
        elif value == self.value:
            self.matching_rows += 1

    def as_dict(self) -> dict[str, object] | None:
        if self.row is None or self.value is None:
            return None
        return {
            "stored_text": format(self.value, "f"),
            "rows_with_this_stored_value": self.matching_rows,
            "example_row": self.row,
        }


def scan_csv(path: Path, spec: dict[str, object]) -> dict[str, object]:
    """Read one monthly CSV. The file is opened for reading only."""

    satellites = spec["satellites"]
    confidence_kind = str(spec["confidence"])
    index = {name: position for position, name in enumerate(COLUMNS)}
    record_count = 0
    malformed = Counter()
    empty_cells = Counter()
    daily: dict[str, Counter[str]] = {}
    hours: dict[str, dict[str, list[int]]] = {}
    weekly = Counter()
    daynight = Counter()
    confidence = Counter()
    instrument = Counter()
    version = Counter()
    fire_type = Counter()
    satellites_seen = Counter()
    cells: dict[str, Counter[tuple[int, int]]] = {}
    exact = bytearray()
    location = bytearray()
    series: dict[str, dict[str, array]] = {}
    bright_367 = Counter()
    bright_above_367 = 0
    bright_360_to_367 = 0
    frp_on_367 = _Extreme()
    extremes: dict[str, dict[str, _Extreme]] = {}
    numeric_excluded = Counter()

    def bucket(satellite: str) -> dict[str, array]:
        found = series.get(satellite)
        if found is None:
            found = {name: array("d") for name in ("frp", "brightness", "latitude", "longitude")}
            series[satellite] = found
        return found

    with read_archive(path) as (header, rows):
        if tuple(header) != COLUMNS:
            raise ValueError(f"{path.name} header does not match the observed 15-column contract")
        for line_number, row in rows:
            record_count += 1
            if len(row) != len(COLUMNS):
                malformed["column_count"] += 1
                continue
            for name in COLUMNS:
                if row[index[name]].strip() == "":
                    empty_cells[name] += 1
            joined = "\x1f".join(row)
            exact += _digest(joined)
            satellite = row[index["satellite"]]
            satellites_seen[satellite] += 1
            location_key = "\x1f".join(
                (
                    satellite,
                    row[index["latitude"]],
                    row[index["longitude"]],
                    row[index["acq_date"]],
                    row[index["acq_time"]],
                )
            )
            location += _digest(location_key)
            acq_date = row[index["acq_date"]]
            if not is_valid_acq_date(acq_date):
                malformed["acq_date"] += 1
            acq_time = row[index["acq_time"]]
            if not is_valid_acq_time(acq_time):
                malformed["acq_time"] += 1
            if satellite not in satellites:
                malformed["satellite"] += 1
            if not is_valid_daynight(row[index["daynight"]]):
                malformed["daynight"] += 1
            if not is_valid_fire_type(row[index["type"]]):
                malformed["type"] += 1
            confidence_text = row[index["confidence"]]
            if confidence_kind == "modis_0_100":
                if not is_valid_modis_confidence(confidence_text):
                    malformed["confidence"] += 1
            elif not is_valid_viirs_confidence(confidence_text):
                malformed["confidence"] += 1
            parsed: dict[str, float | None] = {}
            for name in NUMERIC_COLUMNS:
                value = parse_float(row[index[name]])
                parsed[name] = value
                if value is None:
                    malformed[name] += 1
                    numeric_excluded[name] += 1
            latitude = parsed["latitude"]
            longitude = parsed["longitude"]
            if latitude is not None and not -90.0 <= latitude <= 90.0:
                malformed["latitude_range"] += 1
                latitude = None
            if longitude is not None and not -180.0 <= longitude <= 180.0:
                malformed["longitude_range"] += 1
                longitude = None
            if not is_valid_acq_date(acq_date) or satellite not in satellites:
                continue
            daily.setdefault(satellite, Counter())[acq_date] += 1
            if is_valid_acq_time(acq_time):
                hour_map = hours.setdefault(satellite, {}).setdefault(acq_date, [0] * 24)
                hour_map[int(acq_time[:2])] += 1
            weekly[(satellite, week_label(acq_date))] += 1
            daynight[(satellite, row[index["daynight"]])] += 1
            confidence[(satellite, confidence_text)] += 1
            instrument[row[index["instrument"]]] += 1
            version[row[index["version"]]] += 1
            fire_type[row[index["type"]]] += 1
            if latitude is not None and longitude is not None:
                cells.setdefault(satellite, Counter())[(math.floor(latitude), math.floor(longitude))] += 1
            stored = {column: row[index[column]] for column in COLUMNS}
            stored["line_number"] = str(line_number)
            tracker = extremes.setdefault(satellite, {"frp": _Extreme(), "brightness": _Extreme()})
            values = bucket(satellite)
            if parsed["frp"] is not None:
                values["frp"].append(parsed["frp"])
                tracker["frp"].observe(row[index["frp"]], stored)
            if parsed["brightness"] is not None:
                values["brightness"].append(parsed["brightness"])
                tracker["brightness"].observe(row[index["brightness"]], stored)
            if latitude is not None:
                values["latitude"].append(latitude)
            if longitude is not None:
                values["longitude"].append(longitude)
            brightness_text = row[index["brightness"]]
            if confidence_kind == "viirs_lnh" and parsed["brightness"] is not None:
                if brightness_text == "367":
                    bright_367[confidence_text] += 1
                    if parsed["frp"] is not None:
                        frp_on_367.observe(row[index["frp"]], stored)
                elif parsed["brightness"] > 367.0:
                    bright_above_367 += 1
                elif 360.0 <= parsed["brightness"] < 367.0:
                    bright_360_to_367 += 1

    weekly_zero_dates: dict[str, dict[str, list[str]]] = {}
    for satellite in sorted(satellites):
        counts = daily.get(satellite, {})
        for day in period_dates():
            if counts.get(day, 0) == 0:
                weekly_zero_dates.setdefault(satellite, {}).setdefault(week_label(day), []).append(day)
    arrays = {
        satellite: {name: np.frombuffer(values, dtype=np.float64).copy() for name, values in columns.items()}
        for satellite, columns in series.items()
    }
    return {
        "sensor": spec["sensor"],
        "csv_path": path.as_posix(),
        "csv_filename": path.name,
        "csv_bytes": path.stat().st_size,
        "csv_sha256": sha256_file(path),
        "record_count": record_count,
        "empty_cells": dict(empty_cells),
        "malformed": dict(malformed),
        "numeric_values_excluded_from_distributions": dict(numeric_excluded),
        "exact_duplicate_rows": count_sorted_duplicates(exact),
        "location_time_duplicate_rows": count_sorted_duplicates(location),
        "duplicates_removed": 0,
        "satellites_observed": dict(sorted(satellites_seen.items())),
        "instrument_observed": dict(sorted(instrument.items())),
        "version_observed": dict(sorted(version.items())),
        "type_observed": dict(sorted(fire_type.items())),
        "daily": {satellite: dict(sorted(counts.items())) for satellite, counts in sorted(daily.items())},
        "hours": hours,
        "weekly": {f"{satellite}|{label}": count for (satellite, label), count in sorted(weekly.items())},
        "weekly_dates_with_zero_rows": weekly_zero_dates,
        "daynight": {f"{satellite}|{flag}": count for (satellite, flag), count in sorted(daynight.items())},
        "confidence": {f"{satellite}|{flag}": count for (satellite, flag), count in sorted(confidence.items())},
        "spatial": {
            satellite: [
                {"latitude_floor": lat, "longitude_floor": lon, "delivered_rows": count}
                for (lat, lon), count in counts.most_common(12)
            ]
            for satellite, counts in sorted(cells.items())
        },
        "occupied_cells": {satellite: len(counts) for satellite, counts in sorted(cells.items())},
        "cell_row_total": {satellite: int(sum(counts.values())) for satellite, counts in sorted(cells.items())},
        "extremes": {
            satellite: {name: tracker.as_dict() for name, tracker in fields.items()}
            for satellite, fields in sorted(extremes.items())
        },
        "brightness_text_367_by_confidence": dict(bright_367),
        "brightness_above_367": bright_above_367,
        "brightness_from_360_until_367": bright_360_to_367,
        "max_frp_among_brightness_text_367": frp_on_367.as_dict(),
        "arrays": arrays,
    }


def satellite_profiles(scans: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    profiles = {}
    for scan in scans:
        for satellite, columns in scan["arrays"].items():
            frp = columns["frp"]
            brightness = columns["brightness"]
            profiles[satellite] = {
                "sensor": scan["sensor"],
                "delivered_rows": sum(scan["daily"][satellite].values()),
                "frp": _json_numeric(frp) if frp.size else None,
                "brightness": _json_numeric(brightness) if brightness.size else None,
                "frp_zero_rows": int(np.count_nonzero(frp == 0.0)) if frp.size else 0,
                "extreme_frp": scan["extremes"].get(satellite, {}).get("frp"),
                "extreme_brightness": scan["extremes"].get(satellite, {}).get("brightness"),
            }
    return profiles


def _json_numeric(values: np.ndarray) -> dict[str, object]:
    summary = summarize_numeric(values)
    return {
        "count": summary["count"],
        "mean": summary["mean"],
        "median": summary["median"],
        "std": summary["std"],
        "minimum": summary["minimum"],
        "maximum": summary["maximum"],
        "quantiles": summary["quantiles"],
        "zero_count": summary["zero_count"],
    }
