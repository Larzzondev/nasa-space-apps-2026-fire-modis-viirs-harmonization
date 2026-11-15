"""Experiment B: FRP, brightness, scan, track, and confidence by satellite.

Quantiles keep non-positive FRP. A published FRP ratio is cited and is not a
slope, intercept, or harmonization coefficient.
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
    confidence_code,
    daynight_code,
    finish,
    publish_run,
    quantiles,
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
from fire_data.monthly_scan import ARCHIVES
from fire_data.spatiotemporal_analysis import VIIRS_FLAGS

EDA_JSON = Path(__file__).resolve().parents[2] / "reports" / "monthly_eda_2024_07.json"
NEIGHBOR_JSON = Path(__file__).resolve().parents[2] / "reports" / "nearest_neighbor_analysis_2024_07.json"


def _stratum(name: str, mask: np.ndarray, frp: np.ndarray, brightness: np.ndarray, scan: np.ndarray, track: np.ndarray) -> dict[str, Any]:
    chosen = frp[mask]
    positive = chosen[chosen > 0]
    return {
        "stratum": name,
        "rows": int(np.count_nonzero(mask)),
        "nonpositive_frp_rows": int(np.count_nonzero(chosen <= 0)),
        "negative_frp_rows": int(np.count_nonzero(chosen < 0)),
        "zero_frp_rows": int(np.count_nonzero(chosen == 0)),
        "frp_all_rows": quantiles(chosen),
        "frp_positive_only": quantiles(positive),
        "frp_positive_only_is_not_the_all_row_distribution": True,
        "brightness": quantiles(brightness[mask]),
        "scan": quantiles(scan[mask]),
        "track": quantiles(track[mask]),
    }


def _scan_bins(scan: np.ndarray) -> tuple[np.ndarray, list[float]]:
    edges = [float(value) for value in np.quantile(scan, [0.25, 0.5, 0.75], method="linear")]
    bins = np.zeros(scan.size, dtype=np.int8)
    bins[scan > edges[0]] = 1
    bins[scan > edges[1]] = 2
    bins[scan > edges[2]] = 3
    return bins, edges


def _modis_bins(confidence: np.ndarray) -> dict[str, int]:
    return {
        "0_to_29": int(np.count_nonzero(confidence <= 29)),
        "30_to_79": int(np.count_nonzero((confidence >= 30) & (confidence <= 79))),
        "80_to_100": int(np.count_nonzero(confidence >= 80)),
        "scale": "modis_0_100",
        "converted_to_viirs_flags": False,
    }


def _viirs_counts(confidence: np.ndarray) -> dict[str, int | bool]:
    return {
        "l": int(np.count_nonzero(confidence == 0)),
        "n": int(np.count_nonzero(confidence == 1)),
        "h": int(np.count_nonzero(confidence == 2)),
        "scale": "viirs_lnh",
        "converted_to_modis_score": False,
    }


def _brightness_367(brightness: np.ndarray, confidence: np.ndarray, scale: str) -> dict[str, Any]:
    exact = brightness == 367.0
    record = {
        "rows_stored_at_367_k": int(np.count_nonzero(exact)),
        "rows_in_360_to_367_exclusive": int(np.count_nonzero((brightness >= 360.0) & (brightness < 367.0))),
        "rows_above_367_k": int(np.count_nonzero(brightness > 367.0)),
        "brightness_367_is_confirmed_saturation": False,
    }
    if scale == "viirs_lnh":
        record["rows_at_367_k_with_flag_h"] = int(np.count_nonzero(exact & (confidence == VIIRS_FLAGS.index("h"))))
        record["rows_at_367_k_with_flag_other_than_h"] = int(np.count_nonzero(exact & (confidence != VIIRS_FLAGS.index("h"))))
    return record


def _cite_ratios(report: dict[str, Any]) -> list[dict[str, Any]]:
    cited = []
    for pair in report["pairs"]:
        for item in pair["thresholds"]:
            if float(item["radius_m"]) != 1000.0:
                continue
            ratio = item["frp_directed"]["ratio_other_over_reference"]
            cited.append(
                {
                    "label": pair["label"],
                    "radius_m": 1000.0,
                    "window_min": int(item["max_delta_minutes"]),
                    "ratio_count": ratio.get("count"),
                    "ratio_p50": ratio.get("p50"),
                    "ratio_p10": ratio.get("p10"),
                    "ratio_p90": ratio.get("p90"),
                    "excluded_nonpositive_frp_pairs": item["frp_directed"]["excluded_nonpositive_frp_pairs"],
                    "ratio_definition": "partner_over_reference_when_both_positive",
                    "ratio_is_a_harmonization_coefficient": False,
                    "pairs_are_independent": False,
                    "same_fire": "not_assessed",
                    "recomputed": False,
                }
            )
    return cited


def _cite_daynight(report: dict[str, Any]) -> list[dict[str, Any]]:
    cited = []
    for pair in report["pairs"]:
        for item in pair["thresholds"]:
            if float(item["radius_m"]) != 1000.0 or int(item["max_delta_minutes"]) != 30:
                continue
            cited.append(
                {
                    "label": pair["label"],
                    "radius_m": 1000.0,
                    "window_min": 30,
                    "daynight_pairs": item["daynight_directed"],
                    "meaning": "Stored day/night flags of the two rows. Not a shared fire.",
                    "same_fire": "not_assessed",
                    "recomputed": False,
                }
            )
    return cited


def _collect(config: dict[str, Any]) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, dict[str, Any]], int, int]:
    specs = {str(spec["sensor"]): spec for spec in ARCHIVES}
    capacity = {
        satellite: int(count)
        for archive in config["inputs"]["archives"]
        for satellite, count in archive["satellites"].items()
    }
    columns = {
        satellite: {
            "frp": np.empty(count, dtype=np.float64),
            "brightness": np.empty(count, dtype=np.float64),
            "scan": np.empty(count, dtype=np.float64),
            "track": np.empty(count, dtype=np.float64),
            "daynight": np.empty(count, dtype=np.int8),
            "confidence": np.empty(count, dtype=np.int16),
            "type": np.empty(count, dtype=np.int8),
        }
        for satellite, count in capacity.items()
    }
    cursor = {satellite: 0 for satellite in capacity}
    identity: dict[str, dict[str, Any]] = {
        satellite: {"instrument": {}, "version": {}, "unexpected_type": {}} for satellite in capacity
    }

    def consume(sensor: str, row: list[str], index: dict[str, int]) -> None:
        del index
        spec = specs[sensor]
        satellite = require_satellite(row, spec["satellites"], sensor)
        require_july_timestamp(row, sensor, satellite)
        position = cursor[satellite]
        if position >= capacity[satellite]:
            raise ExperimentRunError(f"{satellite} exceeded the configuration row count")
        bucket = columns[satellite]
        bucket["frp"][position] = float(row[INDEX["frp"]])
        bucket["brightness"][position] = float(row[INDEX["brightness"]])
        bucket["scan"][position] = float(row[INDEX["scan"]])
        bucket["track"][position] = float(row[INDEX["track"]])
        bucket["daynight"][position] = daynight_code(row, sensor)
        bucket["confidence"][position] = confidence_code(row, str(spec["confidence"]), sensor)
        stored_type = row[INDEX["type"]]
        if stored_type in {"0", "1", "2", "3"}:
            bucket["type"][position] = int(stored_type)
        else:
            bucket["type"][position] = -1
            unexpected = identity[satellite]["unexpected_type"]
            unexpected[stored_type] = unexpected.get(stored_type, 0) + 1
        seen = identity[satellite]
        instrument = row[INDEX["instrument"]]
        version = row[INDEX["version"]]
        seen["instrument"][instrument] = seen["instrument"].get(instrument, 0) + 1
        seen["version"][version] = seen["version"].get(version, 0) + 1
        cursor[satellite] = position + 1

    counts = scan_archives(tuple(spec["sensor"] for spec in ARCHIVES), consume)
    for satellite, count in capacity.items():
        if cursor[satellite] != count:
            raise ExperimentRunError(f"{satellite} has {cursor[satellite]} rows; the configuration records {count}")
    rows_read = sum(item for key, item in counts.items() if key != "source_bytes_read")
    return columns, identity, int(rows_read), int(counts["source_bytes_read"])


def _satellite_record(
    name: str,
    table: dict[str, Any],
    identity: dict[str, dict[str, int]],
    scale: str,
    published_eda: dict[str, Any],
) -> dict[str, Any]:
    frp = table["frp"]
    brightness = table["brightness"]
    scan = table["scan"]
    track = table["track"]
    daynight = table["daynight"]
    confidence = table["confidence"]
    bins, edges = _scan_bins(scan)
    strata = [
        _stratum("all_rows", np.ones(frp.size, dtype=bool), frp, brightness, scan, track),
        _stratum("day", daynight == 0, frp, brightness, scan, track),
        _stratum("night", daynight == 1, frp, brightness, scan, track),
    ]
    for index, label in enumerate(("scan_quartile_1", "scan_quartile_2", "scan_quartile_3", "scan_quartile_4")):
        strata.append(_stratum(label, bins == index, frp, brightness, scan, track))
    published = published_eda["satellites"][name]
    recomputed_median = float(np.median(frp))
    published_quantile = float(published["frp"]["quantiles"]["0.500"])
    type_codes, type_counts_array = np.unique(table["type"], return_counts=True)
    type_counts = {str(int(code)): int(count) for code, count in zip(type_codes, type_counts_array, strict=True) if int(code) >= 0}
    return {
        "satellite": name,
        "display": DISPLAY[name],
        "stored_instrument": identity["instrument"],
        "version_text": identity["version"],
        "processing_level": "unresolved",
        "rows": int(frp.size),
        "scan_quartile_edges_km": edges,
        "scan_quartile_rule": "A row stays in the lower bin when it equals a quartile edge.",
        "strata": strata,
        "brightness_367": _brightness_367(brightness, confidence, scale),
        "confidence": _modis_bins(confidence) if scale == "modis_0_100" else _viirs_counts(confidence),
        "confidence_quantiles_native": quantiles(confidence.astype(np.float64)) if scale == "modis_0_100" else None,
        "type_stored_codes": type_counts,
        "unexpected_type_codes": identity["unexpected_type"],
        "type_codes_were_not_named": True,
        "published_monthly_eda": {
            "recomputed": False,
            "frp_median": published["frp"]["median"],
            "frp_quantile_0_500": published_quantile,
            "brightness_median": published["brightness"]["median"],
            "day_rows": published_eda["daynight"][name]["D"],
            "night_rows": published_eda["daynight"][name]["N"],
            "frp_zero_rows": published["frp"]["zero_count"],
        },
        "recomputed_matches_published_eda": {
            "frp_median": bool(np.isclose(recomputed_median, float(published["frp"]["median"]), rtol=0.0, atol=1e-9)),
            "frp_quantile_0_500": bool(np.isclose(strata[0]["frp_all_rows"]["p50"], published_quantile, rtol=0.0, atol=1e-6)),
            "day_rows": int(np.count_nonzero(daynight == 0)) == int(published_eda["daynight"][name]["D"]),
            "night_rows": int(np.count_nonzero(daynight == 1)) == int(published_eda["daynight"][name]["N"]),
            "zero_frp_rows": int(np.count_nonzero(frp == 0)) == int(published["frp"]["zero_count"]),
        },
        "same_fire": "not_assessed",
    }


def _figures(results: dict[str, Any], directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    names = []
    labels = [DISPLAY[name] for name in SATELLITE_ORDER]
    lookup = {sensor["satellite"]: sensor for sensor in results["satellites"]}

    def stratum(name: str, label: str) -> dict[str, Any]:
        return next(item for item in lookup[name]["strata"] if item["stratum"] == label)

    figure, axis = plt.subplots(figsize=(8.2, 4.6))
    medians = [stratum(name, "all_rows")["frp_all_rows"]["p50"] for name in SATELLITE_ORDER]
    low = [stratum(name, "all_rows")["frp_all_rows"]["p10"] for name in SATELLITE_ORDER]
    high = [stratum(name, "all_rows")["frp_all_rows"]["p90"] for name in SATELLITE_ORDER]
    positions = np.arange(len(labels))
    axis.bar(positions, medians, color=[COLORS[name] for name in SATELLITE_ORDER])
    axis.vlines(positions, low, high, color="#1f1a17")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel("FRP (MW)")
    axis.set_title("All-row FRP median, with the p10–p90 interval")
    path = directory / "frp_all_rows.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)

    figure, axis = plt.subplots(figsize=(8.2, 4.6))
    width = 0.36
    day = [stratum(name, "day")["frp_all_rows"]["p50"] for name in SATELLITE_ORDER]
    night = [stratum(name, "night")["frp_all_rows"]["p50"] for name in SATELLITE_ORDER]
    axis.bar(positions - width / 2, day, width=width, color="#d4a017", label="Day")
    axis.bar(positions + width / 2, night, width=width, color="#243447", label="Night")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel("Median FRP (MW)")
    axis.set_title("All-row median FRP by stored day/night flag")
    axis.legend(frameon=False)
    path = directory / "frp_day_night.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)

    figure, axis = plt.subplots(figsize=(8.8, 4.8))
    quartile_names = ("scan_quartile_1", "scan_quartile_2", "scan_quartile_3", "scan_quartile_4")
    for name in SATELLITE_ORDER:
        series = [stratum(name, label)["frp_all_rows"]["p50"] for label in quartile_names]
        axis.plot([1, 2, 3, 4], series, marker="o", color=COLORS[name], label=DISPLAY[name])
    axis.set_xticks([1, 2, 3, 4])
    axis.set_xlabel("Scan quartile within the satellite")
    axis.set_ylabel("Median FRP (MW)")
    axis.set_title("Conditional median FRP by scan quartile")
    axis.legend(ncol=3, frameon=False)
    path = directory / "frp_by_scan_quartile.png"
    save_figure(figure, path)
    plt.close(figure)
    names.append(path.name)
    return names


def _markdown(results: dict[str, Any]) -> str:
    lines = [
        "# Experiment B: sensor measurement relationships",
        "",
        "Question: how do FRP, brightness, scan, track, confidence, and day/night differ among the five satellites when every stored row stays in the distribution?",
        "",
        "No slope, intercept, or harmonization coefficient is estimated. The published positive-FRP ratios are cited. They are partner divided by reference, and only when both values are positive. Non-positive rows remain in the all-row quantiles and are counted beside any ratio.",
        "",
        f"`same_fire` is `{results['same_fire']}`. Terra and Aqua stay separate. A cited pair keeps its published label.",
        "",
        "## All-row distributions",
        "",
        "The p50 column is the linear quantile of every finite row, including non-positive FRP. The median column is `numpy.median` of those same rows.",
        "",
        "| Satellite | Rows | FRP p50 (MW) | FRP non-positive | Brightness p50 (K) | Scan p50 (km) | Track p50 (km) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    lookup = {sensor["satellite"]: sensor for sensor in results["satellites"]}
    for name in SATELLITE_ORDER:
        sensor = lookup[name]
        all_rows = sensor["strata"][0]
        lines.append(
            f"| {sensor['display']} | {sensor['rows']} | {all_rows['frp_all_rows']['p50']:.3f} | "
            f"{all_rows['nonpositive_frp_rows']} | {all_rows['brightness']['p50']:.3f} | "
            f"{all_rows['scan']['p50']:.3f} | {all_rows['track']['p50']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Day and night",
            "",
            "Day and night are the stored flags. They are not recomputed from the clock.",
            "",
            "| Satellite | Day rows | Day FRP p50 | Night rows | Night FRP p50 | Night brightness p50 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in SATELLITE_ORDER:
        sensor = lookup[name]
        day = next(item for item in sensor["strata"] if item["stratum"] == "day")
        night = next(item for item in sensor["strata"] if item["stratum"] == "night")
        lines.append(
            f"| {sensor['display']} | {day['rows']} | {day['frp_all_rows']['p50']:.3f} | {night['rows']} | "
            f"{night['frp_all_rows']['p50']:.3f} | {night['brightness']['p50']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Scan quartiles",
            "",
            "Quartile edges are computed inside each satellite. A larger FRP in a larger scan bin is a conditional description of the stored columns. It is not a fire-size result and it is not a fitted line.",
            "",
            "| Satellite | Q1 FRP p50 | Q2 FRP p50 | Q3 FRP p50 | Q4 FRP p50 | Q4 scan p50 (km) |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in SATELLITE_ORDER:
        sensor = lookup[name]
        cells = []
        q4_scan = None
        for label in ("scan_quartile_1", "scan_quartile_2", "scan_quartile_3", "scan_quartile_4"):
            item = next(row for row in sensor["strata"] if row["stratum"] == label)
            value = item["frp_all_rows"]["p50"]
            cells.append("n/a" if value is None else f"{value:.3f}")
            if label == "scan_quartile_4":
                q4_scan = item["scan"]["p50"]
        lines.append(f"| {sensor['display']} | " + " | ".join(cells) + f" | {q4_scan:.3f} |")
    lines.extend(
        [
            "",
            "## Brightness at 367 K",
            "",
            "A stored VIIRS brightness of 367 K is counted. It is not marked as confirmed saturation. The files have no Level-1 saturation flag. MODIS brightness is a different stored temperature.",
            "",
            "| Satellite | Rows at 367 K | Rows in [360, 367) | Rows above 367 K |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for name in SATELLITE_ORDER:
        item = lookup[name]["brightness_367"]
        lines.append(
            f"| {lookup[name]['display']} | {item['rows_stored_at_367_k']} | "
            f"{item['rows_in_360_to_367_exclusive']} | {item['rows_above_367_k']} |"
        )
    lines.extend(
        [
            "",
            "## Native confidence and type",
            "",
            "MODIS confidence stays on 0–100. The 0–29, 30–79, and 80–100 groups repeat the published reporting split. VIIRS flags stay `l`, `n`, and `h`. The scales are not converted. `type` is counted as the stored codes 0, 1, 2, and 3. Those codes are not named.",
            "",
            "Counts are in `results.json`.",
            "",
            "## Published positive-FRP ratios",
            "",
            "These ratios were not recomputed. Each one is the other sensor's FRP divided by the reference sensor's FRP when both are positive. The excluded-pair count sits beside the ratio. A ratio quantile is not a coefficient.",
            "",
            "| Published label | Window (min) | Ratio rows | p50 | Excluded non-positive pairs |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in results["cited_positive_frp_ratios_1km"]:
        if item["window_min"] != 30:
            continue
        p50 = item["ratio_p50"]
        p50_text = "n/a" if p50 is None else f"{float(p50):.3f}"
        lines.append(
            f"| {item['label']} | {item['window_min']} | {item['ratio_count']} | {p50_text} | {item['excluded_nonpositive_frp_pairs']} |"
        )
    lines.extend(
        [
            "",
            "The 30-minute window is the cited comparison above. Other 1 km windows remain in the JSON. Published day/night pair labels at 1 km and 30 minutes are stored flags of the two rows, not a shared fire.",
            "",
            "## Agreement with the monthly EDA",
            "",
            "All-row FRP medians, the 0.500 FRP quantile, day/night counts, and zero-FRP counts were compared with `reports/monthly_eda_2024_07.json`.",
            "",
            "## Limits",
            "",
            "- Non-positive FRP stays in every distribution that claims to describe all rows.",
            "- Positive-only quantiles are labeled separately.",
            "- `bright_t31` was not renamed and was not entered into a coefficient.",
            "- NOAA-20 and NOAA-21 processing level stays unresolved.",
            "- XGBoost was not trained.",
            "",
        ]
    )
    return "\n".join(lines)


def run(work_root: Path, run_id: str, checksum_cache: Path) -> int:
    clock = Stopwatch()
    destination: Path | None = None
    schema: dict[str, Any] | None = None
    try:
        destination, config, schema = begin("B", work_root, run_id)
        assert_locks(config)
        if config["parameters"]["estimate_calibration_coefficient"] or config["parameters"]["fit_regression"]:
            raise ExperimentRunError("experiment B cannot fit a coefficient")
        checksums = verify_checksum_cache(checksum_cache, config)
        eda = read_json(EDA_JSON)
        neighbors = read_json(NEIGHBOR_JSON)
        arrays, identity, rows_read, bytes_read = _collect(config)
        scales = {}
        for archive in config["inputs"]["archives"]:
            for satellite in archive["satellites"]:
                scales[satellite] = "viirs_lnh" if archive["confidence"] == "viirs_lnh" else "modis_0_100"
        satellites = [
            _satellite_record(name, arrays[name], identity[name], scales[name], eda) for name in SATELLITE_ORDER
        ]
        del arrays
        results = base_results(config, checksums)
        results.update(
            {
                "estimate_calibration_coefficient": False,
                "fit_regression": False,
                "frp_quantiles_include_nonpositive": True,
                "confidence_scales_converted": False,
                "brightness_367_is_confirmed_saturation": False,
                "satellites": satellites,
                "cited_positive_frp_ratios_1km": _cite_ratios(neighbors),
                "cited_daynight_pair_labels_1km_30min": _cite_daynight(neighbors),
                "records_processed": rows_read,
            }
        )
        matched = all(all(sensor["recomputed_matches_published_eda"].values()) for sensor in satellites)
        checks = [
            {"name": "eda_marginal_totals_match", "passed": matched},
            {"name": "no_coefficient", "passed": results["harmonization_coefficient"] is None},
            {"name": "same_fire_not_assessed", "passed": True},
            {"name": "ratios_not_recomputed", "passed": all(item["recomputed"] is False for item in results["cited_positive_frp_ratios_1km"])},
            {"name": "source_rows_match_manifest", "passed": rows_read == config["inputs"]["expected_rows"]},
        ]
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
        publish_run(destination, "B")
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
        publish_run(destination, "B")
    except OSError:
        pass
