"""Second-pass investigation of two one-day anomalies.

This module reads the raw archives and writes a separate report. It does not
change the exploratory pipeline, the existing EDA products, or the CSV files.
"""

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np

from fire_data.contract import BACKEND_ROOT, COLUMNS, RAW_DIR, SOURCES, SourceContract
from fire_data.eda_spatial import EARTH_RADIUS_M, haversine_m
from fire_data.fields import parse_float
from fire_data.readers import read_archive

REPORTS_DIR = BACKEND_ROOT / "reports"
VIIRS_SOURCE_IDS = ("viirs_noaa20", "viirs_noaa21", "viirs_snpp")
CEILING = Decimal("367")
WINDOW_START = Decimal("366")
TARGET_FRP = (Decimal("7956.3"), Decimal("7328.1"))
SEARCH_RADIUS_M = 10_000.0
DETAIL_RADIUS_M = 5_000.0
COUNT_RADII_M = (1_000.0, 5_000.0, 10_000.0)
TIME_WINDOWS_MIN = (0, 30, 180)


def decimal_value(text: str) -> Decimal | None:
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def decimal_places(text: str) -> int | None:
    number = text[1:] if text.startswith("-") else text
    if number.count(".") > 1 or not number:
        return None
    whole, dot, fraction = number.partition(".")
    if not whole.isdigit() or (dot and not fraction.isdigit()):
        return None
    return len(fraction)


def utc_minutes(acq_time: str) -> int:
    return int(acq_time[:2]) * 60 + int(acq_time[2:])


def great_circle_distance_m(
    latitude: float,
    longitude: float,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
) -> np.ndarray:
    """Vector form of the great-circle distance used for one target."""

    radius = EARTH_RADIUS_M
    phi1 = np.radians(latitude)
    phi2 = np.radians(latitudes)
    dphi = phi2 - phi1
    dlambda = np.radians(longitudes - longitude)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    return 2.0 * radius * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _column_index() -> dict[str, int]:
    return {name: position for position, name in enumerate(COLUMNS)}


def _empty_brightness() -> dict:
    return {
        "detection_count": 0,
        "decimal_place_counts": Counter(),
        "invalid_brightness": 0,
        "below_window": 0,
        "in_window_below_ceiling": 0,
        "numeric_ceiling": 0,
        "above_ceiling": 0,
        "above_ceiling_examples": [],
        "confidence_above_ceiling": Counter(),
        "string_counts_from_366": Counter(),
        "ceiling_texts": Counter(),
        "confidence_at_ceiling": Counter(),
        "confidence_below_ceiling": Counter(),
        "daynight_at_ceiling": Counter(),
        "high_confidence_at_ceiling": 0,
        "high_confidence_below_ceiling": 0,
        "bright_t31_at_ceiling": [],
        "frp_at_ceiling": [],
        "maximum_text": None,
        "maximum_value": None,
        "highest_below_text": None,
        "highest_below_value": None,
        "highest_below_count": 0,
        "maximum_frp": None,
        "maximum_frp_brightness": None,
    }


def _row_dict(row: list[str]) -> dict[str, str]:
    return {column: row[position] for position, column in enumerate(COLUMNS)}


