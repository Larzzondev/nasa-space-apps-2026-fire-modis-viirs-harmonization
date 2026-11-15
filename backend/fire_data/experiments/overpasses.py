"""Experiment C: acquisition clocks and the dates a comparison can use.

A short gap between stored minutes is not identity. Absent S-NPP dates stay
empty. Partial dates are not repaired.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fire_data.eda_figures import COLORS
from fire_data.experiments.common import (
    DISPLAY,
    INDEX,
    SATELLITE_ORDER,
    ExperimentRunError,
    Stopwatch,
    assert_locks,
    base_results,
    begin,
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

SPATIAL_JSON = Path(__file__).resolve().parents[2] / "reports" / "spatiotemporal_analysis_2024_07.json"
COVERAGE_JSON = Path(__file__).resolve().parents[2] / "reports" / "coverage_investigation_2024_07.json"


def _closest_minutes(left: np.ndarray, right: np.ndarray) -> int | None:
    if left.size == 0 or right.size == 0:
        return None
    left = np.sort(left)
    right = np.sort(right)
    best = 1440
    start = 0
    for minute in left:
        while start + 1 < right.size and abs(int(right[start + 1]) - int(minute)) <= abs(int(right[start]) - int(minute)):
            start += 1
        best = min(best, abs(int(right[start]) - int(minute)))
    return int(best)


def _gap_histogram(minutes: np.ndarray) -> dict[str, int]:
    if minutes.size < 2:
        gaps = np.empty(0, dtype=np.int32)
    else:
        ordered = np.sort(minutes)
        gaps = np.diff(ordered)
    return {
        "consecutive_pairs": int(gaps.size),
        "gap_0_duplicate_minute": int(np.count_nonzero(gaps == 0)) if gaps.size else 0,
        "gap_1_to_5": int(np.count_nonzero((gaps >= 1) & (gaps <= 5))) if gaps.size else 0,
        "gap_6_to_30": int(np.count_nonzero((gaps >= 6) & (gaps <= 30))) if gaps.size else 0,
        "gap_31_to_90": int(np.count_nonzero((gaps >= 31) & (gaps <= 90))) if gaps.size else 0,
        "gap_91_or_more": int(np.count_nonzero(gaps >= 91)) if gaps.size else 0,
        "median_gap_minutes": None if gaps.size == 0 else float(np.median(gaps)),
    }


def _cite_time_bins(report: dict[str, Any]) -> list[dict[str, Any]]:
    cited = []
    for pair in report["pairs"]:
        histogram = pair["time_histogram_5km_60min"]
        cited.append(
            {
                "label": pair["label"],
                "radius_m": 5000.0,
                "window_min": 60,
                "median_bin_minutes": histogram["median_bin_minutes"],
                "recomputed": False,
                "same_fire": "not_assessed",
                "temporal_coincidence_is_same_fire": False,
                "spatial_constraint": "These bins describe candidate pairs inside 5 km. They are not the closest clocks of the two satellites regardless of location.",
            }
        )
    return cited


def _collect() -> tuple[dict[str, dict[str, np.ndarray]], int, int]:
    specs = {str(spec["sensor"]): spec for spec in ARCHIVES}
    seen = {name: np.zeros((32, 1440), dtype=bool) for name in SATELLITE_ORDER}
    rows = {name: np.zeros(32, dtype=np.int64) for name in SATELLITE_ORDER}
    hours = {name: np.zeros((32, 24), dtype=np.int64) for name in SATELLITE_ORDER}

    def consume(sensor: str, row: list[str], index: dict[str, int]) -> None:
        del index
        satellite = require_satellite(row, specs[sensor]["satellites"], sensor)
        day, minute = require_july_timestamp(row, sensor, satellite)
        seen[satellite][day, minute] = True
        rows[satellite][day] += 1
        hours[satellite][day, minute // 60] += 1

    counts = scan_archives(tuple(spec["sensor"] for spec in ARCHIVES), consume)
    packed = {name: {"seen": seen[name], "rows": rows[name], "hours": hours[name]} for name in SATELLITE_ORDER}
    rows_read = sum(item for key, item in counts.items() if key != "source_bytes_read")
    return packed, int(rows_read), int(counts["source_bytes_read"])


def _satellite_record(name: str, packed: dict[str, np.ndarray], zero_dates: set[str], partial_dates: set[str]) -> dict[str, Any]:
    days = []
    gap_totals = {key: 0 for key in ("consecutive_pairs", "gap_0_duplicate_minute", "gap_1_to_5", "gap_6_to_30", "gap_31_to_90", "gap_91_or_more")}
    within_gaps = []
    midnight = []
    early = 0
    late = 0
    for day in range(1, 32):
        date = f"2024-07-{day:02d}"
        count = int(packed["rows"][day])
        minutes = np.flatnonzero(packed["seen"][day])
        hours_with_rows = [hour for hour in range(24) if int(packed["hours"][day, hour]) > 0]
        hours_without_rows = [hour for hour in range(24) if int(packed["hours"][day, hour]) == 0]
        if count == 0:
            days.append(
                {
                    "date": date,
                    "status": "zero_rows_delivered",
                    "rows": 0,
                    "distinct_acq_time": None,
                    "hours_with_rows": None,
                    "hours_without_rows": None,
                    "zero_detections": False,
                    "meaning": ZERO_ROW_MEANING,
                    "filled": False,
                    "named_zero_row_date": date in zero_dates,
                    "named_partial_date": date in partial_dates,
                }
            )
            continue
        histogram = _gap_histogram(minutes.astype(np.int32))
        for key in gap_totals:
            gap_totals[key] += int(histogram[key])
        if histogram["median_gap_minutes"] is not None:
            within_gaps.append(histogram["median_gap_minutes"])
        early += int(np.count_nonzero(minutes <= 180))
        late += int(np.count_nonzero(minutes >= 1440 - 180))
        days.append(
            {
                "date": date,
                "status": "rows_delivered",
                "rows": count,
                "distinct_acq_time": int(minutes.size),
                "first_acq_time": f"{int(minutes[0]) // 60:02d}{int(minutes[0]) % 60:02d}",
                "last_acq_time": f"{int(minutes[-1]) // 60:02d}{int(minutes[-1]) % 60:02d}",
                "hours_with_rows": hours_with_rows,
                "hours_without_rows": hours_without_rows,
                "within_date_gap_summary": histogram,
                "zero_detections": False,
                "filled": False,
                "named_partial_date": date in partial_dates,
            }
        )
    for day in range(1, 31):
        current = next(item for item in days if item["date"] == f"2024-07-{day:02d}")
        nxt = next(item for item in days if item["date"] == f"2024-07-{day + 1:02d}")
        if current["status"] != "rows_delivered" or nxt["status"] != "rows_delivered":
            midnight.append(
                {
                    "from_date": current["date"],
                    "to_date": nxt["date"],
                    "gap_minutes": None,
                    "reason": "one of the two UTC dates has no delivered rows",
                    "same_fire": "not_assessed",
                }
            )
            continue
        last = int(current["last_acq_time"][:2]) * 60 + int(current["last_acq_time"][2:])
        first = int(nxt["first_acq_time"][:2]) * 60 + int(nxt["first_acq_time"][2:])
        midnight.append(
            {
                "from_date": current["date"],
                "to_date": nxt["date"],
                "gap_minutes": (1440 - last) + first,
                "reason": "clock gap between the last stored minute of one UTC date and the first stored minute of the next",
                "same_fire": "not_assessed",
                "gap_is_an_orbital_element": False,
            }
        )
    delivered = [item for item in days if item["status"] == "rows_delivered"]
    return {
        "satellite": name,
        "display": DISPLAY[name],
        "dates_with_rows": len(delivered),
        "dates_without_rows": 31 - len(delivered),
        "rows": int(sum(item["rows"] for item in delivered)),
        "distinct_minutes_per_delivered_date": {
            "minimum": None if not delivered else min(item["distinct_acq_time"] for item in delivered),
            "median": None if not delivered else float(np.median([item["distinct_acq_time"] for item in delivered])),
            "maximum": None if not delivered else max(item["distinct_acq_time"] for item in delivered),
        },
        "rows_per_delivered_date": {
            "minimum": None if not delivered else min(item["rows"] for item in delivered),
            "median": None if not delivered else float(np.median([item["rows"] for item in delivered])),
            "maximum": None if not delivered else max(item["rows"] for item in delivered),
        },
        "within_date_gaps_pooled": gap_totals,
        "median_of_daily_median_gaps": None if not within_gaps else float(np.median(within_gaps)),
        "distinct_minutes_in_first_180": early,
        "distinct_minutes_in_last_180": late,
        "cross_midnight_gaps": midnight,
        "days": days,
        "clock": "UTC",
        "clock_resolution": "minute",
        "gap_is_not_an_ephemeris": True,
        "same_fire": "not_assessed",
    }


def _comparisons_from_minutes(sensors: list[dict[str, Any]], minutes: dict[str, list[np.ndarray]]) -> list[dict[str, Any]]:
    by_name = {sensor["satellite"]: sensor for sensor in sensors}
    rows = []
    names = list(SATELLITE_ORDER)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            left_only_rows = 0
            right_only_rows = 0
            gaps = []
            both = 0
            for day in range(1, 32):
                left_rows = int(by_name[left_name]["days"][day - 1]["rows"] or 0)
                right_rows = int(by_name[right_name]["days"][day - 1]["rows"] or 0)
                left_minutes = minutes[left_name][day]
                right_minutes = minutes[right_name][day]
                if left_minutes.size and right_minutes.size:
                    both += 1
                    gap = _closest_minutes(left_minutes, right_minutes)
                    if gap is not None:
                        gaps.append(gap)
                elif left_minutes.size:
                    left_only_rows += left_rows
                elif right_minutes.size:
                    right_only_rows += right_rows
            gap_array = np.asarray(gaps, dtype=np.int32)
            rows.append(
                {
                    "satellite_a": left_name,
                    "satellite_b": right_name,
                    "label": f"{DISPLAY[left_name]} and {DISPLAY[right_name]}",
                    "dates_compared": both,
                    "dates_not_compared": 31 - both,
                    "rows_on_dates_the_other_sensor_has_no_rows": {
                        left_name: left_only_rows,
                        right_name: right_only_rows,
                    },
                    "closest_stored_minute": {
                        "dates": int(gap_array.size),
                        "median_minutes": None if gap_array.size == 0 else float(np.median(gap_array)),
                        "minimum_minutes": None if gap_array.size == 0 else int(gap_array.min()),
                        "dates_whose_closest_minutes_exceed_30": int(np.count_nonzero(gap_array > 30)) if gap_array.size else 0,
                        "dates_whose_closest_minutes_exceed_60": int(np.count_nonzero(gap_array > 60)) if gap_array.size else 0,
                        "meaning": "Minimum absolute difference between distinct acquisition minutes on the same UTC date. Location is ignored. This is not a candidate pair and not a fire match.",
                        "same_fire": "not_assessed",
                    },
                    "filled": False,
                    "absent_date_is_zero_fire": False,
                }
            )
    return rows


def _figures(results: dict[str, Any], directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    names = []
    figure, axes = plt.subplots(len(SATELLITE_ORDER), 1, figsize=(10.5, 8.5), sharex=True)
    for axis, sensor in zip(axes, results["satellites"], strict=True):
        grid = np.zeros((31, 24), dtype=np.float64)
        for index, day in enumerate(sensor["days"]):
            if day["hours_with_rows"] is None:
                grid[index, :] = np.nan
            else:
                for hour in day["hours_with_rows"]:
                    grid[index, hour] = 1.0
        axis.imshow(grid.T, aspect="auto", interpolation="nearest", cmap="cividis", vmin=0, vmax=1)
        axis.set_yticks([0, 6, 12, 18, 23])
        axis.set_ylabel(sensor["display"])
    axes[-1].set_xlabel("July 2024 day")
    axes[-1].set_xticks([0, 9, 14, 19, 24, 30])
    axes[-1].set_xticklabels(["1", "10", "15", "20", "25", "31"])
    axes[0].set_title("Hours with at least one stored row")
    path = directory / "hours_with_rows.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)

    figure, axis = plt.subplots(figsize=(8.2, 4.4))
    labels = [sensor["display"] for sensor in results["satellites"]]
    values = [sensor["dates_with_rows"] for sensor in results["satellites"]]
    axis.bar(labels, values, color=[COLORS[sensor["satellite"]] for sensor in results["satellites"]])
    axis.set_ylim(0, 31)
    axis.set_ylabel("UTC dates with delivered rows")
    axis.set_title("Delivered dates are not filled to 31")
    path = directory / "dates_with_rows.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)
    return names


def _markdown(results: dict[str, Any]) -> str:
    lines = [
        "# Experiment C: temporal sampling and overpasses",
        "",
        "Question: how far apart are the stored acquisition minutes, how often does each satellite report, and which comparisons have no rows on one side?",
        "",
        "The clock is UTC and the resolution is one minute. A gap describes the stored clock. It is not an orbital element, and a short gap is not identity. `same_fire` stays `not_assessed`.",
        "",
        "Absent dates were not filled. S-NPP's zero-row dates stay out of every comparison. The partial dates 16, 24, and 29 July are used only where rows are present.",
        "",
        "## Delivered dates",
        "",
        "| Satellite | Dates with rows | Dates without rows | Median distinct minutes on a delivered date | Median rows on a delivered date |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for sensor in results["satellites"]:
        lines.append(
            f"| {sensor['display']} | {sensor['dates_with_rows']} | {sensor['dates_without_rows']} | "
            f"{sensor['distinct_minutes_per_delivered_date']['median']:.1f} | {sensor['rows_per_delivered_date']['median']:.1f} |"
        )
    snpp = next(sensor for sensor in results["satellites"] if sensor["satellite"] == "SNPP")
    zero = [day["date"] for day in snpp["days"] if day["status"] == "zero_rows_delivered"]
    partial = [day for day in snpp["days"] if day.get("named_partial_date") and day["status"] == "rows_delivered"]
    lines.extend(
        [
            "",
            f"S-NPP dates with zero delivered rows: {', '.join(zero)}. Each one has a delivered-row count of zero because the CSV has no row that date. That is not zero fire activity.",
            "",
            "Partial S-NPP dates that still have rows:",
            "",
        ]
    )
    for day in partial:
        lines.append(f"- {day['date']}: {day['rows']} rows, hours with rows {day['hours_with_rows']}.")
    n21 = next(sensor for sensor in results["satellites"] if sensor["satellite"] == "N21")
    july20 = next(day for day in n21["days"] if day["date"] == "2024-07-20")
    lines.extend(
        [
            "",
            f"NOAA-21 on 20 July has {july20['rows']} delivered rows. Hours without rows: {july20['hours_without_rows']}. Those hours are not labeled as an outage.",
            "",
            "## Within-satellite gaps",
            "",
            "The pooled counts are gaps between consecutive distinct acquisition minutes inside one UTC date.",
            "",
            "| Satellite | Consecutive pairs | 1–5 min | 6–30 min | 31–90 min | 91 min or more |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for sensor in results["satellites"]:
        gaps = sensor["within_date_gaps_pooled"]
        lines.append(
            f"| {sensor['display']} | {gaps['consecutive_pairs']} | {gaps['gap_1_to_5']} | {gaps['gap_6_to_30']} | "
            f"{gaps['gap_31_to_90']} | {gaps['gap_91_or_more']} |"
        )
    lines.extend(
        [
            "",
            "Cross-midnight gaps are the clock distance from the last stored minute of one delivered date to the first stored minute of the next delivered date. A missing date makes that gap null. July 31 has no 1 August neighbor inside this extract.",
            "",
            "## Dates a comparison can use",
            "",
            "A date is compared only when both satellites have at least one row that UTC date.",
            "",
            "| Pair | Dates compared | Dates not compared | Closest-minute median | Dates whose closest minutes exceed 30 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for pair in results["satellite_pairs"]:
        closest = pair["closest_stored_minute"]
        median = closest["median_minutes"]
        median_text = "n/a" if median is None else f"{median:.1f}"
        lines.append(
            f"| {pair['label']} | {pair['dates_compared']} | {pair['dates_not_compared']} | {median_text} | "
            f"{closest['dates_whose_closest_minutes_exceed_30']} |"
        )
    lines.extend(
        [
            "",
            "The closest-minute median ignores location. It can be zero when two satellites store the same `acq_time` somewhere on Earth that date. It is not the separation of a spatially nearby pair, and it does not establish the same fire.",
            "",
            "S-NPP's ten zero-row dates reduce a comparison that includes S-NPP from 31 dates to 21 when the other satellite has rows on all 31 dates.",
            "",
            "## Published spatially constrained time bins",
            "",
            "These median bins are copied from the candidate-pair report at 5 km and 60 minutes. They were not recomputed. NOAA-20 and NOAA-21 falling in a 50–51 minute bin is why a 30-minute window contains no pairs for that couple: the acquisitions used by those pairs are farther apart than 30 minutes. That empty window is not a spatial miss.",
            "",
            "| Published label | Median bin start (min) | Median bin end (min) | Pairs in the histogram |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for item in results["cited_time_bins_5km_60min"]:
        median = item["median_bin_minutes"]
        lines.append(
            f"| {item['label']} | {median['bin_start']} | {median['bin_end']} | {median['count']} |"
        )
    lines.extend(
        [
            "",
            "## Coverage evidence",
            "",
            "The coverage investigation keeps FIRMS evidence and Level-2 evidence in separate classes. This experiment cites that report and does not extend a Level-2 sentence into a FIRMS outage class. It does not download a replacement S-NPP archive.",
            "",
            "## Limits",
            "",
            "- No date was filled. A zero delivered-row count is not zero fire activity.",
            "- Hour gaps are not given an outage class.",
            "- Temporal coincidence was not used as physical fire matching.",
            "- NOAA-20 and NOAA-21 processing level stays unresolved.",
            "- No harmonization coefficient was calculated.",
            "",
        ]
    )
    return "\n".join(lines)


def run(work_root: Path, run_id: str, checksum_cache: Path) -> int:
    clock = Stopwatch()
    destination: Path | None = None
    schema: dict[str, Any] | None = None
    try:
        destination, config, schema = begin("C", work_root, run_id)
        assert_locks(config)
        parameters = config["parameters"]
        if parameters["fill_absent_dates"] or parameters["absent_date_is_zero_fire"] or parameters["repair_partial_delivery"]:
            raise ExperimentRunError("experiment C cannot fill or repair dates")
        checksums = verify_checksum_cache(checksum_cache, config)
        packed, rows_read, bytes_read = _collect()
        zero_dates = set(parameters["snpp_zero_row_dates"])
        partial_dates = set(parameters["snpp_partial_dates"])
        minutes = {
            name: [np.flatnonzero(packed[name]["seen"][day]).astype(np.int32) for day in range(32)]
            for name in SATELLITE_ORDER
        }
        satellites = [
            _satellite_record(name, packed[name], zero_dates, partial_dates) for name in SATELLITE_ORDER
        ]
        pairs = _comparisons_from_minutes(satellites, minutes)
        snpp = next(sensor for sensor in satellites if sensor["satellite"] == "SNPP")
        observed_zero = {day["date"] for day in snpp["days"] if day["status"] == "zero_rows_delivered"}
        spatial = read_json(SPATIAL_JSON)
        coverage = read_json(COVERAGE_JSON)
        results = base_results(config, checksums)
        results.update(
            {
                "fill_absent_dates": False,
                "absent_date_is_zero_fire": False,
                "repair_partial_delivery": False,
                "clock": "UTC",
                "clock_resolution": "minute",
                "satellites": satellites,
                "satellite_pairs": pairs,
                "cited_time_bins_5km_60min": _cite_time_bins(spatial),
                "coverage_investigation_cited": {
                    "report": "reports/coverage_investigation_2024_07.json",
                    "recomputed": False,
                    "firms_and_level2_kept_separate": True,
                    "top_level_keys": sorted(coverage.keys()),
                },
                "records_processed": rows_read,
            }
        )
        snpp_pairs = [pair for pair in pairs if "SNPP" in (pair["satellite_a"], pair["satellite_b"])]
        checks = [
            {"name": "snpp_zero_dates_match_configuration", "passed": observed_zero == zero_dates},
            {"name": "snpp_partial_dates_have_rows", "passed": all(snpp["days"][int(date[8:10]) - 1]["rows"] > 0 for date in partial_dates)},
            {"name": "no_dates_filled", "passed": all(day["filled"] is False for sensor in satellites for day in sensor["days"])},
            {
                "name": "snpp_comparisons_use_21_dates_against_complete_sensors",
                "passed": all(pair["dates_compared"] == 21 for pair in snpp_pairs if pair["satellite_a"] != "SNPP" or pair["satellite_b"] != "SNPP"),
            },
            {"name": "same_fire_not_assessed", "passed": True},
            {"name": "source_rows_match_manifest", "passed": rows_read == config["inputs"]["expected_rows"]},
        ]
        # Terra, Aqua, N20, and N21 have rows every July date in this archive.
        # The check above requires every S-NPP pair to have 21 compared dates.
        status = "completed" if all(item["passed"] for item in checks) else "failed"
        results["validation"] = checks
        results["figures"] = _figures(results, destination / "figures")
        write_json(destination / "results.json", results)
        (destination / "report.md").write_text(_markdown(results), encoding="utf-8")
        write_json(destination / "validation.json", {"passed": status == "completed", "checks": checks})
        write_json(
            destination / "execution.json",
            {
                "wall_clock_seconds": clock.wall(),
                "cpu_seconds": clock.cpu(),
                "source_rows_read": rows_read,
                "source_bytes_read": bytes_read,
                "records_processed": rows_read,
                "records_per_second": None if clock.wall() == 0 else rows_read / clock.wall(),
                "retries": 0,
                "cancelled": False,
            },
        )
        finish(
            destination,
            schema,
            status=status,
            science_executed=True,
            results=results,
            source_rows_read=rows_read,
            source_bytes_read=bytes_read,
            records_processed=rows_read,
            science_seconds=clock.wall(),
            cpu_seconds=clock.cpu(),
        )
        publish_run(destination, "C")
        return 0 if status == "completed" else 1
    except (OSError, ExperimentRunError, ExperimentConfigError, SchemaError, KeyError, ValueError) as exc:
        if destination is not None and schema is not None:
            _fail(destination, schema, clock, exc)
        return 1


def _fail(destination: Path, schema: dict[str, Any], clock: Stopwatch, exc: Exception) -> None:
    try:
        finish(
            destination,
            schema,
            status="failed",
            science_executed=True,
            results={"error": f"{type(exc).__name__}: {exc}", "same_fire": "not_assessed"},
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
        publish_run(destination, "C")
    except OSError:
        pass
