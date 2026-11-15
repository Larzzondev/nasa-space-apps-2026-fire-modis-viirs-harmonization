"""Plan a second FIRMS S-NPP delivery and compare it with the local archive.

The archive download tool can accept 16 and 25 July 2024. It returns a new
emailed order, not the existing request id. This module does not submit that
order and does not call the area API. A MAP_KEY is read only to see whether
one is present. The key is never stored, logged, or written into a report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

from fire_data.contract import BACKEND_ROOT, COLUMNS, NUMERIC_COLUMNS

VERIFICATION_DIR = BACKEND_ROOT / "data" / "verification"
REPORT_JSON = BACKEND_ROOT / "reports" / "firms_reacquisition_2024_07.json"
REPORT_MD = BACKEND_ROOT / "reports" / "firms_reacquisition_2024_07.md"
LOCAL_SNPP = (
    BACKEND_ROOT
    / "data"
    / "raw"
    / "monthly_2024_07"
    / "viirs_snpp"
    / "fire_archive_SV-C2_850322.csv"
)

TARGET_DATES = ("2024-07-16", "2024-07-25")
ARCHIVE_FILENAME_FAMILY = "fire_archive_SV-C2"
ARCHIVE_SHORT_NAME = "VNP14IMGTML"
API_SOURCE = "VIIRS_SNPP_SP"
ARCHIVE_COVERAGE_TEXT = "20 January 2012 - 2 November 2026"
DOWNLOAD_PAGE = "https://firms.modaps.eosdis.nasa.gov/download/"
README_URL = "https://firms.modaps.eosdis.nasa.gov/download/Readme.txt"
AREA_PAGE = "https://firms.modaps.eosdis.nasa.gov/api/area/"
AVAILABILITY_PAGE = "https://firms.modaps.eosdis.nasa.gov/api/data_availability/"
MISSING_DATA_URL = "https://firms.modaps.eosdis.nasa.gov/api/missing_data/?action=fetch_data"
AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_SNPP_SP/world/1/{day}"
AVAILABILITY_URL = "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{map_key}/VIIRS_SNPP_SP"

IDENTITY_FIELDS = ("latitude", "longitude", "acq_date", "acq_time", "satellite")
KEY_VARIABLES = ("MAP_KEY", "FIRMS_MAP_KEY")
ROW_HTML = re.compile(
    r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>",
    re.DOTALL,
)


class ReacquireError(ValueError):
    """The request cannot be turned into a FIRMS download by this module."""


def credential_status() -> dict[str, object]:
    """Report which variable is set, without reading the value into the result."""

    selected = next((name for name in KEY_VARIABLES if os.environ.get(name)), None)
    return {
        "variables": list(KEY_VARIABLES),
        "present": selected is not None,
        "selected_variable": selected,
        "value_recorded": False,
    }


def archive_date_supported(day: str) -> bool:
    """The download page lists S-NPP 375 m coverage through 2 November 2026."""

    parsed = date.fromisoformat(day)
    return date(2012, 1, 20) <= parsed <= date(2026, 11, 2)


def area_request_template(day: str) -> str:
    """Document the area URL with the key position still unsubstituted."""

    if day not in TARGET_DATES:
        raise ReacquireError(f"{day} is outside the two dates of this check")
    if not archive_date_supported(day):
        raise ReacquireError(f"{day} is outside the published S-NPP archive coverage")
    return AREA_URL.format(map_key="[MAP_KEY]", day=day)


def refuse_network_download() -> None:
    """The archive order is emailed, and the area API was not verified for these dates."""

    status = credential_status()
    if not status["present"]:
        raise ReacquireError(
            "No MAP_KEY or FIRMS_MAP_KEY is set. The area API was not called. "
            "The archive download is an authenticated email order, not a stable CSV URL."
        )
    raise ReacquireError(
        "A map key is present, but data availability for VIIRS_SNPP_SP was not confirmed "
        "and that API source is not the file fire_archive_SV-C2. No download was started."
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(column: str, raw: str) -> str:
    text = raw.strip()
    if column in NUMERIC_COLUMNS:
        if text == "":
            raise ReacquireError(f"Empty {column} is not converted to zero")
        try:
            value = Decimal(text)
        except InvalidOperation as error:
            raise ReacquireError(f"Unparseable {column}") from error
        rendered = format(value.normalize(), "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered or "0"
    if column == "acq_time" and text.isdigit():
        return text.zfill(4)
    return text


def load_rows(path: Path, *, only_date: str | None = None) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = [name.strip() for name in next(reader)]
        except StopIteration as error:
            raise ReacquireError(f"{path.name} has no header") from error
        rows: list[dict[str, str]] = []
        for line_number, raw in enumerate(reader, start=2):
            if len(raw) != len(header):
                raise ReacquireError(f"{path.name} line {line_number} does not match its header")
            record = {column: _canonical(column, value) for column, value in zip(header, raw)}
            if only_date is not None and record.get("acq_date") != only_date:
                continue
            rows.append(record)
    return header, rows


def compare_deliveries(
    original_header: list[str],
    original_rows: list[dict[str, str]],
    independent_header: list[str],
    independent_rows: list[dict[str, str]],
) -> dict[str, object]:
    """Compare two delivered tables. Matching rows are not unique fires."""

    shared = [column for column in original_header if column in independent_header]
    missing_identity = [column for column in IDENTITY_FIELDS if column not in shared]
    if missing_identity:
        raise ReacquireError("Both files need latitude, longitude, acq_date, acq_time, and satellite")
    value_fields = [column for column in shared if column not in IDENTITY_FIELDS]

    def identity(row: dict[str, str]) -> tuple[str, ...]:
        return tuple(_canonical(column, row[column]) for column in IDENTITY_FIELDS)

    def payload(row: dict[str, str]) -> tuple[str, ...]:
        return tuple(_canonical(column, row[column]) for column in value_fields)

    original_groups: dict[tuple[str, ...], Counter[tuple[str, ...]]] = {}
    independent_groups: dict[tuple[str, ...], Counter[tuple[str, ...]]] = {}
    for row in original_rows:
        original_groups.setdefault(identity(row), Counter())[payload(row)] += 1
    for row in independent_rows:
        independent_groups.setdefault(identity(row), Counter())[payload(row)] += 1

    exact = 0
    changed = 0
    only_original = 0
    only_independent = 0
    for key in set(original_groups) | set(independent_groups):
        left = original_groups.get(key, Counter())
        right = independent_groups.get(key, Counter())
        if not left:
            only_independent += sum(right.values())
            continue
        if not right:
            only_original += sum(left.values())
            continue
        for payload_key in set(left) | set(right):
            copies = min(left[payload_key], right[payload_key])
            exact += copies
            left[payload_key] -= copies
            right[payload_key] -= copies
        left_left = sum(left.values())
        right_left = sum(right.values())
        changed += min(left_left, right_left)
        if left_left > right_left:
            only_original += left_left - right_left
        elif right_left > left_left:
            only_independent += right_left - left_left

    return {
        "records_are_unique_fires": False,
        "identity_fields": list(IDENTITY_FIELDS),
        "value_fields": value_fields,
        "original_columns": original_header,
        "independent_columns": independent_header,
        "columns_only_in_original": [column for column in original_header if column not in independent_header],
        "columns_only_in_independent": [column for column in independent_header if column not in original_header],
        "original_rows": len(original_rows),
        "independent_rows": len(independent_rows),
        "exact_record_matches": exact,
        "missing_from_independent": only_original,
        "additional_in_independent": only_independent,
        "same_identity_changed_values": changed,
        "numeric_normalization": "Decimal values match after trailing zeros are removed",
        "empty_original_is_zero_detections": False,
        "empty_independent_is_zero_detections": False,
    }


def measure_dates(path: Path, dates: tuple[str, ...] = TARGET_DATES) -> dict[str, object]:
    """Read the local CSV. Dates with no row stay absent and are not stored as zero fires."""

    wanted = set(dates)
    counts = {day: 0 for day in dates}
    time_min = {day: None for day in dates}
    time_max = {day: None for day in dates}
    satellites: Counter[str] = Counter()
    lat_min: Decimal | None = None
    lat_max: Decimal | None = None
    lon_min: Decimal | None = None
    lon_max: Decimal | None = None
    rows = 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = [name.strip() for name in next(reader)]
        if tuple(header) != COLUMNS:
            raise ReacquireError(f"{path.name} does not use the local 15-column header")
        index = {name: position for position, name in enumerate(header)}
        for raw in reader:
            if len(raw) != len(header):
                raise ReacquireError(f"{path.name} has a row whose width differs from the header")
            rows += 1
            latitude = Decimal(raw[index["latitude"]])
            longitude = Decimal(raw[index["longitude"]])
            lat_min = latitude if lat_min is None else min(lat_min, latitude)
            lat_max = latitude if lat_max is None else max(lat_max, latitude)
            lon_min = longitude if lon_min is None else min(lon_min, longitude)
            lon_max = longitude if lon_max is None else max(lon_max, longitude)
            day = raw[index["acq_date"]].strip()
            if day not in wanted:
                continue
            counts[day] += 1
            clock = raw[index["acq_time"]].strip().zfill(4)
            time_min[day] = clock if time_min[day] is None else min(time_min[day], clock)
            time_max[day] = clock if time_max[day] is None else max(time_max[day], clock)
            satellites[raw[index["satellite"]].strip()] += 1
    return {
        "path": str(path),
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": rows,
        "header_matches_local_contract": True,
        "latitude_min": None if lat_min is None else format(lat_min, "f"),
        "latitude_max": None if lat_max is None else format(lat_max, "f"),
        "longitude_min": None if lon_min is None else format(lon_min, "f"),
        "longitude_max": None if lon_max is None else format(lon_max, "f"),
        "requested_area_of_interest": None,
        "dates": {
            day: {
                "rows_in_this_file": counts[day],
                "absent": counts[day] == 0,
                "zero_detections": False,
                "acq_time_min": time_min[day],
                "acq_time_max": time_max[day],
            }
            for day in dates
        },
        "satellites_on_target_dates": dict(satellites),
    }


def parse_missing_standard(payload: dict[str, object]) -> dict[str, object]:
    html = str(payload.get("html", ""))
    rows = ROW_HTML.findall(html)
    standard = [(left.strip(), sensor.strip()) for left, sensor, _right, _sensor in rows]
    snpp = [day for day, sensor in standard if sensor == "Suomi NPP (VIIRS)"]
    july = [day for day in snpp if day.startswith("2024-07")]
    return {
        "url": MISSING_DATA_URL,
        "table_rows": len(rows),
        "standard_column": "Date Missing / Satellite (Sensor)",
        "snpp_standard_missing_dates": len(snpp),
        "snpp_standard_earliest": min(snpp) if snpp else None,
        "snpp_standard_latest": max(snpp) if snpp else None,
        "suomi_npp_standard_missing_in_2024_07": july,
        "2024-07-16_listed": "2024-07-16" in snpp,
        "2024-07-25_listed": "2024-07-25" in snpp,
        "proves": (
            "FIRMS lists the date in the standard-data missing table for Suomi NPP (VIIRS), "
            "or does not list it."
        ),
        "does_not_prove": (
            "A listed day is not a fire count of zero. An unlisted day is not a complete archive "
            "and is not the CSV from order 850322."
        ),
    }


def fetch_missing_standard() -> dict[str, object]:
    request = Request(
        MISSING_DATA_URL,
        headers={"User-Agent": "nasa-fire-harmonization", "X-Requested-With": "XMLHttpRequest"},
    )
    with urlopen(request, timeout=60) as response:
        status = getattr(response, "status", None)
        payload = json.loads(response.read().decode("utf-8"))
    parsed = parse_missing_standard(payload)
    parsed["retrieved_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    parsed["http_status"] = status
    return parsed


def build_report(
    local: dict[str, object],
    missing: dict[str, object] | None,
    *,
    created_at: str,
    comparison: dict[str, object] | None = None,
) -> dict[str, object]:
    status = credential_status()
    if status["present"]:
        reason = (
            "A map key is present in the environment and was not sent. "
            "VIIRS_SNPP_SP availability was not confirmed, and that API source is not the local "
            "fire_archive_SV-C2 file. The archive email order was not submitted. No second CSV was saved."
        )
    else:
        reason = (
            "The archive tool accepts a new VIIRS S-NPP 375 m order for both dates and sends a ZIP by email. "
            "That order was not submitted. The area API documents a historical date, but it requires a MAP_KEY, "
            "and no key is configured. No second CSV was saved."
        )
    return {
        "created_at": created_at,
        "question": (
            "Can the local fire_archive_SV-C2 rows for 16 and 25 July 2024 be reproduced "
            "from a second official FIRMS delivery?"
        ),
        "result": "not_reproduced",
        "independent_file_retrieved": False,
        "comparison_status": "not_performed" if comparison is None else "performed",
        "comparison": comparison,
        "reason": reason,
        "products": {
            "local_filename_family": ARCHIVE_FILENAME_FAMILY,
            "local_file": local["filename"],
            "download_readme_short_name": ARCHIVE_SHORT_NAME,
            "download_readme_statement": (
                "fire_archive_SV-C2 is the VIIRS 375 m standard product VNP14IMGTML, "
                "which replaces NRT VNP14IMGTDL."
            ),
            "api_source": API_SOURCE,
            "api_source_statement": "VIIRS Suomi-NPP Standard Processing.",
            "relationship": (
                "The filename, the readme short name, and the API source are related FIRMS labels "
                "for S-NPP standard processing. This check does not show that an API response is the same file."
            ),
        },
        "archive_download": {
            "url": DOWNLOAD_PAGE,
            "readme": README_URL,
            "authentication": "Earthdata Login or an emailed one-time code. The order form is behind that login.",
            "delivery": "Email with a download link after the request is processed.",
            "formats_stated_on_the_public_page": ["shapefile", "csv", "json"],
            "historical_coverage_text": ARCHIVE_COVERAGE_TEXT,
            "dates_inside_published_coverage": {day: archive_date_supported(day) for day in TARGET_DATES},
            "stable_url_for_order_850322": None,
            "programmatic_order_endpoint_documented": False,
        },
        "area_api": {
            "documentation": AREA_PAGE,
            "availability_documentation": AVAILABILITY_PAGE,
            "source": API_SOURCE,
            "day_range_limit": "1..5",
            "historical_date_parameter": "YYYY-MM-DD, optional. Returns DATE through DATE+DAY_RANGE-1.",
            "request_templates": {day: area_request_template(day) for day in TARGET_DATES},
            "availability_template": AVAILABILITY_URL.format(map_key="[MAP_KEY]"),
            "unauthenticated_availability_status": 401,
            "called": False,
            "area_in_template": (
                "world is the documented global extent on the area page. "
                "It is not the recovered area of order 850322."
            ),
            "credential": status,
        },
        "local_archive": local,
        "firms_missing_data_table": missing,
        "manual_steps": manual_steps(),
        "does_not_prove": [
            "The local absence of rows on 25 July is not zero fire detections.",
            "A missing CMR granule is not evidence in this note.",
            "No harmonization coefficient is implied.",
            "Matching or missing rows, once a second file exists, are archive records rather than unique fires.",
        ],
    }


def manual_steps() -> list[str]:
    return [
        f"Open {DOWNLOAD_PAGE}.",
        "Authenticate with Earthdata Login or request the emailed code. The public page does not show the order form until that login succeeds.",
        "Request VIIRS S-NPP 375 m, the selection whose readme filename is DL_FIRE_SV-C2 and whose standard CSV is fire_archive_SV-C2. The published coverage line is "
        f"VIIRS S-NPP 375m: {ARCHIVE_COVERAGE_TEXT}.",
        "Choose CSV. Submit one order for 2024-07-16 and a separate order for 2024-07-25.",
        "Use the same area of interest as order 850322. That area was not stored with the local ZIP. A different box is a different request, not a reproduction.",
        "Wait for the email. Save the returned ZIP, unchanged, in backend/data/verification/. Do not replace DL_FIRE_SV-C2_850322.zip or fire_archive_SV-C2_850322.csv.",
        "The new request id will differ from 850322. Keep the provider filename.",
        "Compare that new CSV with the local file using python -m fire_data.reacquire --independent <new.csv>. Until that file exists, no record comparison is available.",
    ]


def render_markdown(report: dict[str, object]) -> str:
    local = report["local_archive"]
    dates = local["dates"]
    missing = report["firms_missing_data_table"]
    lines = [
        "# FIRMS S-NPP re-acquisition, 16 and 25 July 2024",
        "",
        "The local file was not reproduced. No second CSV was downloaded, so record differences were not calculated.",
        "",
        report["reason"],
        "",
        "## Product",
        "",
        f"Local file: `{local['filename']}`. SHA-256 `{local['sha256']}`. Rows in the file: {local['rows']}.",
        f"Download readme short name: `{ARCHIVE_SHORT_NAME}`. Area API source, not requested: `{API_SOURCE}`.",
        report["products"]["relationship"],
        "",
        "## Local rows",
        "",
        "A date with no row is absent from this file. It is not a count of zero detections. The requested area of interest was not stored.",
        "",
        "| UTC date | Rows in this file | Acquisition time | Absent from this file |",
        "| --- | --- | --- | --- |",
    ]
    for day, item in dates.items():
        clock = "none" if item["acq_time_min"] is None else f"{item['acq_time_min']}–{item['acq_time_max']} UTC"
        lines.append(
            f"| {day} | {item['rows_in_this_file']} | {clock} | {str(item['absent']).lower()} |"
        )
    lines.extend(
        [
            "",
            f"Observed latitude {local['latitude_min']} to {local['latitude_max']}. "
            f"Observed longitude {local['longitude_min']} to {local['longitude_max']}. "
            "These are ranges of stored points, not the order form's area.",
            "",
            "## Archive download",
            "",
            f"Page: {DOWNLOAD_PAGE}",
            f"VIIRS S-NPP 375 m coverage on that page: {ARCHIVE_COVERAGE_TEXT}. Both target dates fall inside it.",
            "Authentication is Earthdata Login or an emailed code. The processed order arrives by email. "
            "There is no documented URL that returns order 850322.",
            "",
            "Manual steps:",
            "",
        ]
    )
    lines.extend(f"{number}. {step}" for number, step in enumerate(report["manual_steps"], start=1))
    lines.extend(
        [
            "",
            "## Area API",
            "",
            "The area page documents `/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]/[DATE]` "
            "and says the date form returns that date through the following day range. `DAY_RANGE` is 1 to 5. "
            f"`{API_SOURCE}` is labeled standard processing. A MAP_KEY is required.",
            "",
            f"Credential present: {str(report['area_api']['credential']['present']).lower()}. The value was not recorded.",
            report["area_api"]["area_in_template"],
            "An availability URL without a key returns HTTP 401. The availability window for these two dates was therefore not read, and the API was not called.",
            "",
            "## FIRMS missing-data table",
            "",
        ]
    )
    if missing is None:
        lines.append("The missing-data table was not retrieved for this report.")
    else:
        listed = ", ".join(missing["suomi_npp_standard_missing_in_2024_07"])
        lines.extend(
            [
                f"Retrieved {missing.get('retrieved_at', 'during this session')} from {missing['url']}.",
                f"The table has {missing['table_rows']} rows. Suomi NPP standard dates marked missing span "
                f"{missing['snpp_standard_earliest']} through {missing['snpp_standard_latest']}.",
                f"July 2024 Suomi NPP standard dates in that column: {listed}.",
                "16 July 2024 is not in the column. 25 July 2024 is in the column.",
                missing["does_not_prove"],
            ]
        )
    lines.extend(["", "## Comparison", ""])
    if report["comparison"] is None:
        lines.extend(
            [
                "Not performed. There is no independent CSV.",
                "Exact matches, missing records, additional records, and changed values are not estimated.",
                "",
            ]
        )
    else:
        comparison = report["comparison"]
        lines.extend(
            [
                f"Exact record matches: {comparison['exact_record_matches']}.",
                f"Missing from the independent file: {comparison['missing_from_independent']}.",
                f"Additional in the independent file: {comparison['additional_in_independent']}.",
                f"Same identity with changed values: {comparison['same_identity_changed_values']}.",
                "These are archive rows, not unique fires.",
                "",
            ]
        )
    lines.extend(["## What this does not prove", ""])
    lines.extend(f"- {item}" for item in report["does_not_prove"])
    lines.extend(
        [
            "",
            "## Next step",
            "",
            "Submit the two manual archive orders only after the original area of interest is known. "
            "Save them beside the current files and compare the tables. Do not fill 25 July with zeros, "
            "and do not treat either day as harmonized.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(report: dict[str, object]) -> None:
    REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record the FIRMS S-NPP re-acquisition check.")
    parser.add_argument("--independent", type=Path, help="CSV from a later official order. Omit it to write the blocker report.")
    parser.add_argument("--skip-missing-table", action="store_true")
    args = parser.parse_args(argv)
    if not LOCAL_SNPP.is_file():
        raise SystemExit(f"Local archive is not available: {LOCAL_SNPP}")
    local = measure_dates(LOCAL_SNPP)
    missing = None if args.skip_missing_table else fetch_missing_standard()
    comparison = None
    if args.independent is not None:
        if not args.independent.is_file():
            raise SystemExit(f"Independent CSV was not found: {args.independent}")
        per_date = {}
        for day in TARGET_DATES:
            original_header, original_rows = load_rows(LOCAL_SNPP, only_date=day)
            independent_header, independent_rows = load_rows(args.independent, only_date=day)
            per_date[day] = compare_deliveries(original_header, original_rows, independent_header, independent_rows)
        comparison = per_date
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = build_report(local, missing, created_at=created_at, comparison=comparison)
    write_reports(report)
    print(f"result={report['result']} comparison={report['comparison_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
