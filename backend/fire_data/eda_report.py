"""Markdown and JSON rendering for the one-day exploratory summary."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from fire_data.eda_summary import DISPLAY_NAME, SATELLITE_ORDER


def _convert(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Cannot write {type(value).__name__} to JSON")


def write_summary(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, default=_convert) + "\n", encoding="utf-8")


def _split_rule(first: str, groups: int) -> str:
    cells = [first] + ["---:"] * (groups * 2)
    return "| " + " | ".join(cells) + " |"


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    text = f"{value:.4f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _count(value: int) -> str:
    return f"{value:,}"


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _hours(hours: list[int]) -> str:
    return ", ".join(f"{hour:02d} UTC" for hour in hours)


def _distribution_groups(summary: dict) -> list[tuple[str, dict]]:
    groups: list[tuple[str, dict]] = []
    satellites = summary["satellites"]
    for name in ("Terra", "Aqua"):
        if name in satellites:
            groups.append((name, satellites[name]))
    if "modis" in summary["sources"]:
        groups.append(("MODIS archive (Terra + Aqua)", summary["sources"]["modis"]))
    for name in SATELLITE_ORDER:
        if name in {"Terra", "Aqua"}:
            continue
        block = satellites.get(name)
        if block is not None and block.get("same_population_as_source"):
            groups.append((DISPLAY_NAME[name], block))
    return groups


def _numeric_table(groups: list[tuple[str, dict]], column: str) -> str:
    lines = [
        "| Group | Count | Mean | Median | Std | P95 | P99 | Maximum | Zero count |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, group in groups:
        stats = group[column]
        lines.append(
            "| {label} | {count} | {mean} | {median} | {std} | {p95} | {p99} | {maximum} | {zeros} |".format(
                label=label,
                count=_count(stats["count"]),
                mean=_fmt(stats["mean"]),
                median=_fmt(stats["median"]),
                std=_fmt(stats["std"]),
                p95=_fmt(stats["quantiles"]["0.950"]),
                p99=_fmt(stats["quantiles"]["0.990"]),
                maximum=_fmt(stats["maximum"]),
                zeros=_count(stats["zero_count"]),
            )
        )
    return "\n".join(lines)


def _figure(summary: dict, name: str, caption: str) -> str:
    if name not in summary.get("figures", []):
        return ""
    return f"![{caption}](figures/{name})\n\n*{caption}*\n"


def _population_table(summary: dict) -> str:
    lines = [
        "| Group | Archive | Detections | Distinct UTC timestamps |",
        "| --- | --- | ---: | ---: |",
    ]
    for source_id, source in summary["sources"].items():
        lines.append(
            "| {name} archive | `{archive}` | {count} | {times} |".format(
                name=DISPLAY_NAME.get(source_id, source_id),
                archive=source["archive"],
                count=_count(source["detection_count"]),
                times=_count(source["acquisition_hour_utc"]["distinct_timestamps"]),
            )
        )
        for satellite, block in source["satellites"].items():
            if block["same_population_as_source"]:
                continue
            lines.append(
                "| {name} | `{archive}` | {count} | {times} |".format(
                    name=satellite,
                    archive=source["archive"],
                    count=_count(block["detection_count"]),
                    times=_count(block["acquisition_hour_utc"]["distinct_timestamps"]),
                )
            )
    return "\n".join(lines)


def _confidence_sections(summary: dict) -> str:
    satellites = summary["satellites"]
    modis_names = [name for name in ("Terra", "Aqua") if name in satellites]
    observed: set[str] = set()
    for name in modis_names:
        observed.update(satellites[name]["confidence"]["counts"])
    modis_rows = [
        "| Confidence | " + " | ".join(f"{name} count | {name} share" for name in modis_names) + " |",
        _split_rule("---:", len(modis_names)),
    ]
    for label in sorted(observed, key=int):
        cells = [label]
        for name in modis_names:
            counts = satellites[name]["confidence"]["counts"]
            total = satellites[name]["detection_count"]
            value = counts.get(label, 0)
            cells.extend((_count(value), _pct(value / total)))
        modis_rows.append("| " + " | ".join(cells) + " |")
    medians = ", ".join(
        f"{name} median integer {_fmt(satellites[name]['confidence']['median_integer'])}"
        for name in modis_names
    )
    viirs_names = [name for name in ("N20", "N21", "SNPP") if name in satellites]
    flags = ["l", "n", "h"]
    for name in viirs_names:
        for label in satellites[name]["confidence"]["counts"]:
            if label not in flags:
                flags.append(label)
    viirs_header = "| Flag | " + " | ".join(
        f"{DISPLAY_NAME[name]} count | {DISPLAY_NAME[name]} share" for name in viirs_names
    ) + " |"
    viirs_rule = _split_rule("---", len(viirs_names))
    viirs_rows = [viirs_header, viirs_rule]
    for flag in flags:
        cells = [flag]
        for name in viirs_names:
            counts = satellites[name]["confidence"]["counts"]
            total = satellites[name]["detection_count"]
            value = counts.get(flag, 0)
            cells.extend((_count(value), _pct(value / total if total else 0.0)))
        viirs_rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(
        [
            "## Confidence",
            "",
            "MODIS confidence is the stored integer from 0 through 100. "
            "VIIRS confidence is the stored flag `l`, `n`, or `h`. "
            "FIRMS documents those flags as low, nominal, and high. "
            "Those words name the flags. Confidence scales are not equivalent, and no value was converted from one scale to the other.",
            "",
            "### MODIS Terra and Aqua",
            "",
            medians + ". The median is the median of the stored integers on the MODIS scale.",
            "",
            "\n".join(modis_rows),
            "",
            _figure(
                summary,
                "confidence_modis.png",
                "MODIS integer confidence for Terra and Aqua on this date. VIIRS flags are omitted from this axis.",
            ),
            "### VIIRS flags",
            "",
            "\n".join(viirs_rows),
            "",
            _figure(
                summary,
                "confidence_viirs.png",
                "VIIRS confidence flags by satellite. The bars are shares of archived detections.",
            ),
        ]
    )


def _hour_table(summary: dict) -> str:
    names = [name for name in SATELLITE_ORDER if name in summary["satellites"]]
    header = "| UTC hour | " + " | ".join(DISPLAY_NAME[name] for name in names) + " |"
    rule = "| --- | " + " | ".join("---:" for _name in names) + " |"
    lines = [header, rule]
    for hour in range(24):
        cells = [f"{hour:02d}"]
        for name in names:
            cells.append(_count(summary["satellites"][name]["acquisition_hour_utc"]["counts"][hour]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _daynight_table(groups: list[tuple[str, dict]]) -> str:
    lines = [
        "| Group | Day (D) | Day share | Night (N) | Night share |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, group in groups:
        counts = group["daynight"]["counts"]
        total = group["detection_count"]
        day = counts.get("D", 0)
        night = counts.get("N", 0)
        lines.append(
            f"| {label} | {_count(day)} | {_pct(day / total)} | {_count(night)} | {_pct(night / total)} |"
        )
    return "\n".join(lines)


def _spatial_section(summary: dict) -> str:
    density = summary["spatial_density"]["by_source"]
    source_ids = list(density)
    header = "| Latitude band | " + " | ".join(DISPLAY_NAME.get(source_id, source_id) for source_id in source_ids) + " |"
    rule = "| --- | " + " | ".join("---:" for _source in source_ids) + " |"
    lines = [header, rule]
    bands = density[source_ids[0]]["thirty_degree"]["latitude_band_counts"]
    for index, band in enumerate(bands):
        cells = [f"{band['south']:.0f} to {band['north']:.0f}"]
        for source_id in source_ids:
            cells.append(_count(density[source_id]["thirty_degree"]["latitude_band_counts"][index]["detections"]))
        lines.append("| " + " | ".join(cells) + " |")
    details = ["| Archive | Occupied 1° cells | Max 1° count | Cell southwest corner | Max detections per 1,000 km² |",
               "| --- | ---: | ---: | --- | ---: |"]
    for source_id, block in density.items():
        one = block["one_degree"]
        details.append(
            "| {name} | {occupied} | {max_count} ({ties} tied) | {lat:.0f}, {lon:.0f} | {rate} |".format(
                name=DISPLAY_NAME.get(source_id, source_id),
                occupied=_count(one["occupied_cells"]),
                max_count=_count(one["max_count"]),
                ties=_count(one["max_count_ties"]),
                lat=one["max_count_latitude_south"],
                lon=one["max_count_longitude_west"],
                rate=_fmt(one["max_detections_per_1000_km2"]),
            )
        )
    return "\n".join(
        [
            "## Global spatial distribution",
            "",
            summary["spatial_density"]["method"],
            "",
            "Latitude-band counts from the 30° grid. The JSON summary also stores the 30° longitude columns. "
            "A band total is a detection count, not a fire count.",
            "",
            "\n".join(lines),
            "",
            "\n".join(details),
            "",
            _figure(
                summary,
                "global_count_density.png",
                "One-degree detection counts on a log scale. Each archive has its own color scale. Cells are equal degree, not equal area.",
            ),
            _figure(
                summary,
                "global_area_normalized_density.png",
                "One-degree detections per 1,000 km² on a log scale, using spherical cell area. Each archive has its own color scale.",
            ),
        ]
    )


def _overlap_section(summary: dict) -> str:
    overlap = summary["spatial_overlap"]
    thresholds = overlap["thresholds_m"]
    header = (
        "| From | To | Detections in From | "
        + " | ".join(f"≤ {_fmt(threshold)} m" for threshold in thresholds)
        + " |"
    )
    rule = "| --- | --- | ---: | " + " | ".join("---:" for _threshold in thresholds) + " |"
    lines = [header, rule]
    for pair in overlap["pairs"]:
        cells = [
            DISPLAY_NAME.get(pair["satellite_a"], pair["satellite_a"]),
            DISPLAY_NAME.get(pair["satellite_b"], pair["satellite_b"]),
            _count(pair["detections_in_a"]),
        ]
        for threshold in pair["thresholds"]:
            cells.append(f"{_count(threshold['detections_with_neighbor'])} ({_pct(threshold['proportion'])})")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(
        [
            "## Spatial overlap",
            "",
            overlap["method"],
            "",
            "In the FIRMS active-fire CSV, `scan` and `track` are the along-scan and along-track pixel sizes in kilometers. "
            "The fixed radii below do not use those sizes.",
            "",
            "Each cell is the number and share of detections in the From satellite that have at least one detection from the To satellite within the radius.",
            "",
            "\n".join(lines),
        ]
    )


def _terra_aqua_section(summary: dict) -> str:
    satellites = summary["satellites"]
    if "Terra" not in satellites or "Aqua" not in satellites:
        return ""
    rows = [
        "| Quantity | Terra | Aqua |",
        "| --- | ---: | ---: |",
    ]
    for label, key_path in (
        ("Detections", ("detection_count",)),
        ("FRP median", ("frp", "median")),
        ("FRP maximum", ("frp", "maximum")),
        ("FRP zero count", ("frp", "zero_count")),
        ("Brightness median", ("brightness", "median")),
        ("bright_t31 median", ("bright_t31", "median")),
        ("Day share", ("daynight", "proportions", "D")),
        ("Confidence median (integer scale)", ("confidence", "median_integer")),
    ):
        values = []
        for name in ("Terra", "Aqua"):
            cursor = satellites[name]
            for key in key_path:
                cursor = cursor[key]
            values.append(_count(cursor) if key_path == ("detection_count",) or key_path[-1] == "zero_count" else _pct(cursor) if key_path[-1] == "D" else _fmt(cursor))
        rows.append(f"| {label} | {values[0]} | {values[1]} |")
    return "\n".join(
        [
            "## MODIS Terra and Aqua",
            "",
            "Terra and Aqua are separate populations inside the MODIS archive. "
            "The MODIS archive row elsewhere in this report is their sum for that file, not a third population.",
            "",
            "\n".join(rows),
            "",
            "The comparison stays on the MODIS columns and the MODIS integer confidence scale. "
            "It describes this date. Raw detection counts are not a measure of sensor quality.",
        ]
    )


def _extreme_section(summary: dict) -> str:
    records = summary["extreme_frp"]["records"]
    blocks = [
        "## Extreme FRP records",
        "",
        summary["extreme_frp"]["rule"],
        "",
        "Scan and track are printed beside FRP so the stored pixel geometry can be inspected. They are not used to adjust FRP.",
        "",
    ]
    for satellite in SATELLITE_ORDER:
        chosen = [record for record in records if record["satellite"] == satellite]
        if not chosen:
            continue
        cutoff = chosen[0]["extreme_cutoff"]
        blocks.append(
            f"### {DISPLAY_NAME[satellite]}: {_count(len(chosen))} flagged rows, cutoff {_fmt(cutoff)}, maximum source FRP {chosen[0]['row']['frp']}"
        )
        blocks.append("")
        blocks.append("| Line | Latitude | Longitude | UTC | Confidence | Scan | Track | FRP | Day/night |")
        blocks.append("| ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- |")
        for record in chosen[:8]:
            row = record["row"]
            blocks.append(
                "| {line} | {lat} | {lon} | {time} | {confidence} | {scan} | {track} | {frp} | {daynight} |".format(
                    line=record["line_number"],
                    lat=row["latitude"],
                    lon=row["longitude"],
                    time=row["acq_time"],
                    confidence=row["confidence"],
                    scan=row["scan"],
                    track=row["track"],
                    frp=row["frp"],
                    daynight=row["daynight"],
                )
            )
        if len(chosen) > 8:
            blocks.append("")
            blocks.append(
                f"The table shows 8 of {_count(len(chosen))} flagged rows, highest FRP first. "
                "The JSON summary contains every flagged source row."
            )
        blocks.append("")
    blocks.append(
        _figure(
            summary,
            "extreme_frp_locations.png",
            "Locations of FRP at or above the within-satellite 0.999 quantile. Positions are in degrees.",
        )
    )
    return "\n".join(blocks)


def render_report(summary: dict) -> str:
    dates = ", ".join(summary["scope"]["dates"]) or "the dates present in the archives"
    groups = _distribution_groups(summary)
    caveats = "\n".join(f"- {caveat}" for caveat in summary["scope"]["caveats"])
    parts = [
        "# Exploratory summary of FIRMS active-fire detections",
        "",
        f"**Scope:** {summary['scope']['label']} for {dates}.",
        "",
        (
            f"This report describes {_count(summary['scope']['detection_count'])} archived detections "
            "in the extracted FIRMS standard-processing files. "
            "Detections are not unique fires. No harmonization factor is calculated."
        ),
        "",
        "## Limits",
        "",
        caveats,
        "",
        summary["scope"]["populations"],
        "",
        "## Populations",
        "",
        _population_table(summary),
        "",
        "## FRP",
        "",
        summary["numeric_methods"]["std"]
        + " "
        + summary["numeric_methods"]["quantile_method"]
        + ". "
        + summary["numeric_methods"]["zero"]
        + " "
        + summary["numeric_methods"]["extremes"],
        "",
        "The mean and standard deviation respond strongly to the retained high values. "
        "The median and upper quantiles describe the rest of the stored distribution. "
        "Differences among satellites are descriptive for this date. "
        "Raw detection counts are not a measure of sensor quality.",
        "",
        _numeric_table(groups, "frp"),
        "",
        _figure(
            summary,
            "frp_ecdf_by_satellite.png",
            "Empirical FRP distributions by satellite. The left panel includes zeros and extremes. The right panel uses a logarithmic axis, so zero FRP is omitted there and reported in the table.",
        ),
        "## Brightness and bright_t31",
        "",
        "Both quantities use the column names stored in these files. "
        "A shared name is not a statement that the measurements have been cross-calibrated. "
        "VIIRS values are not renamed.",
        "",
        "### Brightness",
        "",
        _numeric_table(groups, "brightness"),
        "",
        "### bright_t31",
        "",
        _numeric_table(groups, "bright_t31"),
        "",
        _figure(
            summary,
            "brightness_bright_t31_ecdf.png",
            "Brightness and bright_t31 by satellite, using the stored column names and retaining extremes.",
        ),
        _confidence_sections(summary),
        "## Scan and track",
        "",
        "In the FIRMS active-fire CSV, scan and track are the along-scan and along-track pixel sizes in kilometers. "
        "The values below are the stored sizes. They are not converted to a common footprint.",
        "",
        "### Scan",
        "",
        _numeric_table(groups, "scan"),
        "",
        "### Track",
        "",
        _numeric_table(groups, "track"),
        "",
        _figure(
            summary,
            "scan_track_by_satellite.png",
            "Stored scan and track by satellite. Whiskers extend from the minimum to the maximum.",
        ),
        "## Day and night",
        "",
        "The daynight flag is the value stored in the archive. It is not recomputed from local solar time.",
        "",
        _daynight_table(groups),
        "",
        _figure(summary, "daynight_proportions.png", "Stored day and night shares by satellite for this date."),
        "## Acquisition time",
        "",
        summary["utc_time"]["note"],
        "",
        _hour_table(summary),
        "",
        _figure(
            summary,
            "detections_by_utc_hour.png",
            "Detection counts by UTC hour. The hour is the first two digits of acq_time and is not local time.",
        ),
        _spatial_section(summary),
        _overlap_section(summary),
        _terra_aqua_section(summary),
        _extreme_section(summary),
        "## Reproduction",
        "",
        "From the backend directory:",
        "",
        "```bash",
        ".venv\\Scripts\\python -m fire_data eda",
        "```",
        "",
        "The default overlap radii are 375 m, 1,000 m, and 5,000 m. "
        "Pass `--thresholds-m` with a comma-separated list of positive meter values to change them. "
        "The command reads each raw archive once, writes `reports/eda_summary.json` and `reports/eda_report.md`, "
        "and writes the figures under `reports/figures/`. It does not modify the raw CSV files.",
    ]
    return "\n".join(part for part in parts if part is not None).rstrip() + "\n"


def write_report(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(summary), encoding="utf-8")
