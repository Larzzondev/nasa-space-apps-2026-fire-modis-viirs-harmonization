"""Markdown and JSON writers for the data-readiness review."""

from __future__ import annotations

import json
from pathlib import Path

from fire_data.temporal import assert_output_allowed

DISPLAY = {
    "Terra": "Terra",
    "Aqua": "Aqua",
    "N20": "NOAA-20",
    "N21": "NOAA-21",
    "SNPP": "S-NPP",
    "candidate_measurement": "Candidate measurement",
    "observation_geometry": "Observation geometry",
    "quality_indicator": "Quality indicator",
    "matching_key": "Matching key",
    "stratification_variable": "Stratification variable",
    "excluded_until_further_evidence": "Excluded until further evidence",
}


def _name(value: str) -> str:
    return DISPLAY.get(value, value)


def _count(value: int) -> str:
    return f"{int(value):,}"


def _num(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.{digits}f}"


def _value(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, dict):
        return ", ".join(f"{key} ({_count(count)})" for key, count in value.items()) or "—"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def render_report(summary: dict) -> str:
    scope = summary["scope"]
    dates = ", ".join(scope["dates_present"]) or "none"
    discrepancy = summary["discrepancy"]
    matrix_by_source: dict[str, list[dict]] = {}
    for row in summary["provenance_matrix"]:
        matrix_by_source.setdefault(row["source_id"], []).append(row)
    matrix_sections = []
    for source_id, rows in matrix_by_source.items():
        lines = [
            f"### {source_id}",
            "",
            "| Field | Status | Value | Evidence |",
            "| --- | --- | --- | --- |",
        ]
        for row in rows:
            lines.append(
                f"| `{row['field']}` | {row['status']} | {_value(row['value'])} | {row['evidence']} |"
            )
        matrix_sections.append("\n".join(lines))
    duplicate = summary["duplicates"]
    match_lines = [
        "| Pair | Radius (m) | Max Δt (min) | Raw pairs | Unique source | Unique target | Detections with a neighbor | Source NN p50 (m) | Pair distance p50 (m) | Pair Δt p50 (min) | Same fire |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary["matching"]:
        match_lines.append(
            "| {pair} | {radius} | {window} | {pairs} | {source} | {target} | {involved} | {nn} | {distance} | {delta} | {same_fire} |".format(
                pair=f"{_name(row['satellite_a'])}–{_name(row['satellite_b'])}",
                radius=_num(row["radius_m"], 0),
                window=row["max_delta_minutes"],
                pairs=_count(row["raw_pair_count"]),
                source=_count(row["unique_source_detections"]),
                target=_count(row["unique_target_detections"]),
                involved=_count(row["detections_with_at_least_one_neighbor"]),
                nn=_num(row["nearest_neighbor_source_to_target_m"]["p50"]),
                distance=_num(row["pair_distance_m"]["p50"]),
                delta=_num(row["abs_delta_minutes"]["p50"]),
                same_fire=row["same_fire"],
            )
        )
    variable_lines = [
        "| Variable | Class | Why |",
        "| --- | --- | --- |",
    ]
    for row in summary["variables"]:
        variable_lines.append(f"| `{row['variable']}` | {_name(row['classification'])} | {row['rationale']} |")
    spec = summary["acquisition_specification"]
    products = spec["product_identifiers"]["download_readme"]
    product_lines = [
        "| Identifier role | Value in the download readme |",
        "| --- | --- |",
    ]
    for key, value in products.items():
        product_lines.append(f"| `{key}` | {value if value is not None else 'not stated'} |")
    document_lines = [
        f"- {item['text']} Source: {item['url']} (retrieved {item['retrieved']})."
        for item in summary["document_statements"]
    ]
    method = summary["matching_method"]
    parts = [
        "# Data readiness and matching methodology",
        "",
        (
            "This review asks whether the current files and the proximity matcher are ready for a "
            "multi-date calibration. It is not a temporal validation and it does not add a statistical model. "
            f"Dates present: {dates}. Temporal validation: {scope['temporal_validation']}. "
            "Calibration coefficients calculated: no."
        ),
        "",
        "## Provenance discrepancy",
        "",
        discrepancy["download_readme"],
        "",
        discrepancy["api_catalog"],
        "",
        discrepancy["local_files"],
        "",
        f"Resolution: {discrepancy['resolution']}. {discrepancy['effect_on_current_archives']}",
        "",
        "The FIRMS VIIRS attribute page also describes a version-suffix convention for URT, RT, NRT, and standard processing. "
        "The local VIIRS version string is `2`, and the local MODIS version string is `61.03`. "
        "Those strings are not the page's examples (`2.0URT`, `2.0RT`, `1.0NRT`, `1.0`). "
        "The suffix convention was not applied. A filename beginning with `fire_archive` or `fire_nrt` was not applied either.",
        "",
        "Two further document mismatches are recorded and left unresolved. "
        "The VIIRS page says the Suomi NPP satellite code is `N`, while the local S-NPP file stores `SNPP`. "
        "The page says the hot-spot type attribute is only available for VNP14IMGT standard-quality data, while every local archive, including NOAA-20 and NOAA-21, has a `type` column. "
        "Neither mismatch identifies the processing stream.",
        "",
        "### Documents retrieved",
        "",
        "\n".join(document_lines),
        "",
        "## Provenance matrix",
        "",
        "Verified values were read from the local files. Unverified values are document statements that do not identify these files. Missing values have no field in the files and were not filled from the filename or the version column.",
        "",
        "\n\n".join(matrix_sections),
        "",
        "## Exact product and processing stream",
        "",
        "The product short name and the processing stream are missing for every local archive. "
        "Candidate names from the download readme and sensor codes from the API catalog remain unverified against these CSVs.",
        "",
        "## Matching methodology",
        "",
        f"Reviewed implementation: `{method['implementation_reviewed']}`.",
        "",
        f"- Distance: {method['distance']}",
        f"- Time: {method['time']}",
        f"- Satellite pairs: {method['satellite_pairs']}",
        f"- Detection pairs: {method['detection_pairs']}",
        f"- Nearest-neighbor ties: {method['nearest_neighbor_tie']}",
        f"- Duplicates: {method['duplicates']}",
        f"- Same fire: `{method['same_fire']}`.",
        f"- Unique fires: {method['unique_fires']}",
        "",
        (
            f"Duplicate accounting on the current files: {_count(duplicate['row_count'])} data rows, "
            f"{_count(duplicate['exact_duplicate_rows'])} exact duplicate rows, "
            f"{_count(duplicate['location_time_duplicate_rows'])} extra rows with the same satellite, "
            "latitude text, longitude text, date, and time. "
            f"Rows removed before matching: {_count(duplicate['duplicates_removed_before_matching'])}. "
            f"{duplicate['handling']}"
        ),
        "",
        "Nearest-neighbor distance is directional and is limited to the largest radius in the configuration set. "
        "A detection whose nearest partner lies outside a tighter radius is counted as without a neighbor for that tighter configuration. "
        "Raw pair count can exceed either unique-detection count because one detection can pair with many partners. "
        "`detections_with_at_least_one_neighbor` is the sum of the unique source rows and the unique target rows that participate. "
        "That sum is a count of archived rows. It is not a count of fires, and it is not added across satellite pairs.",
        "",
        "Full quantile distributions for pair distance, absolute time difference, and both nearest-neighbor directions are in `data_readiness.json`. "
        "The table below is the per-configuration summary.",
        "",
        "\n".join(match_lines),
        "",
        "## Calibration readiness",
        "",
        "Each variable has one class. No coefficient is calculated.",
        "",
        "\n".join(variable_lines),
        "",
        "## Data acquisition specification",
        "",
        spec["purpose"],
        "",
        f"Target date count: {spec['target_date_count']}. Dates acquired for this specification: none. "
        f"Dates already on disk: {', '.join(spec['dates_present_in_current_archives']) or 'none'}. "
        "Fabricated dates: no.",
        "",
        spec["date_selection"]["rule"],
        "",
        spec["date_selection"]["completeness"],
        "",
        spec["date_selection"]["current_holdings"],
        "",
        "### Product identifiers to require in the manifest",
        "",
        "\n".join(product_lines),
        "",
        f"API sensor codes listed on the availability page: {', '.join(f'`{code}`' for code in spec['product_identifiers']['api_sensor_codes'])}.",
        "",
        spec["product_identifiers"]["note"],
        "",
        "### Processing-level requirements",
        "",
        "\n".join(f"- {item}" for item in spec["processing_level_requirements"]),
        "",
        "### Required metadata",
        "",
        "\n".join(f"- {item}" for item in spec["required_metadata"]),
        "",
        "### Missing-data handling",
        "",
        "\n".join(f"- {item}" for item in spec["missing_data_handling"]),
        "",
        "### File naming and checksums",
        "",
        (
            f"Preserve the provider filename: {spec['file_naming_and_checksums']['preserve_provider_filename']}. "
            f"Layout: `{spec['file_naming_and_checksums']['layout']}`. "
            f"Manifest: `{spec['file_naming_and_checksums']['manifest']}`. "
            f"Checksum: {spec['file_naming_and_checksums']['checksum_algorithm']}. "
            f"{spec['file_naming_and_checksums']['checksum_rule']}"
        ),
        "",
        "## Unresolved",
        "",
        "- The processing stream and product short name of each local archive.",
        "- Which FIRMS page is current for NOAA-20 and NOAA-21 standard products, and whether either page describes these downloads.",
        "- Whether the stored VIIRS version `2` was intended to match the attribute page's unsuffixed standard example.",
        "- Whether any proximity pair is the same physical fire.",
        "- The 30 acquisition dates themselves, which are not chosen until a stream and an area of interest are recorded.",
        "",
        "## Reproduction",
        "",
        "From the backend directory:",
        "",
        "```bash",
        ".venv\\Scripts\\python -m fire_data.readiness",
        "```",
        "",
        "The command writes `reports/data_readiness.md` and `reports/data_readiness.json`. "
        "It leaves the exploratory report, the anomaly report, the temporal report, and `data/raw/` unchanged.",
        "",
    ]
    return "\n".join(parts)


def write_readiness(summary: dict, output_dir: Path) -> tuple[Path, Path]:
    assert_output_allowed(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "data_readiness.md"
    json_path = output_dir / "data_readiness.json"
    assert_output_allowed(report_path)
    assert_output_allowed(json_path)
    report_path.write_text(render_report(summary), encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return report_path, json_path