def scan_archives(
    sources: tuple[SourceContract, ...] = SOURCES,
    paths: dict[str, Path] | None = None,
) -> dict:
    """Stream each archive once for brightness text and the target FRP rows."""

    index = _column_index()
    brightness = {source.source_id: _empty_brightness() for source in sources if source.source_id in VIIRS_SOURCE_IDS}
    targets: list[dict] = []
    for source in sources:
        archive = source.path if paths is None else paths[source.source_id]
        with read_archive(archive) as (header, rows):
            if tuple(header) != COLUMNS:
                raise ValueError(f"{archive.name} header does not match the observed contract")
            stats = brightness.get(source.source_id)
            for line_number, row in rows:
                if len(row) != len(COLUMNS):
                    raise ValueError(f"{archive.name} line {line_number} does not have {len(COLUMNS)} fields")
                frp_text = row[index["frp"]]
                frp_number = decimal_value(frp_text)
                if frp_number in TARGET_FRP:
                    targets.append(
                        {
                            "source_id": source.source_id,
                            "archive": source.relative_path.as_posix(),
                            "line_number": line_number,
                            "row": _row_dict(row),
                        }
                    )
                if stats is None:
                    continue
                text = row[index["brightness"]]
                stats["detection_count"] += 1
                places = decimal_places(text)
                if places is None:
                    stats["invalid_brightness"] += 1
                    continue
                stats["decimal_place_counts"][places] += 1
                number = Decimal(text)
                if stats["maximum_value"] is None or number > stats["maximum_value"]:
                    stats["maximum_value"] = number
                    stats["maximum_text"] = text
                if frp_number is not None and (stats["maximum_frp"] is None or frp_number > stats["maximum_frp"]):
                    stats["maximum_frp"] = frp_number
                    stats["maximum_frp_brightness"] = text
                if number > CEILING:
                    stats["above_ceiling"] += 1
                    stats["confidence_above_ceiling"][row[index["confidence"]]] += 1
                    if len(stats["above_ceiling_examples"]) < 5:
                        stats["above_ceiling_examples"].append(text)
                elif number == CEILING:
                    stats["numeric_ceiling"] += 1
                    stats["ceiling_texts"][text] += 1
                    stats["string_counts_from_366"][text] += 1
                    confidence = row[index["confidence"]]
                    stats["confidence_at_ceiling"][confidence] += 1
                    stats["daynight_at_ceiling"][row[index["daynight"]]] += 1
                    if confidence == "h":
                        stats["high_confidence_at_ceiling"] += 1
                    t31 = parse_float(row[index["bright_t31"]])
                    frp = parse_float(frp_text)
                    if t31 is not None:
                        stats["bright_t31_at_ceiling"].append(t31)
                    if frp is not None:
                        stats["frp_at_ceiling"].append(frp)
                else:
                    confidence = row[index["confidence"]]
                    stats["confidence_below_ceiling"][confidence] += 1
                    if confidence == "h":
                        stats["high_confidence_below_ceiling"] += 1
                    if number < WINDOW_START:
                        stats["below_window"] += 1
                    else:
                        stats["in_window_below_ceiling"] += 1
                        stats["string_counts_from_366"][text] += 1
                    if stats["highest_below_value"] is None or number > stats["highest_below_value"]:
                        stats["highest_below_value"] = number
                        stats["highest_below_text"] = text
                        stats["highest_below_count"] = 1
                    elif number == stats["highest_below_value"]:
                        stats["highest_below_count"] += 1
    return {"brightness": brightness, "targets": targets}


def _numeric_summary(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "minimum": None, "median": None, "maximum": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "minimum": float(array.min()),
        "median": float(np.median(array)),
        "maximum": float(array.max()),
    }


def _counter_dict(counter: Counter) -> dict[str, int]:
    return {str(key): int(counter[key]) for key in sorted(counter, key=lambda item: (decimal_value(str(item)) is None, str(item)))}


def brightness_records(scan: dict) -> dict:
    """Convert one streamed satellite scan into JSON-ready frequency records."""

    records = []
    for source_id in VIIRS_SOURCE_IDS:
        stats = scan["brightness"][source_id]
        ordered_strings = sorted(
            stats["string_counts_from_366"].items(),
            key=lambda item: (Decimal(item[0]), item[0]),
        )
        ceiling = stats["numeric_ceiling"]
        total = stats["detection_count"]
        highest_below = None if stats["highest_below_value"] is None else format(stats["highest_below_value"], "f")
        records.append(
            {
                "source_id": source_id,
                "detection_count": total,
                "decimal_place_counts": {str(places): count for places, count in sorted(stats["decimal_place_counts"].items())},
                "invalid_brightness": stats["invalid_brightness"],
                "maximum_text": stats["maximum_text"],
                "maximum_value": None if stats["maximum_value"] is None else format(stats["maximum_value"], "f"),
                "below_366": stats["below_window"],
                "from_366_below_367": stats["in_window_below_ceiling"],
                "numeric_equal_367": ceiling,
                "share_equal_367": None if total == 0 else ceiling / total,
                "above_367": stats["above_ceiling"],
                "above_367_examples": list(stats["above_ceiling_examples"]),
                "confidence_above_367": _counter_dict(stats["confidence_above_ceiling"]),
                "ceiling_texts": _counter_dict(stats["ceiling_texts"]),
                "frequency_from_366_k": [
                    {"text": text, "value": format(Decimal(text), "f"), "count": count}
                    for text, count in ordered_strings
                ],
                "highest_below_367_text": stats["highest_below_text"],
                "highest_below_367_value": highest_below,
                "highest_below_367_count": stats["highest_below_count"],
                "maximum_frp_text": None if stats["maximum_frp"] is None else format(stats["maximum_frp"], "f"),
                "maximum_frp_brightness_text": stats["maximum_frp_brightness"],
                "confidence_at_367": _counter_dict(stats["confidence_at_ceiling"]),
                "confidence_below_367": _counter_dict(stats["confidence_below_ceiling"]),
                "daynight_at_367": _counter_dict(stats["daynight_at_ceiling"]),
                "high_confidence_at_367": stats["high_confidence_at_ceiling"],
                "high_confidence_below_367": stats["high_confidence_below_ceiling"],
                "bright_t31_at_367": _numeric_summary(stats["bright_t31_at_ceiling"]),
                "frp_at_367": _numeric_summary(stats["frp_at_ceiling"]),
            }
        )
    return {"satellites": records}


