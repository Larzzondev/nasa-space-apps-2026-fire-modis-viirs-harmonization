"""Write the July 2024 coverage and exploratory reports."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

LIMITATIONS = (
    "MODIS and VIIRS have different spatial resolutions and detection characteristics. Row counts are not a comparison of sensitivity.",
    "Repeat detections are not necessarily unique fires. Exact duplicate rows and repeated location-time keys are retained.",
    "A date with zero delivered rows, and a date whose source file is missing, are not zero fire detections.",
    "MODIS confidence is an integer from 0 through 100. VIIRS confidence is the flag l, n, or h. The scales are not interchangeable.",
    "Processing-level provenance stays unresolved. The ZIP name, the fire_archive prefix, and the version field are not treated as a processing stream.",
    "One month cannot establish a globally valid harmonization factor. No coefficient is calculated.",
    "Spatial proximity is not assessed here and cannot, by itself, prove that two observations are the same fire.",
    "FRP is the stored fire radiative power value. It is not fire size and it is not total fire energy.",
)


def _count(value: int) -> str:
    return f"{value:,}"


def _num(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _quantile_line(summary: dict) -> str:
    quantiles = summary["quantiles"]
    return (
        f"median {_num(summary['median'])}, mean {_num(summary['mean'])}, "
        f"p05 {_num(quantiles['0.050'])}, p95 {_num(quantiles['0.950'])}, "
        f"p99 {_num(quantiles['0.990'])}, maximum {_num(summary['maximum'])}"
    )


def _hour_phrase(counts: list[int]) -> str:
    present = [hour for hour, count in enumerate(counts) if count]
    if not present:
        return "no UTC hour contains a row"
    missing_inside = [hour for hour in range(present[0], present[-1] + 1) if hour not in present]
    phrase = (
        f"rows fall in {len(present)} UTC hours, from {present[0]:02d} through {present[-1]:02d}"
    )
    if missing_inside:
        shown = ", ".join(f"{hour:02d}" for hour in missing_inside)
        phrase += f", with no rows in hour(s) {shown}"
    return phrase


def render_coverage(report: dict) -> str:
    lines = [
        "# July 2024 temporal coverage",
        "",
        "The counts below are rows delivered in the extracted FIRMS CSVs for 1–31 July 2024. "
        "A delivered-row count of zero means the CSV is present and has no row with that acquisition date. "
        "It is not a measurement of zero fire activity. A missing source file is a separate status and has no delivered-row count.",
        "",
        "## Integrity",
        "",
        f"Ingestion manifest passed: {report['integrity']['manifest_passed']}.",
        "",
        "| Dataset | Expected rows | Delivered rows | Difference | CSV SHA-256 |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for item in report["integrity"]["archives"]:
        lines.append(
            f"| {item['sensor']} | {_count(item['expected_rows'])} | {_count(item['record_count'])} | "
            f"{item['difference']} | `{item['csv_sha256']}` |"
        )
    lines.extend(
        [
            "",
            f"Total delivered rows: {_count(report['integrity']['total_rows'])}. "
            f"Reference total: {_count(report['integrity']['expected_total'])}. "
            f"Difference: {report['integrity']['total_difference']}.",
            "",
            f"Exact duplicate rows retained: {_count(report['integrity']['exact_duplicate_rows'])}. "
            f"Extra location-time keys retained: {_count(report['integrity']['location_time_duplicate_rows'])}. "
            "Duplicate detection uses 128-bit BLAKE2b digests of the stored fields. No row was removed.",
            "",
        ]
    )
    for item in report["integrity"]["archives"]:
        if "exact_duplicate_rows" in item:
            lines.append(
                f"{item['sensor']}: exact duplicate rows {_count(item['exact_duplicate_rows'])}, "
                f"extra location-time keys {_count(item['location_time_duplicate_rows'])}."
            )
    lines.extend(
        [
            "",
            f"Empty cells: {report['integrity']['empty_cells']}. Malformed-field counts: {report['integrity']['malformed']}.",
            "",
            "Each ZIP still has the checksum recorded at ingestion, and each extracted CSV checksum matches that manifest. "
            "The 7 July sample files were hashed before and after this scan.",
            "",
            "## Daily matrix",
            "",
            "Terra and Aqua come from the MODIS CSV. NOAA-20, NOAA-21, and S-NPP come from their own CSVs. "
            "`zero_rows_delivered` is a property of the file. `source_file_missing` would mean the CSV itself is absent.",
            "",
            "| Date | Terra | Aqua | NOAA-20 | NOAA-21 | S-NPP |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for day in report["matrix"]:
        cells = []
        for satellite in ("Terra", "Aqua", "N20", "N21", "SNPP"):
            item = day["satellites"][satellite]
            if item["status"] == "source_file_missing":
                cells.append("file missing")
            elif item["status"] == "zero_rows_delivered":
                cells.append("0 rows delivered")
            else:
                cells.append(_count(item["delivered_rows"]))
        lines.append(f"| {day['date']} | " + " | ".join(cells) + " |")
    lines.extend(["", "## S-NPP windows", ""])
    lines.append(
        "The windows below were examined because earlier notes listed 10–16 July and 25–28 July. "
        "The table uses the rows in this CSV. Other archives having rows on the same date does not establish an S-NPP outage."
    )
    lines.append("")
    for window in report["snpp_windows"]:
        span = window["window"]
        lines.append(f"### {span['start']} through {span['end']}")
        lines.append("")
        lines.append(f"S-NPP dates with zero delivered rows: {', '.join(window['snpp_zero_rows_delivered']) or 'none'}.")
        lines.append(f"S-NPP dates with delivered rows: {', '.join(window['snpp_dates_with_rows']) or 'none'}.")
        lines.append("")
        lines.append("| Date | S-NPP status | S-NPP rows | NOAA-20 rows | NOAA-21 rows | Terra rows | Aqua rows |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
        for day in window["dates"]:
            lines.append(
                "| {date} | {status} | {snpp} | {n20} | {n21} | {terra} | {aqua} |".format(
                    date=day["date"],
                    status=day["snpp"]["status"],
                    snpp=_rows(day["snpp"]),
                    n20=_rows(day["other_archives"]["N20"]),
                    n21=_rows(day["other_archives"]["N21"]),
                    terra=_rows(day["other_archives"]["Terra"]),
                    aqua=_rows(day["other_archives"]["Aqua"]),
                )
            )
        lines.append("")
        lines.append(window["inference"])
        lines.append("")
    lines.extend(["## Smallest delivered days", ""])
    lines.append(
        "These are the three dates with the smallest positive delivered-row counts for each satellite. "
        "They are dates the file did cover. They are not zero-row dates and they are not identified as outages."
    )
    lines.append("")
    for satellite, days in report["smallest_positive_days"].items():
        rendered = ", ".join(f"{item['date']} ({_count(item['delivered_rows'])} rows)" for item in days)
        lines.append(f"- {satellite}: {rendered}.")
        hours = report.get("notable_hour_counts", {}).get(satellite, {})
        for item in days:
            if item["date"] in hours:
                lines.append(f"  {item['date']}: {_hour_phrase(hours[item['date']])}.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _satellite_for_sensor(sensor: str) -> str:
    return {
        "modis": "Terra",
        "viirs_snpp": "SNPP",
        "viirs_noaa20": "N20",
        "viirs_noaa21": "N21",
    }[sensor]


def _rows(cell: dict) -> str:
    if cell["delivered_rows"] is None:
        return "file missing"
    if cell["status"] == "zero_rows_delivered":
        return "0 rows delivered"
    return _count(cell["delivered_rows"])


def render_eda(report: dict) -> str:
    lines = [
        "# July 2024 monthly exploratory summary",
        "",
        "Statistics describe rows in the four FIRMS CSVs for 1–31 July 2024. "
        "They are not unique-fire counts, and sensor totals are not a ranking of detection sensitivity.",
        "",
        "## Detection counts",
        "",
        "| Satellite | Sensor archive | Delivered rows |",
        "| --- | --- | ---: |",
    ]
    for satellite, profile in report["satellites"].items():
        lines.append(f"| {satellite} | {profile['sensor']} | {_count(profile['delivered_rows'])} |")
    lines.extend(["", "## FRP", ""])
    lines.append("FRP is the stored fire radiative power. The summaries keep every parsed finite value, including extremes.")
    lines.append("")
    for satellite, profile in report["satellites"].items():
        frp = profile["frp"]
        lines.append(f"- {satellite}: {_quantile_line(frp)}. Zero-FRP rows: {_count(profile['frp_zero_rows'])}.")
        extreme = profile["extreme_frp"]
        if extreme:
            example = extreme["example_row"]
            lines.append(
                f"  Maximum stored FRP text {extreme['stored_text']} appears on {extreme['rows_with_this_stored_value']} row(s). "
                f"Example line {example['line_number']}: {example['acq_date']} {example['acq_time']} UTC, "
                f"latitude {example['latitude']}, longitude {example['longitude']}, "
                f"confidence {example['confidence']}, brightness {example['brightness']}."
            )
    lines.extend(["", "## Day and night", ""])
    lines.append("The day/night value is the archive flag.")
    lines.append("")
    for satellite, counts in report["daynight"].items():
        lines.append(f"- {satellite}: day {_count(counts.get('D', 0))}, night {_count(counts.get('N', 0))}.")
    lines.extend(["", "## Confidence", ""])
    lines.append(report["confidence_note"])
    lines.append("")
    for satellite, summary in report["confidence"].items():
        if summary["kind"] == "modis_0_100":
            counts = summary["counts"]
            median = summary["median_integer"]
            lines.append(
                f"- {satellite} (modis_0_100): median {median:.0f}, "
                f"confidence 0 on {_count(counts.get('0', 0))} rows, "
                f"confidence 100 on {_count(counts.get('100', 0))} rows. "
                "Every integer from 0 through 100 is stored in the JSON and in confidence_modis.png."
            )
        else:
            rendered = ", ".join(f"{label} {_count(count)}" for label, count in summary["counts"].items())
            lines.append(f"- {satellite} ({summary['kind']}): {rendered}.")
    lines.extend(["", "## Brightness", ""])
    for satellite, profile in report["satellites"].items():
        lines.append(f"- {satellite}: {_quantile_line(profile['brightness'])}.")
    viirs = report["brightness_367"]
    lines.extend(
        [
            "",
            "VIIRS rows whose brightness text is exactly `367`:",
            "",
        ]
    )
    for sensor, payload in viirs.items():
        flags = ", ".join(f"{flag} {_count(count)}" for flag, count in payload["by_confidence"].items()) or "none"
        lines.append(
            f"- {sensor}: {flags}. Rows above 367 K: {_count(payload['above_367'])}. "
            f"Rows in [360 K, 367 K): {_count(payload['from_360_until_367'])}."
        )
        high = report["confidence"].get(_satellite_for_sensor(sensor), {}).get("counts", {}).get("h")
        on_367 = payload["by_confidence"].get("h")
        if high is not None and on_367 == high and payload["by_confidence"].get("n", 0) == 0:
            lines.append(f"  Every stored h flag in this archive is on brightness text 367. No n flag is on that value.")
    lines.extend(
        [
            "",
            "The CSV has no Level-1 saturation flag, so a stored value of 367 K is not marked as confirmed saturation.",
            "",
            "## Weekly delivered rows",
            "",
            "Weekly totals add the rows whose acquisition dates fall in that Monday-start span. "
            "Dates with zero delivered rows are listed and are not filled in.",
            "",
        ]
    )
    for satellite, weeks in report["weekly"].items():
        parts = [f"{label} {_count(count)}" for label, count in weeks["counts"].items()]
        absent = weeks["dates_with_zero_rows"]
        lines.append(f"- {satellite}: {'; '.join(parts)}. Dates with zero delivered rows: {', '.join(absent) or 'none'}.")
    lines.extend(["", "## Geographic concentration", ""])
    lines.append(
        "Cells are 1 degree of latitude and longitude, identified by the floor of each coordinate. "
        "A dense cell is a concentration of archive rows, not one fire."
    )
    lines.append("")
    for satellite, spatial in report["spatial"].items():
        top = spatial["top_cells"][0]
        share = top["delivered_rows"] / spatial["rows_in_cells"] if spatial["rows_in_cells"] else 0
        lines.append(
            f"- {satellite}: { _count(spatial['occupied_cells']) } occupied cells. "
            f"Densest cell floor ({top['latitude_floor']}, {top['longitude_floor']}) has "
            f"{_count(top['delivered_rows'])} rows, {share:.2%} of located rows."
        )
    lines.extend(["", "## July 7 cross-check", ""])
    for satellite, item in report["july7"].items():
        lines.append(
            f"- {satellite}: monthly file delivered {_count(item['monthly_rows'])} rows on 2024-07-07; "
            f"the separate one-day sample has {_count(item['sample_rows'])} rows; difference {item['difference']}."
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def write_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _json_default(value: object) -> object:
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def write_text(payload: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
