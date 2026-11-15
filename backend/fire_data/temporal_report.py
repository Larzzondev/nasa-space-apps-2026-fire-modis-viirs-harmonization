"""Markdown, JSON, and CSV writers for the temporal-validation summary."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from fire_data.temporal import assert_output_allowed

DISPLAY = {
    "Terra": "Terra",
    "Aqua": "Aqua",
    "N20": "NOAA-20",
    "N21": "NOAA-21",
    "SNPP": "S-NPP",
    "D": "day",
    "N": "night",
    "all": "day and night",
}


def _name(value: str) -> str:
    return DISPLAY.get(value, value)


def _count(value: int) -> str:
    return f"{int(value):,}"


def _num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.{digits}f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def _rows(path: Path, header: list[str], records: list[dict]) -> None:
    assert_output_allowed(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({name: record.get(name, "") for name in header})


def _brightness_table(rows: list[dict]) -> str:
    lines = [
        "| Satellite | Date | Rows | Exact text 367 | Numeric 367 | Share | Above 367 | In [360, 367) | In [366, 367) | Highest below 367 | Confirmed saturated |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    if not rows:
        lines.append("| none |  |  |  |  |  |  |  |  |  |  |")
        return "\n".join(lines)
    for row in rows:
        highest = "n/a"
        if row["highest_below_367_text"]:
            highest = f"{row['highest_below_367_text']} ({_count(row['highest_below_367_count'])})"
        lines.append(
            "| {satellite} | {date} | {count} | {exact} | {numeric} | {share} | {above} | {tail} | {gap} | {highest} | {saturated} |".format(
                satellite=_name(row["satellite"]),
                date=row["acq_date"],
                count=_count(row["detection_count"]),
                exact=_count(row["exact_text_367"]),
                numeric=_count(row["numeric_equal_367"]),
                share=_pct(row["share_equal_367"]),
                above=_count(row["above_367"]),
                tail=_count(row["from_360_below_367"]),
                gap=_count(row["from_366_below_367"]),
                highest=highest,
                saturated=_count(row["confirmed_saturated_count"]),
            )
        )
    return "\n".join(lines)


def _frp_table(rows: list[dict]) -> str:
    lines = [
        "| Satellite | Date | Day/night | Rows | Minimum | p50 | p90 | p99 | p99.9 | Maximum text | Rows at maximum | Confidence at maximum |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {satellite} | {date} | {daynight} | {count} | {minimum} | {p50} | {p90} | {p99} | {p999} | {maximum} | {n_max} | {confidence} |".format(
                satellite=_name(row["satellite"]),
                date=row["acq_date"],
                daynight=_name(row["daynight"]),
                count=_count(row["detection_count"]),
                minimum=_num(row["minimum"]),
                p50=_num(row["p50"]),
                p90=_num(row["p90"]),
                p99=_num(row["p99"]),
                p999=_num(row["p999"]),
                maximum=row["maximum_text"] or "n/a",
                n_max=_count(row["maximum_row_count"]),
                confidence=", ".join(row["confidence_at_maximum"]) or "n/a",
            )
        )
    return "\n".join(lines)


def _cluster_table(rows: list[dict]) -> str:
    lines = [
        "| Satellite | Date | Day/night | p99.9 FRP | Extreme rows | Confidence | 1° cells | Densest cell | Cell share | Distinct minutes | Modal minute |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        if row["daynight"] == "all":
            continue
        cell = "n/a"
        if row["densest_cell_lat_floor"] is not None:
            cell_count = int(row["densest_cell_count"])
            cell_noun = "row" if cell_count == 1 else "rows"
            cell = (
                f"{row['densest_cell_lat_floor']}°, {row['densest_cell_lon_floor']}° "
                f"({_count(cell_count)} {cell_noun})"
            )
        confidence = "n/a"
        if row.get("extreme_confidence_min") is not None:
            confidence = (
                f"{row['extreme_confidence_min']}–{row['extreme_confidence_max']} "
                f"(median {_num(row['extreme_confidence_median'], 1)})"
            )
        lines.append(
            "| {satellite} | {date} | {daynight} | {threshold} | {extreme} | {confidence} | {cells} | {cell} | {share} | {times} | {modal} |".format(
                satellite=_name(row["satellite"]),
                date=row["acq_date"],
                daynight=_name(row["daynight"]),
                threshold=_num(row["extreme_threshold"]),
                extreme=_count(row["extreme_count"]),
                confidence=confidence,
                cells=_count(row["extreme_cell_count"]),
                cell=cell,
                share=_pct(row["densest_cell_share"]),
                times=_count(row["extreme_acq_time_count"]),
                modal=row["extreme_modal_acq_time"] or "n/a",
            )
        )
    return "\n".join(lines)


def _maxima_table(rows: list[dict]) -> str:
    lines = [
        "| Satellite | Date | Day/night | Line | UTC | Latitude | Longitude | FRP | Confidence | Brightness | Scan | Track |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| none |  |  |  |  |  |  |  |  |  |  |  |")
        return "\n".join(lines)
    for row in rows:
        lines.append(
            "| {satellite} | {date} | {daynight} | {line} | {time} | {lat} | {lon} | {frp} | {confidence} | {brightness} | {scan} | {track} |".format(
                satellite=_name(row["satellite"]),
                date=row["acq_date"],
                daynight=_name(row["daynight"]),
                line=row["line_number"],
                time=row["acq_time"],
                lat=row["latitude"],
                lon=row["longitude"],
                frp=row["frp"],
                confidence=row["confidence"],
                brightness=row["brightness"],
                scan=row["scan"],
                track=row["track"],
            )
        )
    return "\n".join(lines)


def _proximity_table(rows: list[dict]) -> str:
    lines = [
        "| Satellite A | Satellite B | Radius (m) | Max Δt (min) | Proximity pairs | A with a neighbor | B with a neighbor | Same fire |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {a} | {b} | {radius} | {window} | {pairs} | {count_a} | {count_b} | {same_fire} |".format(
                a=_name(row["satellite_a"]),
                b=_name(row["satellite_b"]),
                radius=_num(row["radius_m"], 0),
                window=row["max_delta_minutes"],
                pairs=_count(row["proximity_pairs"]),
                count_a=_count(row["detections_a_with_neighbor"]),
                count_b=_count(row["detections_b_with_neighbor"]),
                same_fire=row["same_fire"],
            )
        )
    return "\n".join(lines)


def _variable_table(rows: list[dict], disposition: str) -> str:
    selected = [row for row in rows if row["disposition"] == disposition]
    lines = ["| Variable | Support | Rationale |", "| --- | --- | --- |"]
    for row in selected:
        lines.append(f"| `{row['variable']}` | {row['support']} | {row['rationale']} |")
    return "\n".join(lines)


def render_report(summary: dict) -> str:
    scope = summary["scope"]
    dates = ", ".join(scope["dates"]) if scope["dates"] else "none"
    date_counts = ", ".join(f"{day} ({_count(count)} rows)" for day, count in scope["date_counts"].items()) or "none"
    status = scope["multi_date_validation"]
    archive_lines = []
    for archive in summary["archives"]:
        version_text = ", ".join(f"{version} ({_count(count)})" for version, count in archive["versions"].items())
        satellite_text = ", ".join(f"{_name(name)} {_count(count)}" for name, count in archive["satellites"].items())
        time_text = ", ".join(
            f"{_name(name)} { _count(count)} distinct HHMM" for name, count in archive["distinct_acq_time"].items()
        )
        archive_lines.append(
            f"- `{archive['relative_path']}`: {_count(archive['row_count'])} rows; "
            f"dates {', '.join(archive['dates']) or 'none'}; versions {version_text}; "
            f"satellites {satellite_text}; acquisition minutes {time_text}. "
            f"Processing level: {archive['processing_level']}. {archive['reason']}"
        )
    document_lines = [
        f"- {statement['text']} Source: {statement['url']} (retrieved {statement['retrieved']})."
        for statement in summary["document_statements"]
    ]
    missing_lines = [f"- {item}" for item in summary["missing"]]
    brightness_dates = sorted({row["acq_date"] for row in summary["brightness"]})
    repeat_sentence = (
        "The VIIRS table has one date, so it is the available measurement and not a repeat across dates."
        if len(brightness_dates) < 2
        else "The VIIRS table repeats the same counts on each acquisition date present in the files that were read."
    )
    frp_dates = sorted({row["acq_date"] for row in summary["modis_frp"]})
    frp_sentence = (
        "Terra and Aqua FRP quantiles are reported for the one date in the MODIS archive. "
        "A comparison of those quantiles between dates was not computed."
        if len(frp_dates) < 2
        else "Terra and Aqua FRP quantiles are reported separately for each date present."
    )
    parts = [
        "# Temporal validation",
        "",
        (
            f"Multi-date temporal validation is {status}. "
            f"Acquisition dates present: {dates}. Row totals by date: {date_counts}. "
            "The measurements below use only those dates. No additional dates were created."
        ),
        "",
        "## What is missing",
        "",
        "\n".join(missing_lines),
        "",
        "## Provenance",
        "",
        (
            "Processing level is unresolved for every local archive. "
            "A filename that begins with `fire_archive` or `fire_nrt`, and a version value of `2` or `61.03`, "
            "are recorded below and are not treated as proof of standard or near-real-time processing."
        ),
        "",
        "### Files",
        "",
        "\n".join(archive_lines),
        "",
        "### Documents retrieved for this pass",
        "",
        "\n".join(document_lines),
        "",
        (
            "The download readme and the API catalog do not agree about NOAA-20 and NOAA-21 standard products: "
            "the readme says standard-quality data were not yet available, while the API page lists "
            "`VIIRS_NOAA20_SP` and `VIIRS_NOAA21_SP`. Neither page is a field in these CSVs. "
            "The approximately three-month replacement lag is also not used to assign a level, "
            "including when the acquisition date is earlier than this pass."
        ),
        "",
        "## VIIRS 367 K by date",
        "",
        (
            repeat_sentence
            + " Confirmed saturated counts stay at zero because the archives have no Level-1 saturation flag. "
            "A high-confidence flag is not used as that flag."
        ),
        "",
        _brightness_table(summary["brightness"]),
        "",
        "## MODIS FRP by date and day/night",
        "",
        frp_sentence,
        " Quantiles use the linear empirical method on the parsed FRP values. "
        "The maximum is the original CSV text with the greatest exact decimal value. "
        "An extreme row is one at or above the within-group 0.999 quantile. "
        "Cell coordinates are the floor of latitude and longitude, so each cell is the 1° square whose southwest corner is that pair. "
        "A cell count is a count of detection rows.",
        "",
        _frp_table(summary["modis_frp"]),
        "",
        "### Upper tail, geography, and time",
        "",
        _cluster_table(summary["modis_frp"]),
        "",
        "### Rows holding the daytime or nighttime maximum",
        "",
        _maxima_table(summary["modis_maxima"]),
        "",
        "## Cross-satellite proximity",
        "",
        (
            "Distance is the ECEF chord on a sphere of radius "
            f"{scope['earth_radius_m']} m, the same sphere used for the exploratory overlap summary. "
            "Time separation is the absolute difference of UTC minutes, with the date included so that "
            "the same clock time on two dates is not treated as the same minute. "
            f"Radii: {', '.join(_num(radius, 0) for radius in scope['radii_m'])} m. "
            f"Windows: {', '.join(str(window) for window in scope['windows_min'])} minutes. "
            "A proximity pair is not a confirmed same-fire match. "
            "One detection can appear in more than one pair, so the pair column is not a count of fires "
            "and is not summed across satellite pairs."
        ),
        "",
        _proximity_table(summary["proximity"]),
        "",
        "## Variables suitable for a later calibration",
        "",
        "These variables share a stored unit or a stored role that a later calibration could stratify. No coefficient is calculated.",
        "",
        _variable_table(summary["variables"], "calibration_candidate"),
        "",
        "## Variables requiring special treatment",
        "",
        _variable_table(summary["variables"], "special_treatment"),
        "",
        "## Limitations",
        "",
        "- The result is limited to the acquisition dates actually stored in the local archives.",
        "- Provenance stops at unresolved for every file. Collection version and the archive filename are not a processing-level measurement.",
        "- VIIRS rows at 367 K are counted. They are not labeled confirmed saturated.",
        "- Day and night follow the stored flag.",
        "- The 0.999 FRP quantile is internal to each satellite, date, and day/night group in this extract.",
        "- Proximity does not adjust for scan-dependent pixel growth or geolocation error.",
        "- No harmonization coefficient is calculated.",
        "",
        "## Unresolved questions",
        "",
        "- Which processing stream produced each local file, in particular the NOAA-20 and NOAA-21 archives named `fire_archive_J1V-C2` and `fire_archive_J2V-C2`.",
        "- Whether the current API standard-processing codes describe products that can be joined to these download files.",
        "- Whether any individual VIIRS detection at 367 K is the Level-1 saturation case, the fold-over case, or the aggregation case.",
        "- Whether `bright_t31` is MODIS channel 31 in the MODIS file and VIIRS I-5 in the VIIRS files.",
        "- Whether any proximity pair is the same physical fire.",
        "- How often the 367 K value, the MODIS FRP maxima, and the proximity rates recur on other dates.",
        "",
        "## Reproduction",
        "",
        "From the backend directory:",
        "",
        "```bash",
        ".venv\\Scripts\\python -m fire_data.temporal",
        "```",
        "",
        "The command writes `reports/temporal_validation.md`, `reports/temporal_summary.json`, and the CSV files in `reports/temporal/`. "
        "It leaves the exploratory report, the anomaly report, and `data/raw/` unchanged.",
        "",
    ]
    return "\n".join(parts)


def write_temporal(summary: dict, output_dir: Path) -> tuple[Path, Path]:
    assert_output_allowed(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table_dir = output_dir / "temporal"
    report_path = output_dir / "temporal_validation.md"
    json_path = output_dir / "temporal_summary.json"
    assert_output_allowed(report_path)
    assert_output_allowed(json_path)
    assert_output_allowed(table_dir)
    report_path.write_text(render_report(summary), encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _rows(
        table_dir / "archive_inventory.csv",
        [
            "source_id",
            "relative_path",
            "filename",
            "row_count",
            "invalid_rows",
            "processing_level",
            "determined",
            "processing_level_column_present",
            "dates",
            "versions",
            "satellites",
        ],
        [
            {
                **archive,
                "dates": json.dumps(archive["dates"]),
                "versions": json.dumps(archive["versions"]),
                "satellites": json.dumps(archive["satellites"]),
            }
            for archive in summary["archives"]
        ],
    )
    _rows(
        table_dir / "viirs_brightness_by_date.csv",
        [
            "satellite",
            "acq_date",
            "detection_count",
            "exact_text_367",
            "numeric_equal_367",
            "share_equal_367",
            "above_367",
            "from_360_below_367",
            "from_366_below_367",
            "highest_below_367_text",
            "highest_below_367_count",
            "confirmed_saturated_count",
            "saturation_flag_present",
        ],
        summary["brightness"],
    )
    _rows(
        table_dir / "modis_frp_by_date.csv",
        [
            "satellite",
            "acq_date",
            "daynight",
            "detection_count",
            "minimum",
            "p50",
            "p90",
            "p99",
            "p999",
            "maximum_text",
            "maximum_row_count",
            "confidence_at_maximum",
            "extreme_threshold",
            "extreme_count",
            "extreme_confidence_min",
            "extreme_confidence_median",
            "extreme_confidence_max",
            "extreme_cell_count",
            "densest_cell_count",
            "densest_cell_share",
            "densest_cell_lat_floor",
            "densest_cell_lon_floor",
            "extreme_acq_time_count",
            "extreme_modal_acq_time",
            "extreme_modal_acq_time_count",
        ],
        [
            {**row, "confidence_at_maximum": " ".join(row["confidence_at_maximum"])}
            for row in summary["modis_frp"]
        ],
    )
    _rows(
        table_dir / "modis_frp_maxima.csv",
        [
            "satellite",
            "acq_date",
            "daynight",
            "line_number",
            "acq_time",
            "latitude",
            "longitude",
            "frp",
            "confidence",
            "brightness",
            "scan",
            "track",
        ],
        summary["modis_maxima"],
    )
    _rows(
        table_dir / "proximity_matches.csv",
        [
            "satellite_a",
            "satellite_b",
            "radius_m",
            "max_delta_minutes",
            "proximity_pairs",
            "detections_a_with_neighbor",
            "detections_b_with_neighbor",
            "same_fire",
        ],
        summary["proximity"],
    )
    _rows(
        table_dir / "variables.csv",
        ["variable", "disposition", "support", "rationale"],
        summary["variables"],
    )
    return report_path, json_path