def select_nearby(
    candidates: list[dict],
    targets: list[dict],
    radius_m: float = SEARCH_RADIUS_M,
) -> list[dict]:
    """Return candidates within ``radius_m`` of a target, excluding the target row.

    Distance is great-circle distance. ``delta_minutes`` is the absolute
    difference of UTC HHMM on the shared acquisition date. Nothing in the
    result assigns a common fire identity.
    """

    if radius_m <= 0:
        raise ValueError("Search radius must be positive")
    selected = []
    for target in targets:
        row = target["row"]
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        target_minute = utc_minutes(row["acq_time"])
        if not candidates:
            continue
        latitudes = np.asarray([float(item["row"]["latitude"]) for item in candidates], dtype=np.float64)
        longitudes = np.asarray([float(item["row"]["longitude"]) for item in candidates], dtype=np.float64)
        distances = great_circle_distance_m(latitude, longitude, latitudes, longitudes)
        for candidate, distance in zip(candidates, distances.tolist()):
            if candidate["source_id"] == target["source_id"] and candidate["line_number"] == target["line_number"]:
                continue
            if distance > radius_m:
                continue
            delta = abs(utc_minutes(candidate["row"]["acq_time"]) - target_minute)
            selected.append(
                {
                    "target_source_id": target["source_id"],
                    "target_line_number": target["line_number"],
                    "target_frp": target["row"]["frp"],
                    "source_id": candidate["source_id"],
                    "archive": candidate["archive"],
                    "line_number": candidate["line_number"],
                    "satellite": candidate["row"]["satellite"],
                    "distance_m": distance,
                    "delta_minutes": delta,
                    "same_utc_minute": delta == 0,
                    "row": candidate["row"],
                }
            )
    selected.sort(
        key=lambda item: (
            item["target_line_number"],
            item["distance_m"],
            item["delta_minutes"],
            item["source_id"],
            item["line_number"],
        )
    )
    return selected


def _bounding_box(targets: list[dict], radius_m: float) -> tuple[float, float, float, float]:
    pad = np.degrees(radius_m / EARTH_RADIUS_M) * 1.5
    latitudes = [float(target["row"]["latitude"]) for target in targets]
    longitudes = [float(target["row"]["longitude"]) for target in targets]
    cosines = [max(np.cos(np.radians(latitude)), 0.2) for latitude in latitudes]
    lon_pad = max(pad / cosine for cosine in cosines)
    return min(latitudes) - pad, max(latitudes) + pad, min(longitudes) - lon_pad, max(longitudes) + lon_pad


def collect_candidates(
    targets: list[dict],
    radius_m: float = SEARCH_RADIUS_M,
    sources: tuple[SourceContract, ...] = SOURCES,
    paths: dict[str, Path] | None = None,
) -> list[dict]:
    """Stream the archives again and keep only rows inside a padded search box."""

    if not targets:
        return []
    south, north, west, east = _bounding_box(targets, radius_m)
    index = _column_index()
    kept = []
    for source in sources:
        archive = source.path if paths is None else paths[source.source_id]
        with read_archive(archive) as (header, rows):
            if tuple(header) != COLUMNS:
                raise ValueError(f"{archive.name} header does not match the observed contract")
            for line_number, row in rows:
                latitude = float(row[index["latitude"]])
                longitude = float(row[index["longitude"]])
                if south <= latitude <= north and west <= longitude <= east:
                    kept.append(
                        {
                            "source_id": source.source_id,
                            "archive": source.relative_path.as_posix(),
                            "line_number": line_number,
                            "row": _row_dict(row),
                        }
                    )
    return kept


