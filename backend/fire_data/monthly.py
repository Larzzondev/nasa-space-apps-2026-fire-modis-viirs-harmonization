"""Build the July 2024 coverage and exploratory reports from the extracted CSVs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from fire_data.contract import RAW_DIR
from fire_data.eda_summary import VIIRS_FLAG_ORDER, summarize_confidence
from fire_data.ingest import DEFAULT_MANIFEST, DESTINATION_DIR, INCOMING_DIR
from fire_data.monthly_figures import write_figures
from fire_data.monthly_report import LIMITATIONS, render_coverage, render_eda, write_json, write_text
from fire_data.monthly_scan import (
    ARCHIVES,
    EXPECTED_ROWS,
    JULY7_SAMPLE_ROWS,
    SATELLITE_ORDER,
    build_coverage,
    investigate_snpp,
    satellite_profiles,
    scan_csv,
    sha256_file,
)

REPORTS_DIR = DEFAULT_MANIFEST.parent
SAMPLE_FILES = {
    "modis": RAW_DIR / "modis" / "fire_archive_M-C61_850118.csv",
    "viirs_noaa20": RAW_DIR / "viirs_noaa20" / "fire_archive_J1V-C2_850119.csv",
    "viirs_noaa21": RAW_DIR / "viirs_noaa21" / "fire_archive_J2V-C2_850120.csv",
    "viirs_snpp": RAW_DIR / "viirs_snpp" / "fire_archive_SV-C2_850121.csv",
}


def smallest_positive_days(daily: dict[str, int], limit: int = 3) -> list[dict[str, object]]:
    positive = [{"date": day, "delivered_rows": count} for day, count in daily.items() if count > 0]
    positive.sort(key=lambda item: (item["delivered_rows"], item["date"]))
    return positive[:limit]


def _confidence_summary(scan: dict) -> dict[str, dict]:
    kind = "modis_0_100" if scan["sensor"] == "modis" else "viirs_lnh"
    summaries = {}
    grouped: dict[str, Counter[str]] = {}
    for key, count in scan["confidence"].items():
        satellite, label = key.split("|", 1)
        grouped.setdefault(satellite, Counter())[label] = count
    for satellite, counts in grouped.items():
        total = sum(counts.values())
        if kind == "modis_0_100":
            labels = sorted(int(label) for label in counts if label.isdigit())
            values = np.repeat(np.asarray(labels, dtype=np.int16), [counts[str(label)] for label in labels])
            summaries[satellite] = summarize_confidence(values, kind)
            continue
        ordered = [label for label in VIIRS_FLAG_ORDER if label in counts]
        ordered.extend(sorted(set(counts) - set(VIIRS_FLAG_ORDER)))
        summaries[satellite] = {
            "kind": kind,
            "semantics": (
                "VIIRS confidence flags stored as l, n, and h. "
                "FIRMS documents those flags as low, nominal, and high. "
                "The words name the stored flags and are not a conversion onto the MODIS 0-100 scale."
            ),
            "counts": {label: int(counts[label]) for label in ordered},
            "proportions": {label: counts[label] / total for label in ordered},
            "median_integer": None,
        }
    return summaries


def _public_scan(scan: dict) -> dict:
    hidden = {"arrays", "hours"}
    return {key: value for key, value in scan.items() if key not in hidden}


def build_reports(scans: list[dict], manifest: dict, sample_hashes: dict[str, dict[str, str]]) -> tuple[dict, dict]:
    delivered = {}
    present = {}
    for scan in scans:
        present[scan["sensor"]] = True
        for satellite, counts in scan["daily"].items():
            delivered[satellite] = counts
    for spec in ARCHIVES:
        present.setdefault(spec["sensor"], False)
    matrix = build_coverage(delivered, present)
    profiles = satellite_profiles(scans)
    ordered_profiles = {satellite: profiles[satellite] for satellite in SATELLITE_ORDER if satellite in profiles}
    integrity_archives = []
    exact = 0
    location = 0
    empty = Counter()
    malformed = Counter()
    manifest_by_sensor = {item["sensor"]: item for item in manifest["sensors"]}
    for scan in scans:
        expected = EXPECTED_ROWS[scan["sensor"]]
        recorded = manifest_by_sensor[scan["sensor"]]
        exact += scan["exact_duplicate_rows"]
        location += scan["location_time_duplicate_rows"]
        empty.update(scan["empty_cells"])
        malformed.update(scan["malformed"])
        integrity_archives.append(
            {
                "sensor": scan["sensor"],
                "zip_filename": recorded["zip_filename"],
                "zip_sha256": recorded["zip_sha256"],
                "zip_sha256_matches_file": recorded["zip_sha256"] == sha256_file(INCOMING_DIR / recorded["zip_filename"]),
                "csv_filename": scan["csv_filename"],
                "csv_sha256": scan["csv_sha256"],
                "csv_sha256_matches_manifest": scan["csv_sha256"] == recorded["csv_sha256"],
                "expected_rows": expected,
                "record_count": scan["record_count"],
                "difference": scan["record_count"] - expected,
                "date_min": min(day for counts in scan["daily"].values() for day in counts),
                "date_max": max(day for counts in scan["daily"].values() for day in counts),
                "satellites_observed": scan["satellites_observed"],
                "instrument_observed": scan["instrument_observed"],
                "version_observed": scan["version_observed"],
                "exact_duplicate_rows": scan["exact_duplicate_rows"],
                "location_time_duplicate_rows": scan["location_time_duplicate_rows"],
                "empty_cells": scan["empty_cells"],
                "malformed": scan["malformed"],
            }
        )
    total = sum(item["record_count"] for item in integrity_archives)
    expected_total = sum(EXPECTED_ROWS.values())
    coverage = {
        "period": {"start": "2024-07-01", "end": "2024-07-31"},
        "matrix": matrix,
        "snpp_windows": investigate_snpp(delivered, present),
        "smallest_positive_days": {
            satellite: smallest_positive_days(delivered[satellite]) for satellite in SATELLITE_ORDER if satellite in delivered
        },
        "notable_hour_counts": _notable_hours(scans, delivered),
        "integrity": {
            "manifest_passed": manifest["passed"],
            "archives": integrity_archives,
            "total_rows": total,
            "expected_total": expected_total,
            "total_difference": total - expected_total,
            "exact_duplicate_rows": exact,
            "location_time_duplicate_rows": location,
            "empty_cells": dict(empty),
            "malformed": dict(malformed),
            "july7_sample_hashes": sample_hashes,
            "processing_stream": None,
        },
        "harmonization_coefficients_calculated": False,
        "limitations": list(LIMITATIONS),
    }
    eda = {
        "period": {"start": "2024-07-01", "end": "2024-07-31"},
        "scope": "Rows delivered in the four July 2024 FIRMS CSV extracts. Counts are archive rows.",
        "satellites": ordered_profiles,
        "daynight": _daynight(scans),
        "confidence": _confidence_by_satellite(scans),
        "confidence_note": (
            "MODIS confidence remains an integer from 0 through 100. "
            "VIIRS confidence remains the stored flag l, n, or h. The two summaries are separate."
        ),
        "weekly": _weekly(scans),
        "spatial": _spatial(scans),
        "brightness_367": {
            scan["sensor"]: {
                "by_confidence": scan["brightness_text_367_by_confidence"],
                "above_367": scan["brightness_above_367"],
                "from_360_until_367": scan["brightness_from_360_until_367"],
                "max_frp_among_brightness_text_367": scan["max_frp_among_brightness_text_367"],
            }
            for scan in scans
            if scan["sensor"] != "modis"
        },
        "july7": {
            satellite: {
                "monthly_rows": delivered[satellite].get("2024-07-07", 0),
                "sample_rows": JULY7_SAMPLE_ROWS[satellite],
                "difference": delivered[satellite].get("2024-07-07", 0) - JULY7_SAMPLE_ROWS[satellite],
            }
            for satellite in SATELLITE_ORDER
            if satellite in delivered
        },
        "harmonization_coefficients_calculated": False,
        "same_fire_assessment": "not_assessed",
        "limitations": list(LIMITATIONS),
    }
    return coverage, eda


def _notable_hours(scans: list[dict], delivered: dict[str, dict[str, int]]) -> dict[str, dict[str, list[int]]]:
    chosen = {}
    for scan in scans:
        for satellite, hours in scan["hours"].items():
            days = {item["date"] for item in smallest_positive_days(delivered[satellite])}
            if satellite == "SNPP":
                days.update({"2024-07-16", "2024-07-24", "2024-07-29"})
            chosen[satellite] = {day: hours[day] for day in sorted(days) if day in hours}
    return chosen


def _daynight(scans: list[dict]) -> dict[str, dict[str, int]]:
    result = {}
    for scan in scans:
        for key, count in scan["daynight"].items():
            satellite, flag = key.split("|", 1)
            result.setdefault(satellite, {})[flag] = count
    return {satellite: result[satellite] for satellite in SATELLITE_ORDER if satellite in result}


def _confidence_by_satellite(scans: list[dict]) -> dict[str, dict]:
    merged = {}
    for scan in scans:
        merged.update(_confidence_summary(scan))
    return {satellite: merged[satellite] for satellite in SATELLITE_ORDER if satellite in merged}


def _weekly(scans: list[dict]) -> dict[str, dict]:
    result = {}
    for scan in scans:
        for satellite, counts in scan["daily"].items():
            weeks = {}
            for key, count in scan["weekly"].items():
                sat, label = key.split("|", 1)
                if sat == satellite:
                    weeks[label] = count
            zero_rows = []
            for dates in scan["weekly_dates_with_zero_rows"].get(satellite, {}).values():
                zero_rows.extend(dates)
            result[satellite] = {"counts": weeks, "dates_with_zero_rows": zero_rows}
    return {satellite: result[satellite] for satellite in SATELLITE_ORDER if satellite in result}


def _spatial(scans: list[dict]) -> dict[str, dict]:
    result = {}
    for scan in scans:
        for satellite, cells in scan["spatial"].items():
            result[satellite] = {
                "occupied_cells": scan["occupied_cells"][satellite],
                "rows_in_cells": scan["cell_row_total"][satellite],
                "top_cells": cells,
            }
    return {satellite: result[satellite] for satellite in SATELLITE_ORDER if satellite in result}


def run_monthly(destination: Path = DESTINATION_DIR, manifest_path: Path = DEFAULT_MANIFEST, output_dir: Path = REPORTS_DIR) -> dict:
    before = {sensor: sha256_file(path) for sensor, path in SAMPLE_FILES.items()}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scans = []
    for spec in ARCHIVES:
        scans.append(scan_csv(destination / spec["relative_csv"], spec))
    after = {sensor: sha256_file(path) for sensor, path in SAMPLE_FILES.items()}
    sample_hashes = {
        sensor: {"before_scan": before[sensor], "after_scan": after[sensor], "unchanged": before[sensor] == after[sensor]}
        for sensor in before
    }
    coverage, eda = build_reports(scans, manifest, sample_hashes)
    figures = write_figures(scans, output_dir / "figures" / "monthly_2024_07")
    eda["figures"] = figures
    write_json(coverage, output_dir / "temporal_coverage_2024_07.json")
    write_text(render_coverage(coverage), output_dir / "temporal_coverage_2024_07.md")
    write_json(eda, output_dir / "monthly_eda_2024_07.json")
    write_text(render_eda(eda), output_dir / "monthly_eda_2024_07.md")
    return {"coverage": coverage, "eda": eda}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize the extracted July 2024 FIRMS CSVs.")
    parser.add_argument("--destination", type=Path, default=DESTINATION_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=REPORTS_DIR)
    args = parser.parse_args(argv)
    result = run_monthly(args.destination, args.manifest, args.output)
    integrity = result["coverage"]["integrity"]
    print(f"rows={integrity['total_rows']} difference={integrity['total_difference']}")
    print(f"Wrote {args.output / 'temporal_coverage_2024_07.md'}")
    print(f"Wrote {args.output / 'monthly_eda_2024_07.md'}")
    return 0 if integrity["total_difference"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
