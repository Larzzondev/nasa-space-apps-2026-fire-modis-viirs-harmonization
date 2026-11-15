"""Render the anomaly investigation without changing the exploratory report."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import numpy as np

from fire_data.investigate import CEILING, DETAIL_RADIUS_M

DISPLAY = {
    "viirs_noaa20": "NOAA-20",
    "viirs_noaa21": "NOAA-21",
    "viirs_snpp": "S-NPP",
    "modis": "MODIS",
    "Terra": "Terra",
    "Aqua": "Aqua",
    "N20": "NOAA-20",
    "N21": "NOAA-21",
    "SNPP": "S-NPP",
}


def _convert(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Cannot write {type(value).__name__} to JSON")


def _fmt(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.{digits}f}"


def _count(value: int) -> str:
    return f"{value:,}"


def _rows(count: int) -> str:
    number = int(count)
    noun = "row" if number == 1 else "rows"
    return f"{_count(number)} {noun}"


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def _name(source_id: str) -> str:
    return DISPLAY.get(source_id, source_id)


def _adjacent(record: dict) -> dict | None:
    below = [item for item in record["frequency_from_366_k"] if Decimal(item["value"]) < CEILING]
    if not below:
        return None
    return max(below, key=lambda item: (Decimal(item["value"]), item["count"]))


def classify(summary: dict) -> dict:
    """Split the investigation into facts, hypotheses, and unresolved questions."""

    facts = [
        "All counts in this investigation are one-day global observations for 2024-07-07.",
        "A count is a count of archived detection rows. Unique fires are not identified.",
        "No harmonization factor is calculated.",
        (
            "The FIRMS download readme maps the file codes J1V-C2, J2V-C2, and SV-C2 to the "
            "VIIRS 375 m products for NOAA-20, NOAA-21, and S-NPP. "
            "It maps fire_archive_SV-C2 to the standard VNP14IMGTML product and fire_archive_M-C61 to MCD14ML."
        ),
        (
            "The FIRMS attribute table defines the VIIRS field Brightness as the I-4 channel brightness "
            "temperature in kelvin. These archives store that field under the column name brightness. "
            "They do not contain a column named bright_ti4."
        ),
        (
            "The Collection 2 VIIRS 375 m Active Fire User's Guide, version 1.2, says that in the typical "
            "I4 saturation case the pixel is assigned the nominal saturation temperature of 367 K. "
            "The same answer describes two other saturation situations: a digital-count fold-over that "
            "appears as an abnormally low temperature, and mixed saturated and unsaturated samples from "
            "onboard aggregation."
        ),
        (
            "The FIRMS attribute table says VIIRS high-confidence pixels are associated with day or nighttime "
            "saturated pixels. Low, nominal, and high remain the stored flags l, n, and h."
        ),
    ]
    for record in summary["brightness"]["satellites"]:
        name = _name(record["source_id"])
        places = ", ".join(f"{places} decimal places: {_count(count)}" for places, count in record["decimal_place_counts"].items())
        texts = ", ".join(f"{text} ({_count(count)})" for text, count in record["ceiling_texts"].items()) or "none"
        adjacent = _adjacent(record)
        if adjacent is None:
            adjacent_text = "no stored value falls in [366, 367)"
        else:
            adjacent_text = f"the next stored text is {adjacent['text']} with {_count(adjacent['count'])} rows"
        below = record.get("highest_below_367_text")
        if below:
            adjacent_text += (
                f"; the highest brightness text below 367 is {below} "
                f"({_rows(record.get('highest_below_367_count', 0))})"
            )
        integer_texts = int(record["decimal_place_counts"].get("0", 0))
        exact_integer_ceiling = int(record["ceiling_texts"].get("367", 0))
        facts.append(
            f"{name}: { _count(record['detection_count']) } detections; maximum stored brightness text "
            f"{record['maximum_text']}; {_count(record['numeric_equal_367'])} rows "
            f"({_pct(record['share_equal_367'])}) are numerically equal to 367; "
            f"{_count(record['above_367'])} rows are numerically above 367; {adjacent_text}. "
            f"Original 367 texts: {texts}. Decimal-place counts: {places}. "
            f"Integer text 367 accounts for {_count(exact_integer_ceiling)} of {_count(integer_texts)} "
            "brightness values stored with no decimal point."
        )
        confidence = ", ".join(f"{flag} {_count(count)}" for flag, count in record["confidence_at_367"].items()) or "none"
        facts.append(
            f"{name} confidence among rows numerically equal to 367: {confidence}. "
            f"High-confidence flag h below 367: {_count(record['high_confidence_below_367'])}."
        )
    for target in summary["extreme_frp"]["targets"]:
        row = target["row"]
        facts.append(
            "Aqua source row "
            f"line {target['line_number']} in {target['archive']}: "
            f"latitude {row['latitude']}, longitude {row['longitude']}, "
            f"brightness {row['brightness']}, scan {row['scan']}, track {row['track']}, "
            f"acq_date {row['acq_date']}, acq_time {row['acq_time']} UTC, "
            f"satellite {row['satellite']}, instrument {row['instrument']}, "
            f"confidence {row['confidence']}, version {row['version']}, "
            f"bright_t31 {row['bright_t31']}, frp {row['frp']}, "
            f"daynight {row['daynight']}, type {row['type']}."
        )
    pair_distance = summary["extreme_frp"]["pair_distance_m"]
    pair_delta = summary["extreme_frp"]["pair_delta_minutes"]
    if pair_distance is not None and pair_delta is not None:
        facts.append(
            f"The two target Aqua rows are {_fmt(pair_distance)} m apart on a great circle and "
            f"{pair_delta} minutes apart in UTC acq_time."
        )
    facts.append(summary["extreme_frp"]["distance_method"])
    hypotheses = [
        (
            "The repeated stored value 367 is the nominal I4 saturation temperature described by the "
            "Collection 2 375 m user's guide, recorded in the FIRMS brightness column. "
            "This investigation can test the stored number and the published definition. "
            "It cannot inspect the Level-1 saturation flag for an individual CSV row."
        ),
        (
            "A brightness value well below 367 can include the guide's fold-over or aggregation cases. "
            "Those cases are not identified by the number 367, and this pass does not classify them."
        ),
        (
            "The two Aqua FRP values are large stored retrievals for their pixels. "
            "Their size, identical acquisition minute, and separation relative to the stored scan length "
            "describe the observation geometry. They do not by themselves establish a single physical fire."
        ),
    ]
    unresolved = [
        "The CSV has no I4 saturation quality bit, so row-level saturation remains unverified even where brightness is exactly 367.",
        (
            "The VIIRS files name the second thermal column bright_t31. The FIRMS VIIRS attribute table "
            "names the I-5 brightness temperature Bright_ti5, also called Brightness_2 in web services. "
            "The column correspondence is not written inside these files."
        ),
        (
            "The FIRMS download readme says standard-quality data were not yet available from FIRMS for "
            "NOAA-20 and NOAA-21, while these files are named fire_archive_J1V-C2 and fire_archive_J2V-C2 "
            "and their version field is 2 with no NRT suffix. The processing stream is not fully identified "
            "by the readme entry that was current at retrieval."
        ),
        (
            "Nearby detections from Terra, NOAA-20, NOAA-21, and S-NPP are spatial and temporal neighbors "
            "under the stated search windows. They are not classified as the same fire."
        ),
        "This date supplies no historical baseline for how often 367 K or these FRP values occur.",
    ]
    return {"facts": facts, "hypotheses": hypotheses, "unresolved": unresolved}


def _frequency_table(record: dict) -> str:
    lines = [
        "| Stored brightness text | Parsed value (K) | Rows |",
        "| --- | ---: | ---: |",
    ]
    for item in record["frequency_from_366_k"]:
        lines.append(f"| {item['text']} | {item['value']} | {_count(item['count'])} |")
    if len(lines) == 2:
        lines.append("| none |  | 0 |")
    return "\n".join(lines)


def _confidence_table(summary: dict) -> str:
    lines = [
        "| Satellite | Rows equal to 367 | Share | l | n | h | h below 367 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for record in summary["brightness"]["satellites"]:
        flags = record["confidence_at_367"]
        lines.append(
            "| {name} | {rows} | {share} | {low} | {nominal} | {high} | {high_below} |".format(
                name=_name(record["source_id"]),
                rows=_count(record["numeric_equal_367"]),
                share=_pct(record["share_equal_367"]),
                low=_count(flags.get("l", 0)),
                nominal=_count(flags.get("n", 0)),
                high=_count(flags.get("h", 0)),
                high_below=_count(record["high_confidence_below_367"]),
            )
        )
    return "\n".join(lines)


def _target_table(targets: list[dict]) -> str:
    header = (
        "| Line | Latitude | Longitude | UTC | FRP | Confidence | Brightness | bright_t31 | "
        "Scan | Track | Day/night | Type | Version |"
    )
    lines = [header, "| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |"]
    for target in targets:
        row = target["row"]
        lines.append(
            "| {line} | {lat} | {lon} | {time} | {frp} | {confidence} | {brightness} | {t31} | "
            "{scan} | {track} | {daynight} | {kind} | {version} |".format(
                line=target["line_number"],
                lat=row["latitude"],
                lon=row["longitude"],
                time=row["acq_time"],
                frp=row["frp"],
                confidence=row["confidence"],
                brightness=row["brightness"],
                t31=row["bright_t31"],
                scan=row["scan"],
                track=row["track"],
                daynight=row["daynight"],
                kind=row["type"],
                version=row["version"],
            )
        )
    return "\n".join(lines)


def _count_table(block: dict) -> str:
    lines = [
        "| Radius | Time window | Neighbors | By satellite |",
        "| ---: | --- | ---: | --- |",
    ]
    for item in block["counts"]:
        window = "any time on this date" if item["max_delta_minutes"] is None else f"≤ {item['max_delta_minutes']} min"
        satellites = ", ".join(f"{name} {_count(count)}" for name, count in item["by_satellite"].items()) or "none"
        lines.append(f"| {_fmt(item['radius_m'], 0)} m | {window} | {_count(item['count'])} | {satellites} |")
    return "\n".join(lines)


def _neighbor_rows(rows: list[dict]) -> list[str]:
    lines = [
        "| Satellite | Line | Distance (m) | Δt (min) | UTC | Latitude | Longitude | FRP | Confidence | Scan | Track | Brightness | Day/night |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    if not rows:
        lines.append("| none |  |  |  |  |  |  |  |  |  |  |  |  |")
        return lines
    for item in rows:
        row = item["row"]
        lines.append(
            "| {satellite} | {line} | {distance} | {delta} | {time} | {lat} | {lon} | {frp} | {confidence} | "
            "{scan} | {track} | {brightness} | {daynight} |".format(
                satellite=_name(item["satellite"]),
                line=item["line_number"],
                distance=_fmt(item["distance_m"]),
                delta=item["delta_minutes"],
                time=row["acq_time"],
                lat=row["latitude"],
                lon=row["longitude"],
                frp=row["frp"],
                confidence=row["confidence"],
                scan=row["scan"],
                track=row["track"],
                brightness=row["brightness"],
                daynight=row["daynight"],
            )
        )
    return lines


def _detail_table(nearby: list[dict], target_line: int) -> str:
    rows = [
        item
        for item in nearby
        if item["target_line_number"] == target_line and item["distance_m"] <= DETAIL_RADIUS_M
    ]
    same_minute = [item for item in rows if item["same_utc_minute"]]
    nearest = rows[:12]
    parts = [
        "Same UTC minute and within 5,000 m:",
        "",
        "\n".join(_neighbor_rows(same_minute)),
        "",
        "Nearest 12 rows within 5,000 m at any time on this date. A short distance with a large time gap is still only a spatial neighbor:",
        "",
        "\n".join(_neighbor_rows(nearest)),
    ]
    if len(rows) > len(nearest):
        parts.append(
            f"\nThe JSON file contains all {_count(len(rows))} rows within 5,000 m and every row within 10,000 m."
        )
    return "\n".join(parts)


def render_report(summary: dict) -> str:
    classified = summary.get("classification") or classify(summary)
    brightness_sections = []
    for record in summary["brightness"]["satellites"]:
        t31 = record["bright_t31_at_367"]
        frp = record["frp_at_367"]
        daynight = ", ".join(f"{flag} {_count(count)}" for flag, count in record["daynight_at_367"].items()) or "none"
        gap = ""
        if record.get("highest_below_367_text"):
            gap = (
                f" Highest stored brightness below 367: {record['highest_below_367_text']} "
                f"({_rows(record.get('highest_below_367_count', 0))})."
            )
        frp_note = ""
        if record.get("maximum_frp_text"):
            frp_note = (
                f" The largest FRP in the archive is {_fmt(float(record['maximum_frp_text']), 2)} MW "
                f"and its brightness text is {record.get('maximum_frp_brightness_text')}."
            )
        brightness_sections.append(
            "\n".join(
                [
                    f"### {_name(record['source_id'])}",
                    "",
                    (
                        f"Rows numerically equal to 367: {_count(record['numeric_equal_367'])} "
                        f"({_pct(record['share_equal_367'])}). "
                        f"Rows above 367: {_count(record['above_367'])}. "
                        f"Rows in [366, 367): {_count(record['from_366_below_367'])}."
                        f"{gap}"
                    ),
                    "",
                    f"Day/night among the 367 K rows: {daynight}.",
                    "",
                    (
                        f"Where brightness is numerically 367, stored bright_t31 has minimum {_fmt(t31['minimum'], 2)}, "
                        f"median {_fmt(t31['median'], 2)}, and maximum {_fmt(t31['maximum'], 2)}. "
                        f"Stored FRP has minimum {_fmt(frp['minimum'], 2)}, median {_fmt(frp['median'], 2)}, "
                        f"and maximum {_fmt(frp['maximum'], 2)}.{frp_note}"
                    ),
                    "",
                    "Original CSV brightness text from 366 K through 367 K:",
                    "",
                    _frequency_table(record),
                ]
            )
        )
    extreme = summary["extreme_frp"]
    neighbor_sections = []
    for block in extreme["nearby_counts"]:
        neighbor_sections.append(
            "\n".join(
                [
                    f"### Neighbors of Aqua line {block['target_line_number']} (FRP {block['target_frp']})",
                    "",
                    "A neighbor is another archived detection inside the search radius. "
                    "The same acquisition minute is temporal coincidence to the stored minute, not a fire identity.",
                    "",
                    _count_table(block),
                    "",
                    _detail_table(extreme["nearby"], block["target_line_number"]),
                ]
            )
        )
    fact_lines = "\n".join(f"- {item}" for item in classified["facts"])
    hypothesis_lines = "\n".join(f"- {item}" for item in classified["hypotheses"])
    unresolved_lines = "\n".join(f"- {item}" for item in classified["unresolved"])
    parts = [
        "# Investigation of two anomalies on 2024-07-07",
        "",
        "**Scope:** one-day global observations. This note is separate from `eda_report.md` and does not replace it.",
        "",
        (
            "Two patterns from the exploratory summary are examined here: VIIRS brightness stored at exactly 367 K, "
            "and two Aqua FRP rows stored as 7956.3 and 7328.1. "
            "The raw CSV files are read and are not rewritten."
        ),
        "",
        "## How the statements are separated",
        "",
        "Verified facts are measurements from these files or statements quoted from the cited product documents. "
        "Hypotheses are interpretations that the files and documents make plausible and do not prove row by row. "
        "Unresolved questions are left open on purpose.",
        "",
        "## Documents consulted",
        "",
        (
            "FIRMS download readme, file-code definitions for M-C61, J1V-C2, J2V-C2, and SV-C2: "
            "https://firms.modaps.eosdis.nasa.gov/download/Readme.txt"
        ),
        "",
        (
            "FIRMS active-fire attributes for MODIS and VIIRS: "
            "https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs"
        ),
        "",
        (
            "Schroeder, Giglio, and Hall, Collection 2 VIIRS 375 m Active Fire Product User's Guide, "
            "version 1.2, June 2025, FAQ on I4 saturation: "
            "https://www.earthdata.nasa.gov/s3fs-public/2025-06/VIIRS_C2_AF-375m_User_Guide_1.2.pdf"
        ),
        "",
        "## VIIRS brightness",
        "",
        "The frequency tables count original brightness strings. Numerically equal texts such as `367` and `367.0` stay distinct in the text column and are combined only in the numeric total.",
        "",
        _confidence_table(summary),
        "",
        "\n\n".join(brightness_sections),
        "",
        (
            "The empty interval from the mid-350s to 367 K is a property of the stored numbers. "
            "A filled tail rounded onto a 0.01 K grid would leave occupied bins immediately below 367; those bins are empty. "
            "Values above 367 are also absent. Decimal-place counts describe storage precision separately: "
            "most brightness texts have two decimal places, and a two-decimal text does not by itself produce a spike at one value. "
            "The cross-tab shows that every high-confidence flag in these files sits on 367, while some 367 rows carry the low flag. "
            "The user's guide statement is quoted under verified facts. Whether each 367 row is the guide's typical saturation assignment is a hypothesis, because these CSVs do not carry an I4 saturation bit."
        ),
        "",
        "## Extreme Aqua FRP",
        "",
        "The rows below are the original CSV fields for the FRP texts 7956.3 and 7328.1. Confidence remains the stored MODIS integer.",
        "",
        _target_table(extreme["targets"]),
        "",
        (
            f"Separation between these two stored rows: {_fmt(extreme['pair_distance_m'])} m and "
            f"{extreme['pair_delta_minutes']} minutes."
            if extreme["pair_distance_m"] is not None
            else "Fewer than two target rows were available for a pair separation."
        ),
        "",
        extreme["distance_method"],
        "",
        "\n\n".join(neighbor_sections),
        "",
        (
            "The neighbor tables are the spatial and temporal evidence assembled for this pass. "
            "Nearby detections are not classified as the same fire."
        ),
        "",
        "## Verified facts",
        "",
        fact_lines,
        "",
        "## Hypotheses",
        "",
        hypothesis_lines,
        "",
        "## Unresolved questions",
        "",
        unresolved_lines,
        "",
        "## Reproduction",
        "",
        "From the backend directory:",
        "",
        "```bash",
        ".venv\\Scripts\\python -m fire_data.investigate",
        "```",
        "",
        "The command writes `reports/anomaly_investigation.md` and `reports/anomaly_summary.json`. It leaves `reports/eda_report.md`, `reports/eda_summary.json`, `reports/figures/`, and `data/raw/` unchanged.",
        "",
    ]
    return "\n".join(parts)


def write_investigation(summary: dict, json_path: Path, markdown_path: Path) -> None:
    payload = dict(summary)
    payload["classification"] = classify(summary)
    json_path.write_text(json.dumps(payload, indent=2, default=_convert) + "\n", encoding="utf-8")
    markdown_path.write_text(render_report(payload), encoding="utf-8")