def neighbor_counts(nearby: list[dict], target_line_number: int) -> list[dict]:
    rows = [item for item in nearby if item["target_line_number"] == target_line_number]
    counts = []
    for radius in COUNT_RADII_M:
        for window in (*TIME_WINDOWS_MIN, None):
            matched = [
                item
                for item in rows
                if item["distance_m"] <= radius and (window is None or item["delta_minutes"] <= window)
            ]
            by_satellite: dict[str, int] = {}
            for item in matched:
                by_satellite[item["satellite"]] = by_satellite.get(item["satellite"], 0) + 1
            counts.append(
                {
                    "radius_m": radius,
                    "max_delta_minutes": window,
                    "count": len(matched),
                    "by_satellite": dict(sorted(by_satellite.items())),
                }
            )
    return counts


def build_investigation(
    sources: tuple[SourceContract, ...] = SOURCES,
    paths: dict[str, Path] | None = None,
) -> dict:
    scan = scan_archives(sources, paths)
    targets = sorted(scan["targets"], key=lambda item: (-Decimal(item["row"]["frp"]), item["line_number"]))
    missing = [str(value) for value in TARGET_FRP if not any(Decimal(item["row"]["frp"]) == value for item in targets)]
    if missing:
        raise ValueError("Target FRP rows were not found: " + ", ".join(missing))
    candidates = collect_candidates(targets, SEARCH_RADIUS_M, sources, paths)
    nearby = select_nearby(candidates, targets, SEARCH_RADIUS_M)
    pair_distance = None
    pair_delta = None
    if len(targets) >= 2:
        first, second = targets[0], targets[1]
        pair_distance = haversine_m(
            float(first["row"]["latitude"]),
            float(first["row"]["longitude"]),
            float(second["row"]["latitude"]),
            float(second["row"]["longitude"]),
        )
        pair_delta = abs(utc_minutes(first["row"]["acq_time"]) - utc_minutes(second["row"]["acq_time"]))
    return {
        "scope": {
            "label": "one-day global observations",
            "date": "2024-07-07",
            "purpose": "Investigate the VIIRS brightness value 367 K and two extreme Aqua FRP rows.",
        },
        "brightness": brightness_records(scan),
        "extreme_frp": {
            "search_radius_m": SEARCH_RADIUS_M,
            "detail_radius_m": DETAIL_RADIUS_M,
            "count_radii_m": list(COUNT_RADII_M),
            "time_windows_min": list(TIME_WINDOWS_MIN),
            "distance_method": (
                "Great-circle distance on a sphere of radius "
                f"{EARTH_RADIUS_M:.1f} m, the radius used in the exploratory overlap summary. "
                "Time separation is the absolute difference of UTC minutes from acq_time on 2024-07-07."
            ),
            "targets": targets,
            "pair_distance_m": pair_distance,
            "pair_delta_minutes": pair_delta,
            "nearby_counts": [
                {"target_line_number": target["line_number"], "target_frp": target["row"]["frp"], "counts": neighbor_counts(nearby, target["line_number"])}
                for target in targets
            ],
            "nearby": nearby,
        },
    }


def _refuse_raw_output(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    raw = RAW_DIR.resolve()
    if resolved == raw or raw in resolved.parents:
        raise ValueError("Refusing to write the investigation into the raw archive directory")


def run_investigation(output_dir: Path | None = None) -> dict:
    output = REPORTS_DIR if output_dir is None else Path(output_dir)
    _refuse_raw_output(output)
    summary = build_investigation()
    from fire_data.investigate_report import write_investigation

    output.mkdir(parents=True, exist_ok=True)
    write_investigation(summary, output / "anomaly_summary.json", output / "anomaly_investigation.md")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Investigate the 367 K brightness values and two extreme Aqua FRP rows.")
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args(argv)
    summary = run_investigation(args.output_dir)
    ceiling = ", ".join(
        f"{item['source_id']}={item['numeric_equal_367']}" for item in summary["brightness"]["satellites"]
    )
    print(f"brightness_equal_367 {ceiling}")
    print(f"extreme_rows={len(summary['extreme_frp']['targets'])} nearby={len(summary['extreme_frp']['nearby'])}")
    print(f"Wrote {args.output_dir / 'anomaly_investigation.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
