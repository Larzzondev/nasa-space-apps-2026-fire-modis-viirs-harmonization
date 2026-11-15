"""Controlled FIRMS area-API client for the 7 July 2024 NOAA provenance check.

The MAP_KEY is read from the environment or from ``backend/.env``. It is never
written into a report, a log line, or an exception message. A missing key
stops the client before any authenticated URL is opened.

URL shapes come from the FIRMS area page, the FIRMS API index, and the FIRMS
API code-examples page. This module does not invent a path segment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import perf_counter, process_time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from fire_data.contract import BACKEND_ROOT

AREA_PAGE = "https://firms.modaps.eosdis.nasa.gov/api/area/"
AVAILABILITY_PAGE = "https://firms.modaps.eosdis.nasa.gov/api/data_availability/"
API_INDEX = "https://firms.modaps.eosdis.nasa.gov/api/"
ACADEMY_PAGE = "https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html"
MAP_KEY_PAGE = "https://firms.modaps.eosdis.nasa.gov/api/map_key"
ORIGIN = "https://firms.modaps.eosdis.nasa.gov"

AREA_TEMPLATE = "/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]/[DATE]"
AVAILABILITY_TEMPLATE = "/api/data_availability/csv/[MAP_KEY]/[SENSOR]"
STATUS_TEMPLATE = "/mapserver/mapkey_status/?MAP_KEY=[MAP_KEY]"

DOCUMENTED_SOURCES = (
    "LANDSAT_NRT",
    "MODIS_NRT",
    "MODIS_SP",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA20_SP",
    "VIIRS_NOAA21_NRT",
    "VIIRS_NOAA21_SP",
    "VIIRS_SNPP_NRT",
    "VIIRS_SNPP_SP",
)
TARGET_SOURCES = ("VIIRS_NOAA20_SP", "VIIRS_NOAA21_SP")
TARGET_DAY = "2024-07-07"
KEY_VARIABLES = ("FIRMS_MAP_KEY", "MAP_KEY")
ENV_PATH = BACKEND_ROOT / ".env"
INGESTION_MANIFEST = BACKEND_ROOT / "reports" / "ingestion_2024_07.json"
REPORT_JSON = BACKEND_ROOT / "reports" / "firms_api_provenance_2024_07_07.json"
REPORT_MD = BACKEND_ROOT / "reports" / "firms_api_provenance_2024_07_07.md"
TIMING_JSON = BACKEND_ROOT / "reports" / "milestones" / "milestone_13_timing.json"
TIMING_MD = BACKEND_ROOT / "reports" / "milestones" / "milestone_13_timing.md"
USER_AGENT = "nasa-fire-harmonization"

ARCHIVES = (
    {
        "platform": "NOAA-20",
        "api_source": "VIIRS_NOAA20_SP",
        "path": BACKEND_ROOT / "data" / "raw" / "viirs_noaa20" / "fire_archive_J1V-C2_850119.csv",
        "monthly_path": BACKEND_ROOT / "data" / "raw" / "monthly_2024_07" / "viirs_noaa20" / "fire_archive_J1V-C2_850320.csv",
        "monthly_sensor": "viirs_noaa20",
    },
    {
        "platform": "NOAA-21",
        "api_source": "VIIRS_NOAA21_SP",
        "path": BACKEND_ROOT / "data" / "raw" / "viirs_noaa21" / "fire_archive_J2V-C2_850120.csv",
        "monthly_path": BACKEND_ROOT / "data" / "raw" / "monthly_2024_07" / "viirs_noaa21" / "fire_archive_J2V-C2_850321.csv",
        "monthly_sensor": "viirs_noaa21",
    },
)

DOCUMENTATION_URLS = (API_INDEX, AREA_PAGE, AVAILABILITY_PAGE, ACADEMY_PAGE)
IDENTITY_FIELDS = ("latitude", "longitude", "acq_date", "acq_time", "satellite")
ATTRIBUTE_LINK = re.compile(
    r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>\s*Attribute table for ([^<]+?)\s*</a>',
    re.IGNORECASE,
)
PHRASES = (
    "VIIRS_NOAA20_SP",
    "VIIRS_NOAA21_SP",
    "VJ114IMG",
    "VJ114IMGDL",
    "VJ114IMGML",
    "VJ214IMG",
    "VJ214IMGDL",
    "VJ214IMGML",
    "fire_archive_J1V-C2",
    "fire_archive_J2V-C2",
    "fire_nrt_J1V-C2",
    "fire_nrt_J2V-C2",
    "not yet available",
    "Standard Processing",
    "bright_ti4",
    "bright_ti5",
    "brightness",
    "bright_t31",
)


class FirmsApiError(ValueError):
    """The FIRMS request cannot be made or cannot be read as a fire table."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact(text: str, key: str | None) -> str:
    """Remove a map key from text that might be printed or stored."""

    if not key:
        return text
    redacted = text.replace(key, "[MAP_KEY]")
    return redacted.replace(key.lower(), "[MAP_KEY]")


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    found: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if name:
            found[name] = value
    return found


def load_map_key(environ: dict[str, str] | None = None, env_path: Path | None = None) -> tuple[str | None, str | None]:
    """Return ``(value, source)``. The value stays out of reports."""

    environment = os.environ if environ is None else environ
    for name in KEY_VARIABLES:
        value = environment.get(name)
        if value:
            return value, f"environment:{name}"
    parsed = _parse_env_file(ENV_PATH if env_path is None else env_path)
    for name in KEY_VARIABLES:
        value = parsed.get(name)
        if value:
            return value, f"env_file:{name}"
    return None, None


def credential_status(environ: dict[str, str] | None = None, env_path: Path | None = None) -> dict[str, object]:
    value, source = load_map_key(environ, env_path)
    return {
        "variables": list(KEY_VARIABLES),
        "env_file": str(ENV_PATH if env_path is None else env_path),
        "env_file_exists": (ENV_PATH if env_path is None else env_path).is_file(),
        "present": value is not None,
        "selected_source": source,
        "value_recorded": False,
    }


def _validate_source(source: str) -> str:
    if source not in DOCUMENTED_SOURCES and source != "all":
        raise FirmsApiError(f"{source} is not a source identifier on the retrieved FIRMS area page")
    return source


def _validate_day(day: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise FirmsApiError("FIRMS documents the historical date as YYYY-MM-DD")
    datetime.strptime(day, "%Y-%m-%d")
    return day


def _validate_day_range(day_range: int) -> int:
    if day_range < 1 or day_range > 5:
        raise FirmsApiError("FIRMS documents DAY_RANGE as an integer from 1 through 5")
    return day_range


def format_bbox(west: str, south: str, east: str, north: str) -> str:
    """Format a documented west,south,east,north box. ``world`` is separate."""

    values = {}
    for name, text in (("west", west), ("south", south), ("east", east), ("north", north)):
        try:
            values[name] = Decimal(text)
        except InvalidOperation as error:
            raise FirmsApiError(f"{name} is not a decimal coordinate") from error
    if values["west"] < Decimal("-180") or values["east"] > Decimal("180"):
        raise FirmsApiError("Longitude is outside the documented maximum boundary -180 to 180")
    if values["south"] < Decimal("-90") or values["north"] > Decimal("90"):
        raise FirmsApiError("Latitude is outside the documented maximum boundary -90 to 90")
    if values["west"] > values["east"] or values["south"] > values["north"]:
        raise FirmsApiError("The area page documents a west,south,east,north box. A wrapped box is not constructed.")
    return f"{west},{south},{east},{north}"


def redacted_area_url(source: str, area: str, day: str, day_range: int = 1) -> str:
    _validate_source(source)
    _validate_day(day)
    _validate_day_range(day_range)
    if area != "world" and area.count(",") != 3:
        raise FirmsApiError("AREA_COORDINATES is world or west,south,east,north")
    return ORIGIN + AREA_TEMPLATE.replace("[SOURCE]", source).replace("[AREA_COORDINATES]", area).replace(
        "[DAY_RANGE]", str(day_range)
    ).replace("[DATE]", day)


def redacted_availability_url(sensor: str) -> str:
    _validate_source(sensor)
    return ORIGIN + AVAILABILITY_TEMPLATE.replace("[SENSOR]", sensor)


def authenticated_url(template_url: str, key: str) -> str:
    if "[MAP_KEY]" not in template_url:
        raise FirmsApiError("Refusing to open a FIRMS URL that has no key placeholder")
    if not key:
        raise FirmsApiError("Refusing to open an authenticated FIRMS URL without a MAP_KEY")
    return template_url.replace("[MAP_KEY]", key)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _header_map(headers: object) -> dict[str, str]:
    items = getattr(headers, "items", None)
    if items is None:
        return {}
    return {str(name): str(value) for name, value in items()}


def fetch_public(url: str, *, timeout: float = 60) -> dict[str, object]:
    """GET a documentation page. No map key is added."""

    if "MAP_KEY" in url or "[MAP_KEY]" in url:
        raise FirmsApiError("A documentation fetch does not carry a MAP_KEY")
    attempts: list[dict[str, object]] = []
    started = perf_counter()
    last_error: str | None = None
    for attempt in (1, 2):
        attempt_started = perf_counter()
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read()
                status = int(getattr(response, "status", 0) or 0)
                headers = _header_map(response.headers)
            elapsed = perf_counter() - attempt_started
            record = {
                "attempt": attempt,
                "url": url,
                "http_status": status,
                "elapsed_seconds": round(elapsed, 6),
                "body_bytes": len(body),
                "sha256": sha256_bytes(body),
                "headers": headers,
                "retrieved_at": utc_now(),
            }
            attempts.append({key: value for key, value in record.items() if key != "body"})
            text = body.decode("utf-8", errors="replace")
            return {
                **record,
                "body_text": text,
                "attempts": attempts,
                "retries": attempt - 1,
                "network_wait_seconds": round(perf_counter() - started, 6),
            }
        except HTTPError as error:
            body = error.read()
            elapsed = perf_counter() - attempt_started
            status = int(error.code)
            headers = _header_map(error.headers)
            attempts.append(
                {
                    "attempt": attempt,
                    "url": url,
                    "http_status": status,
                    "elapsed_seconds": round(elapsed, 6),
                    "body_bytes": len(body),
                    "sha256": sha256_bytes(body),
                    "headers": headers,
                    "retrieved_at": utc_now(),
                }
            )
            if status < 500 or attempt == 2:
                text = body.decode("utf-8", errors="replace")
                return {
                    "attempt": attempt,
                    "url": url,
                    "http_status": status,
                    "elapsed_seconds": round(elapsed, 6),
                    "body_bytes": len(body),
                    "sha256": sha256_bytes(body),
                    "headers": headers,
                    "retrieved_at": utc_now(),
                    "body_text": text,
                    "attempts": attempts,
                    "retries": attempt - 1,
                    "network_wait_seconds": round(perf_counter() - started, 6),
                }
            last_error = f"HTTP {status}"
        except URLError as error:
            elapsed = perf_counter() - attempt_started
            reason = str(getattr(error, "reason", error))
            attempts.append(
                {
                    "attempt": attempt,
                    "url": url,
                    "http_status": None,
                    "elapsed_seconds": round(elapsed, 6),
                    "error": reason,
                    "retrieved_at": utc_now(),
                }
            )
            last_error = reason
            if attempt == 2:
                break
    raise FirmsApiError(f"Documentation request failed after 2 attempts: {last_error}")


def fetch_authenticated(url: str, key: str, *, timeout: float = 180) -> dict[str, object]:
    """GET one authenticated FIRMS URL. The stored record uses the redacted URL."""

    redacted = redact(url, key)
    attempts: list[dict[str, object]] = []
    started = perf_counter()
    last_error = "request failed"
    for attempt in (1, 2):
        attempt_started = perf_counter()
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read()
                status = int(getattr(response, "status", 0) or 0)
                headers = _header_map(response.headers)
            elapsed = perf_counter() - attempt_started
            safe_headers = {name: redact(value, key) for name, value in headers.items()}
            attempts.append(
                {
                    "attempt": attempt,
                    "url": redacted,
                    "http_status": status,
                    "elapsed_seconds": round(elapsed, 6),
                    "body_bytes": len(body),
                    "sha256": sha256_bytes(body),
                    "headers": safe_headers,
                    "retrieved_at": utc_now(),
                }
            )
            return {
                "url": redacted,
                "http_status": status,
                "headers": safe_headers,
                "body": body,
                "body_bytes": len(body),
                "sha256": sha256_bytes(body),
                "elapsed_seconds": round(elapsed, 6),
                "network_wait_seconds": round(perf_counter() - started, 6),
                "attempts": attempts,
                "retries": attempt - 1,
                "retrieved_at": attempts[-1]["retrieved_at"],
            }
        except HTTPError as error:
            body = error.read()
            status = int(error.code)
            headers = {name: redact(value, key) for name, value in _header_map(error.headers).items()}
            elapsed = perf_counter() - attempt_started
            attempts.append(
                {
                    "attempt": attempt,
                    "url": redacted,
                    "http_status": status,
                    "elapsed_seconds": round(elapsed, 6),
                    "body_bytes": len(body),
                    "sha256": sha256_bytes(body),
                    "headers": headers,
                    "retrieved_at": utc_now(),
                }
            )
            if status < 500 or attempt == 2:
                return {
                    "url": redacted,
                    "http_status": status,
                    "headers": headers,
                    "body": body,
                    "body_bytes": len(body),
                    "sha256": sha256_bytes(body),
                    "elapsed_seconds": round(elapsed, 6),
                    "network_wait_seconds": round(perf_counter() - started, 6),
                    "attempts": attempts,
                    "retries": attempt - 1,
                    "retrieved_at": attempts[-1]["retrieved_at"],
                }
            last_error = f"HTTP {status}"
        except URLError as error:
            reason = redact(str(getattr(error, "reason", "network error")), key)
            elapsed = perf_counter() - attempt_started
            attempts.append(
                {
                    "attempt": attempt,
                    "url": redacted,
                    "http_status": None,
                    "elapsed_seconds": round(elapsed, 6),
                    "error": reason,
                    "retrieved_at": utc_now(),
                }
            )
            last_error = reason
            if attempt == 2:
                break
    failure = FirmsApiError(redact(f"FIRMS request failed after 2 attempts: {last_error}", key))
    failure.attempts = attempts  # type: ignore[attr-defined]
    raise failure


def parse_availability(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise FirmsApiError("Availability response has no header")
    fields = [name.strip() for name in reader.fieldnames]
    if "data_id" not in fields or "min_date" not in fields or "max_date" not in fields:
        raise FirmsApiError("Availability response does not have data_id, min_date, and max_date")
    rows = []
    for raw in reader:
        rows.append({name: (raw.get(name) or "").strip() for name in ("data_id", "min_date", "max_date")})
    return rows


def date_inside(day: str, row: dict[str, str]) -> bool | None:
    try:
        target = datetime.strptime(day, "%Y-%m-%d").date()
        start = datetime.strptime(row["min_date"], "%Y-%m-%d").date()
        end = datetime.strptime(row["max_date"], "%Y-%m-%d").date()
    except ValueError:
        return None
    return start <= target <= end


def interpret_availability(text: str, source: str, day: str) -> dict[str, object]:
    """Read one data-availability CSV. A missing window is not an outside-window result."""

    try:
        rows = parse_availability(text)
    except FirmsApiError as error:
        return {
            "parsed": False,
            "rows": [],
            "inside": None,
            "error": str(error),
            "reason": "The data-availability body was not a data_id, min_date, max_date table.",
        }
    matched = [row for row in rows if row["data_id"] == source]
    if not matched:
        return {
            "parsed": True,
            "rows": [],
            "inside": None,
            "error": None,
            "reason": f"The data-availability table did not contain {source}.",
        }
    inside = date_inside(day, matched[0])
    if inside is None:
        reason = f"The served window for {source} could not be read as dates."
    elif inside:
        reason = f"{day} is inside the served window for {source}."
    else:
        reason = (
            f"{day} is outside the served window for {source}: "
            f"{matched[0]['min_date']} through {matched[0]['max_date']}."
        )
    return {"parsed": True, "rows": matched, "inside": inside, "error": None, "reason": reason}


def parse_fire_csv(text: str) -> tuple[list[str], list[dict[str, str]], dict[str, object]]:
    """Parse a FIRMS CSV. A header-only file is an empty table, not zero fires."""

    if text.strip() == "":
        return [], [], {
            "parsed_as_fire_table": False,
            "header_only": False,
            "rows": 0,
            "zero_fire_activity": False,
            "reason": "The response body is empty. It is not a count of zero fire detections.",
        }
    reader = csv.reader(io.StringIO(text))
    try:
        header = [name.strip() for name in next(reader)]
    except StopIteration:
        return [], [], {
            "parsed_as_fire_table": False,
            "header_only": False,
            "rows": 0,
            "zero_fire_activity": False,
            "reason": "The response has no header. It is not a count of zero fire detections.",
        }
    if "latitude" not in header or "longitude" not in header:
        prefix = " ".join(text.split())[:180]
        return header, [], {
            "parsed_as_fire_table": False,
            "header_only": False,
            "rows": 0,
            "zero_fire_activity": False,
            "body_prefix": prefix,
            "reason": "The response is not a fire-location table. It is not a count of zero fire detections.",
        }
    rows: list[dict[str, str]] = []
    for raw in reader:
        if len(raw) != len(header):
            raise FirmsApiError("A FIRMS CSV row does not match its header")
        if not any(cell.strip() for cell in raw):
            continue
        rows.append({column: value.strip() for column, value in zip(header, raw)})
    return header, rows, {
        "parsed_as_fire_table": True,
        "header_only": len(rows) == 0,
        "rows": len(rows),
        "zero_fire_activity": False,
        "reason": (
            "A header-only CSV is an empty delivered table. "
            "It is not recorded as zero fire activity."
            if len(rows) == 0
            else "Rows were parsed. Product equivalence is still not_assessed."
        ),
    }


def _decimal_key(column: str, raw: str) -> str:
    text = raw.strip()
    if column in {"latitude", "longitude", "brightness", "scan", "track", "bright_t31", "bright_ti4", "bright_ti5", "frp"}:
        try:
            value = Decimal(text)
        except InvalidOperation:
            return text
        rendered = format(value.normalize(), "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered or "0"
    if column == "acq_time" and text.isdigit():
        return text.zfill(4)
    return text


def compare_tables(
    archive_header: list[str],
    archive_rows: list[dict[str, str]],
    api_header: list[str],
    api_rows: list[dict[str, str]],
) -> dict[str, object]:
    """Compare two delivered tables without renaming fields or declaring the same product."""

    shared = [column for column in archive_header if column in api_header]
    missing_identity = [column for column in IDENTITY_FIELDS if column not in shared]
    archive_only = [column for column in archive_header if column not in api_header]
    api_only = [column for column in api_header if column not in archive_header]
    relationship = {
        "shared_column_names": shared,
        "archive_only_columns": archive_only,
        "api_only_columns": api_only,
        "brightness_renamed_to_bright_ti4": False,
        "bright_t31_renamed_to_bright_ti5": False,
        "row_equality_forced": False,
        "product_equivalence": "not_assessed",
        "same_fire": "not_assessed",
    }
    if missing_identity:
        return {
            **relationship,
            "identity_comparison": "not_performed",
            "reason": "Identity comparison needs latitude, longitude, acq_date, acq_time, and satellite under those names in both tables.",
            "archive_rows": len(archive_rows),
            "api_rows": len(api_rows),
            "zero_fire_activity": False,
        }

    def identity(row: dict[str, str]) -> tuple[str, ...]:
        return tuple(_decimal_key(column, row[column]) for column in IDENTITY_FIELDS)

    value_fields = [column for column in shared if column not in IDENTITY_FIELDS]

    def payload(row: dict[str, str]) -> tuple[str, ...]:
        return tuple(_decimal_key(column, row[column]) for column in value_fields)

    archive_groups: dict[tuple[str, ...], Counter[tuple[str, ...]]] = {}
    api_groups: dict[tuple[str, ...], Counter[tuple[str, ...]]] = {}
    for row in archive_rows:
        archive_groups.setdefault(identity(row), Counter())[payload(row)] += 1
    for row in api_rows:
        api_groups.setdefault(identity(row), Counter())[payload(row)] += 1
    exact = changed = only_archive = only_api = 0
    for key in set(archive_groups) | set(api_groups):
        left = archive_groups.get(key, Counter())
        right = api_groups.get(key, Counter())
        if not left:
            only_api += sum(right.values())
            continue
        if not right:
            only_archive += sum(left.values())
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
            only_archive += left_left - right_left
        elif right_left > left_left:
            only_api += right_left - left_left
    return {
        **relationship,
        "identity_comparison": "performed",
        "identity_fields": list(IDENTITY_FIELDS),
        "value_fields_compared": value_fields,
        "archive_rows": len(archive_rows),
        "api_rows": len(api_rows),
        "exact_shared_field_matches": exact,
        "archive_rows_without_api_identity": only_archive,
        "api_rows_without_archive_identity": only_api,
        "same_identity_changed_shared_values": changed,
        "records_are_unique_fires": False,
        "zero_fire_activity": False,
        "empty_api_table_is_zero_detections": False,
    }


def measure_archive(path: Path) -> dict[str, object]:
    """Read a local CSV. The file is not written."""

    digest = hashlib.sha256()
    lat_min: tuple[Decimal, str] | None = None
    lat_max: tuple[Decimal, str] | None = None
    lon_min: tuple[Decimal, str] | None = None
    lon_max: tuple[Decimal, str] | None = None
    dates: set[str] = set()
    time_min: str | None = None
    time_max: str | None = None
    satellites: Counter[str] = Counter()
    instruments: Counter[str] = Counter()
    versions: Counter[str] = Counter()
    confidences: Counter[str] = Counter()
    seen: set[tuple[str, ...]] = set()
    duplicate_rows = 0
    rows = 0
    with path.open("rb") as handle:
        payload = handle.read()
    digest.update(payload)
    text = payload.decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    try:
        header = [name.strip() for name in next(reader)]
    except StopIteration as error:
        raise FirmsApiError(f"{path.name} has no header") from error
    index = {name: position for position, name in enumerate(header)}
    required = ("latitude", "longitude", "acq_date", "acq_time", "satellite", "instrument", "confidence", "version")
    missing = [name for name in required if name not in index]
    if missing:
        raise FirmsApiError(f"{path.name} is missing {', '.join(missing)}")
    for raw in reader:
        if len(raw) != len(header):
            raise FirmsApiError(f"{path.name} has a row whose width differs from the header")
        rows += 1
        key = tuple(cell.strip() for cell in raw)
        if key in seen:
            duplicate_rows += 1
        else:
            seen.add(key)
        latitude_text = raw[index["latitude"]].strip()
        longitude_text = raw[index["longitude"]].strip()
        latitude = Decimal(latitude_text)
        longitude = Decimal(longitude_text)
        if lat_min is None or latitude < lat_min[0]:
            lat_min = (latitude, latitude_text)
        if lat_max is None or latitude > lat_max[0]:
            lat_max = (latitude, latitude_text)
        if lon_min is None or longitude < lon_min[0]:
            lon_min = (longitude, longitude_text)
        if lon_max is None or longitude > lon_max[0]:
            lon_max = (longitude, longitude_text)
        day = raw[index["acq_date"]].strip()
        dates.add(day)
        clock = raw[index["acq_time"]].strip()
        time_min = clock if time_min is None else min(time_min, clock)
        time_max = clock if time_max is None else max(time_max, clock)
        satellites[raw[index["satellite"]].strip()] += 1
        instruments[raw[index["instrument"]].strip()] += 1
        versions[raw[index["version"]].strip()] += 1
        confidences[raw[index["confidence"]].strip()] += 1
    if lat_min is None or lat_max is None or lon_min is None or lon_max is None:
        raise FirmsApiError(f"{path.name} has a header and no data rows")
    return {
        "path": str(path),
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "header": header,
        "rows": rows,
        "duplicate_full_rows": duplicate_rows,
        "acq_dates": sorted(dates),
        "acq_time_min": time_min,
        "acq_time_max": time_max,
        "latitude_min": lat_min[1],
        "latitude_max": lat_max[1],
        "longitude_min": lon_min[1],
        "longitude_max": lon_max[1],
        "satellites": dict(satellites),
        "instruments": dict(instruments),
        "versions": dict(versions),
        "confidences": dict(confidences),
        "observed_bbox": format_bbox(lon_min[1], lat_min[1], lon_max[1], lat_max[1]),
        "bbox_meaning": (
            "Axis-aligned extent of stored detection coordinates. "
            "This is not the original archive-download request area."
        ),
    }


def documentation_facts(pages: dict[str, dict[str, object]]) -> dict[str, object]:
    area = str(pages.get(AREA_PAGE, {}).get("body_text", ""))
    availability = str(pages.get(AVAILABILITY_PAGE, {}).get("body_text", ""))
    index = str(pages.get(API_INDEX, {}).get("body_text", ""))
    academy = str(pages.get(ACADEMY_PAGE, {}).get("body_text", ""))
    area_normal = re.sub(r"\s+", " ", area)
    combined = "\n".join((area, availability, index, academy))
    attribute_links = [
        {"label": label.strip(), "href": urljoin(AREA_PAGE, href)}
        for href, label in ATTRIBUTE_LINK.findall(area)
    ]
    return {
        "area_template_present": AREA_TEMPLATE in area_normal,
        "historical_date_syntax": "YYYY-MM-DD" if "YYYY-MM-DD" in area_normal else None,
        "day_range_text": "1 .. 5" if "1 .. 5" in area_normal or "1..5" in area_normal else None,
        "world_token_present": "world" in area_normal and "-180,-90,180,90" in area_normal.replace(" ", ""),
        "output_format_in_area_template": "csv",
        "transaction_limit_text": "5000 transactions" if "5000 transactions" in combined else None,
        "sources_on_area_page": [source for source in DOCUMENTED_SOURCES if source in area],
        "sources_on_availability_page": [source for source in DOCUMENTED_SOURCES if source in availability],
        "target_sources_on_area_page": [source for source in TARGET_SOURCES if source in area],
        "api_index_describes_area_as": "CSV format" if "CSV format" in index or "CSV" in index else None,
        "country_service_marked_unavailable": "Feature currently not available" in index,
        "archive_download_equated_to_area_csv": False,
        "attribute_links": attribute_links,
        "academy_documents_availability_csv": "/api/data_availability/csv/" in academy,
        "academy_documents_area_csv": "/api/area/csv/" in academy,
        "academy_documents_status_query": "/mapserver/mapkey_status/?MAP_KEY=" in academy,
        "academy_nrt_example_uses_bright_ti4": "bright_ti4" in academy,
        "academy_nrt_example_is_not_a_july_2024_response": True,
        "phrases_present": {phrase: phrase in combined for phrase in PHRASES},
    }


def _public_record(page: dict[str, object]) -> dict[str, object]:
    return {
        "url": page.get("url"),
        "http_status": page.get("http_status"),
        "retrieved_at": page.get("retrieved_at"),
        "elapsed_seconds": page.get("elapsed_seconds"),
        "network_wait_seconds": page.get("network_wait_seconds"),
        "body_bytes": page.get("body_bytes"),
        "sha256": page.get("sha256"),
        "retries": page.get("retries"),
        "headers": page.get("headers"),
        "attempts": page.get("attempts"),
    }


def configuration_needed() -> dict[str, object]:
    return {
        "variable": "FIRMS_MAP_KEY",
        "also_accepted": "MAP_KEY",
        "precedence": "The process environment is read first. backend/.env is read only when the environment variable is absent.",
        "file": "backend/.env",
        "file_is_gitignored": True,
        "line": "FIRMS_MAP_KEY=<MAP_KEY issued by FIRMS>",
        "issuer": MAP_KEY_PAGE,
        "do_not": [
            "Commit backend/.env.",
            "Print the key.",
            "Put the key in a URL that is written to a log or a report.",
        ],
    }


def build_report(
    *,
    created_at: str,
    archives: list[dict[str, object]],
    monthly_checks: list[dict[str, object]],
    pages: dict[str, dict[str, object]],
    facts: dict[str, object],
    credential: dict[str, object],
    requests: list[dict[str, object]],
    comparison: dict[str, object] | None,
) -> dict[str, object]:
    authenticated = [item for item in requests if item.get("authenticated") is True and item.get("sent") is True]
    area_tables = [
        item
        for item in requests
        if item.get("kind") == "area" and isinstance(item.get("parse"), dict) and item["parse"].get("parsed_as_fire_table") is True
    ]
    area_sent = [item for item in requests if item.get("kind") == "area" and item.get("sent") is True]
    if not authenticated:
        result = "not_requested"
    elif area_tables:
        result = "retrieved"
    elif area_sent:
        result = "request_failed"
    else:
        result = "area_not_sent"
    return {
        "created_at": created_at,
        "question": (
            "Does an authenticated FIRMS area response for VIIRS_NOAA20_SP and VIIRS_NOAA21_SP "
            "on 2024-07-07 identify the processing stream of the local July 7 archive CSVs?"
        ),
        "result": result,
        "authenticated_requests_sent": bool(authenticated),
        "processing_stream": "unresolved",
        "same_fire": "not_assessed",
        "harmonization_coefficient_calculated": False,
        "missing_observations_filled": False,
        "product_equivalence": "not_assessed",
        "original_request_area_reproduced": False,
        "level2_swath_equated_to_firms_csv": False,
        "credential": credential,
        "configuration_needed": None if credential["present"] else configuration_needed(),
        "documentation": {
            "pages": [_public_record(page) for page in pages.values()],
            "facts": facts,
            "same_product_as_archive_download": (
                "The retrieved area page names a CSV query for a source code. "
                "It does not say that the response is the archive-download file "
                "fire_archive_J1V-C2 or fire_archive_J2V-C2. Equivalence stays not_assessed."
            ),
        },
        "local_archives": archives,
        "monthly_checksums": monthly_checks,
        "requests": requests,
        "comparison": comparison,
        "comparison_status": "not_performed" if comparison is None else "performed",
        "does_not_prove": [
            "An absent API response is not zero fire activity.",
            "The observed coordinate extent is not the original order polygon.",
            "A catalog label Standard Processing does not assign the local file's stream.",
            "A Level-2 swath identifier is not a FIRMS location CSV.",
            "same_fire remains not_assessed.",
        ],
    }


def render_markdown(report: dict[str, object]) -> str:
    facts = report["documentation"]["facts"]
    lines = [
        "# FIRMS area API provenance, 7 July 2024",
        "",
        f"Created {report['created_at']}.",
        "",
        "## Result",
        "",
        "Authenticated FIRMS requests were not sent."
        if not report["authenticated_requests_sent"]
        else "Authenticated FIRMS requests were sent. The processing stream of the local files remains a separate conclusion.",
        "",
        f"Processing stream of the local NOAA-20 and NOAA-21 archive CSVs: `{report['processing_stream']}`.",
        f"`same_fire` is `{report['same_fire']}`. Product equivalence is `{report['product_equivalence']}`.",
        "No harmonization coefficient was calculated. No missing observation was filled.",
        "",
    ]
    if report["configuration_needed"] is not None:
        needed = report["configuration_needed"]
        lines.extend(
            [
                "## Configuration required before a keyed request",
                "",
                f"`{needed['variable']}` was absent from the process environment and from `{needed['file']}`.",
                f"The file did not exist at the time of this run (`env_file_exists` is false in the JSON).",
                f"Create `{needed['file']}` with one line, `{needed['line']}`. "
                f"The value is the MAP_KEY issued at {needed['issuer']}.",
                f"`{needed['also_accepted']}` is also read. The process environment takes precedence over the file.",
                "The file is covered by the repository gitignore. It must not be committed. "
                "The client keeps the value out of reports, exception text, and stored URLs.",
                "",
            ]
        )
    lines.extend(
        [
            "## Official API statements used",
            "",
            f"Area page: {AREA_PAGE}",
            f"Data-availability page: {AVAILABILITY_PAGE}",
            f"API index: {API_INDEX}",
            f"API code examples: {ACADEMY_PAGE}",
            "",
            f"Area template present on the retrieved area page: `{str(facts['area_template_present']).lower()}`. "
            f"Template: `{AREA_TEMPLATE}`.",
            f"Historical date syntax on that page: `{facts['historical_date_syntax']}`. "
            "The dated form returns that date through date plus day range minus one.",
            f"DAY_RANGE text: `{facts['day_range_text']}`.",
            "AREA_COORDINATES is `west,south,east,north` or the token `world`, defined on the page as `-180,-90,180,90`. "
            "Hemisphere names are rejected by the page. The maximum boundary is `-180,-90,180,90`.",
            f"Output format named by the area template and the API index: `{facts['output_format_in_area_template']}`.",
            f"Transaction limit text found: `{facts['transaction_limit_text']}` per 10-minute interval. "
            "The page says a larger transaction may count as more than one request and gives a 7-day request as the example.",
            f"Target source identifiers present on the area page: {', '.join(facts['target_sources_on_area_page']) or 'none'}.",
            "The area page labels `VIIRS_NOAA20_SP` as VIIRS NOAA-20 Standard Processing and "
            "`VIIRS_NOAA21_SP` as VIIRS NOAA-21 Standard Processing. Those are catalog labels.",
            report["documentation"]["same_product_as_archive_download"],
            "",
            "The code-examples page shows a `VIIRS_NOAA20_NRT` world request whose sample columns include "
            "`bright_ti4` and `bright_ti5` and whose sample version cell is `2.0NRT`. "
            "That example is not a 7 July 2024 standard-processing response, and its column names are not renamed onto the local header.",
            "",
            "## Local July 7 archive CSVs",
            "",
            "The comparison files are the single-day archive downloads `fire_archive_J1V-C2_850119.csv` and "
            "`fire_archive_J2V-C2_850120.csv`. They were opened read-only. "
            "The original request area is not stored with them, so it is not claimed to have been reproduced.",
            "",
            "| Platform | File | Rows | SHA-256 | Observed extent (west, south, east, north) | Dates |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for archive in report["local_archives"]:
        lines.append(
            f"| {archive['platform']} | `{archive['filename']}` | {archive['rows']} | `{archive['sha256']}` | "
            f"`{archive['observed_bbox']}` | {', '.join(archive['acq_dates'])} |"
        )
    lines.extend(
        [
            "",
            "Each extent is the axis-aligned range of stored points. It is the smallest rectangle that contains those points. "
            "It is not the archive order's area of interest. Longitude slices outside that range were not part of the planned request.",
            "",
            "Requests. Stored URLs keep the key position unsubstituted:",
            "",
        ]
    )
    for item in report["requests"]:
        lines.append(
            f"- `{item.get('source')}` `{item.get('kind', 'area')}` sent=`{str(item.get('sent')).lower()}` "
            f"HTTP `{item.get('http_status')}` rows `{item.get('rows')}` bytes `{item.get('body_bytes')}` "
            f"seconds `{item.get('elapsed_seconds')}` retries `{item.get('retries', 0)}`. {item.get('reason', '')}"
        )
        if item.get("body_prefix"):
            lines.append(f"  Response prefix: `{item['body_prefix']}`")
        if item.get("availability_rows"):
            lines.append(f"  Availability rows: `{item['availability_rows']}`.")
        if item.get("summary"):
            lines.append(f"  API field summary: `{item['summary']}`.")
    lines.extend(["", "## Comparison", ""])
    comparison = report["comparison"]
    if comparison is None:
        lines.extend(
            [
                "Not performed. No API fire table was parsed, so record counts, coordinate differences, "
                "timestamp differences, duplicate observations, and missing observations were not calculated from an API response.",
                "An empty or failed response is not interpreted as zero fire activity.",
                "",
            ]
        )
    else:
        for source, item in comparison.items():
            lines.append(f"### {source}")
            lines.append("")
            lines.append(
                f"Archive rows `{item.get('archive_rows')}`. API rows `{item.get('api_rows')}`. "
                f"Exact shared-field matches `{item.get('exact_shared_field_matches')}`. "
                f"Archive rows without an API identity `{item.get('archive_rows_without_api_identity')}`. "
                f"API rows without an archive identity `{item.get('api_rows_without_archive_identity')}`. "
                f"Same identity with changed shared values `{item.get('same_identity_changed_shared_values')}`."
            )
            lines.append(
                f"Columns only in the archive: `{item.get('archive_only_columns')}`. "
                f"Columns only in the API table: `{item.get('api_only_columns')}`."
            )
            lines.append(
                "Field names were not renamed. Product equivalence remains `not_assessed`. "
                "`same_fire` remains `not_assessed`."
            )
            if item.get("reason"):
                lines.append(str(item["reason"]))
            lines.append("")
    lines.extend(["## Monthly archive checksums", ""])
    for item in report["monthly_checksums"]:
        lines.append(
            f"- `{item['filename']}` SHA-256 `{item['sha256']}` matches the ingestion manifest: "
            f"`{str(item['matches_ingestion_manifest']).lower()}`."
        )
    lines.extend(["", "## What this run leaves unresolved", ""])
    lines.extend(f"- {item}" for item in report["does_not_prove"])
    lines.extend(
        [
            "",
            "The local NOAA-20 and NOAA-21 archive streams stay `unresolved`. "
            "A catalog label, an API version cell, or a row overlap does not by itself name the stream of the archive file.",
            "",
        ]
    )
    return "\n".join(lines)


def append_manifest_record(path: Path, record: dict[str, object]) -> None:
    """Add a provenance record. Existing manifest fields stay byte-stable on first insert."""

    original = path.read_text(encoding="utf-8")
    data = json.loads(original)
    sensors_snapshot = json.dumps(data["sensors"], sort_keys=True)
    preserved = {key: value for key, value in data.items() if key != "firms_api_provenance"}
    preserved_snapshot = json.dumps(preserved, sort_keys=True)
    checks = [item for item in list(data.get("firms_api_provenance") or []) if item.get("id") != record["id"]]
    checks.append(record)
    if "firms_api_provenance" in data:
        data["firms_api_provenance"] = checks
        rendered = json.dumps(data, indent=2) + "\n"
    else:
        raw_lines = json.dumps(checks, indent=2).split("\n")
        shifted = ["  " + line if line else line for line in raw_lines[1:]]
        newline = "\r\n" if "\r\n" in original else "\n"
        stripped = original.rstrip()
        if not stripped.endswith("}"):
            raise FirmsApiError("The ingestion manifest is not a JSON object")
        body = stripped[:-1].rstrip()
        insertion = "," + newline + '  "firms_api_provenance": [' + newline + newline.join(shifted)
        rendered = body + insertion + newline + "}" + newline
    parsed = json.loads(rendered)
    if json.dumps(parsed["sensors"], sort_keys=True) != sensors_snapshot:
        raise FirmsApiError("Refusing to write a manifest that changes sensor records")
    remaining = {key: value for key, value in parsed.items() if key != "firms_api_provenance"}
    if json.dumps(remaining, sort_keys=True) != preserved_snapshot:
        raise FirmsApiError("Refusing to write a manifest that changes original fields")
    path.write_text(rendered, encoding="utf-8")


def _monthly_check(archive: dict[str, object], manifest: dict[str, object]) -> dict[str, object]:
    path = archive["monthly_path"]
    digest = sha256_file(path) if isinstance(path, Path) and path.is_file() else None
    recorded = {sensor["sensor"]: sensor for sensor in manifest.get("sensors", [])}
    source = recorded.get(archive["monthly_sensor"], {})
    return {
        "sensor": archive["monthly_sensor"],
        "filename": path.name if isinstance(path, Path) else None,
        "bytes": path.stat().st_size if isinstance(path, Path) and path.is_file() else None,
        "sha256": digest,
        "ingestion_sha256": source.get("csv_sha256"),
        "matches_ingestion_manifest": digest is not None and digest == source.get("csv_sha256"),
        "processing_stream_left_unchanged": source.get("processing_stream") is None,
    }


def planned_requests(archives: list[dict[str, object]]) -> list[dict[str, object]]:
    requests = []
    for archive in archives:
        area = str(archive["observed_bbox"])
        source = str(archive["api_source"])
        url = redacted_area_url(source, area, TARGET_DAY, 1)
        availability = redacted_availability_url(source)
        requests.append(
            {
                "platform": archive["platform"],
                "source": source,
                "date": TARGET_DAY,
                "day_range": 1,
                "area": area,
                "area_meaning": archive["bbox_meaning"],
                "output_format": "csv",
                "url": url,
                "availability_url": availability,
                "authenticated": True,
                "sent": False,
                "http_status": None,
                "headers": None,
                "body_bytes": None,
                "sha256": None,
                "rows": None,
                "elapsed_seconds": None,
                "network_wait_seconds": None,
                "retries": 0,
                "attempts": [],
                "reason": "FIRMS_MAP_KEY is not configured. The authenticated URL was not opened.",
                "zero_fire_activity": False,
            }
        )
    return requests


def execute_requests(archives: list[dict[str, object]], key: str) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    """Availability first. An area request is sent only when the served window contains the target day."""

    requests: list[dict[str, object]] = []
    comparisons: dict[str, object] = {}
    for archive in archives:
        source = str(archive["api_source"])
        area = str(archive["observed_bbox"])
        availability_template = redacted_availability_url(source)
        area_template = redacted_area_url(source, area, TARGET_DAY, 1)
        availability_record = _call(availability_template, key, "availability")
        availability_record.update(
            {
                "platform": archive["platform"],
                "source": source,
                "date": TARGET_DAY,
                "kind": "data_availability",
            }
        )
        requests.append(availability_record)
        inside: bool | None = None
        availability_text = str(availability_record.get("text") or "")
        if availability_text:
            availability_record["body_prefix"] = _redacted_prefix(availability_text, key)
        if availability_record.get("http_status") == 200 and availability_text:
            interpreted = interpret_availability(availability_text, source, TARGET_DAY)
            availability_record["availability_rows"] = interpreted["rows"]
            availability_record["target_date_inside_served_window"] = interpreted["inside"]
            availability_record["availability_reason"] = interpreted["reason"]
            if interpreted["error"]:
                availability_record["parse_error"] = redact(str(interpreted["error"]), key)
            inside = interpreted["inside"]
        elif availability_text:
            availability_record["availability_reason"] = "The data-availability response was not HTTP 200."
        if inside is not True:
            requests.append(
                {
                    "platform": archive["platform"],
                    "source": source,
                    "date": TARGET_DAY,
                    "day_range": 1,
                    "area": area,
                    "area_meaning": archive["bbox_meaning"],
                    "output_format": "csv",
                    "url": area_template,
                    "authenticated": True,
                    "sent": False,
                    "kind": "area",
                    "http_status": None,
                    "rows": None,
                    "retries": 0,
                    "attempts": [],
                    "reason": (
                        "The area request was not sent. "
                        + str(availability_record.get("availability_reason") or "The served window was not confirmed.")
                    ),
                    "zero_fire_activity": False,
                }
            )
            continue
        area_record = _call(area_template, key, "area")
        area_record.update(
            {
                "platform": archive["platform"],
                "source": source,
                "date": TARGET_DAY,
                "day_range": 1,
                "area": area,
                "area_meaning": archive["bbox_meaning"],
                "output_format": "csv",
                "kind": "area",
                "zero_fire_activity": False,
            }
        )
        if area_record.get("http_status") == 200 and "text" in area_record:
            header, rows, parsed = parse_fire_csv(str(area_record.pop("text")))
            area_record["parse"] = parsed
            area_record["rows"] = parsed["rows"]
            area_record["header"] = header
            area_record["summary"] = summarize_fire_table(header, rows)
            if not parsed["parsed_as_fire_table"]:
                prefix = str(parsed.get("body_prefix") or "")
                area_record["body_prefix"] = redact(prefix, key)
                parsed["body_prefix"] = area_record["body_prefix"]
            if parsed["parsed_as_fire_table"]:
                archive_header = list(archive["header"])
                archive_rows = _load_rows(Path(str(archive["path"])))
                comparisons[source] = compare_tables(archive_header, archive_rows, header, rows)
            else:
                comparisons[source] = {
                    "product_equivalence": "not_assessed",
                    "same_fire": "not_assessed",
                    "identity_comparison": "not_performed",
                    "reason": parsed["reason"],
                    "zero_fire_activity": False,
                }
        else:
            if area_record.get("text"):
                area_record["body_prefix"] = _redacted_prefix(str(area_record["text"]), key)
            area_record.pop("text", None)
            comparisons[source] = {
                "product_equivalence": "not_assessed",
                "same_fire": "not_assessed",
                "identity_comparison": "not_performed",
                "reason": "The area response was not a successful CSV body.",
                "zero_fire_activity": False,
            }
        requests.append(area_record)
    return requests, comparisons or None


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def _call(template_url: str, key: str, kind: str) -> dict[str, object]:
    live = authenticated_url(template_url, key)
    try:
        fetched = fetch_authenticated(live, key)
    except FirmsApiError as error:
        attempts = getattr(error, "attempts", [])
        return {
            "url": template_url,
            "authenticated": True,
            "sent": True,
            "kind": kind,
            "http_status": None,
            "error": redact(str(error), key),
            "attempts": attempts,
            "retries": max(len(attempts) - 1, 0),
            "zero_fire_activity": False,
            "reason": redact(str(error), key),
        }
    text = fetched["body"].decode("utf-8", errors="replace") if isinstance(fetched["body"], bytes) else ""
    if key and key in text:
        text = redact(text, key)
    stored = {key_name: value for key_name, value in fetched.items() if key_name != "body"}
    stored["text"] = text
    stored["authenticated"] = True
    stored["sent"] = True
    stored["kind"] = kind
    stored["reason"] = f"HTTP {fetched['http_status']}"
    stored["zero_fire_activity"] = False
    return stored


def _redacted_prefix(text: str, key: str, limit: int = 180) -> str:
    return redact(" ".join(text.split())[:limit], key)


def summarize_fire_table(header: list[str], rows: list[dict[str, str]]) -> dict[str, object]:
    """Keep field evidence from an API table without storing the rows."""

    summary: dict[str, object] = {"rows": len(rows), "columns": header}
    for column in ("satellite", "instrument", "version", "confidence", "acq_date", "daynight"):
        if column not in header:
            continue
        summary[column] = dict(Counter(row.get(column, "") for row in rows))
    return summary


def _drop_response_text(requests: list[dict[str, object]], key: str | None = None) -> None:
    for item in requests:
        text = item.pop("text", None)
        if not isinstance(text, str):
            continue
        if "sha256" not in item:
            item["sha256"] = sha256_bytes(text.encode("utf-8"))
        if item.get("http_status") != 200 or item.get("parse_error") or item.get("parsed_as_fire_table") is False:
            item["body_prefix"] = _redacted_prefix(text, key or "")


def peak_working_set() -> int | None:
    from fire_data.spatiotemporal_analysis import _peak_working_set

    return _peak_working_set()


def python_environment() -> dict[str, object]:
    executable = Path(sys.executable)
    return {
        "executable": str(executable),
        "version": sys.version.split()[0],
        "windows_store_stub": "WindowsApps" in str(executable),
        "venv_name": executable.parent.parent.name,
    }


def write_reports(report: dict[str, object]) -> None:
    encoded = json.dumps(report, indent=2)
    if re.search(r"/csv/[^/\"\s]{16,}/", encoded) or re.search(r"MAP_KEY=(?!<)[^\s\"<]{8,}", encoded):
        raise FirmsApiError("Refusing to write a report that embeds a MAP_KEY value")
    REPORT_JSON.write_text(encoded + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")


def run(environ: dict[str, str] | None = None) -> dict[str, object]:
    started = perf_counter()
    cpu_started = process_time()
    created_at = utc_now()
    archives = []
    for spec in ARCHIVES:
        measured = measure_archive(spec["path"])
        measured["platform"] = spec["platform"]
        measured["api_source_requested_beside_this_file"] = spec["api_source"]
        measured["api_source_is_not_a_processing_stream_assignment"] = True
        archives.append({**spec, **measured})
    manifest = json.loads(INGESTION_MANIFEST.read_text(encoding="utf-8"))
    monthly = [_monthly_check(archive, manifest) for archive in archives]
    pages: dict[str, dict[str, object]] = {}
    page_errors = []
    for url in DOCUMENTATION_URLS:
        try:
            pages[url] = fetch_public(url)
        except FirmsApiError as error:
            page_errors.append({"url": url, "error": str(error)})
    facts = documentation_facts(pages)
    key, _source = load_map_key(environ)
    credential = credential_status(environ)
    comparison = None
    if key is None:
        requests = planned_requests(archives)
    else:
        if not facts["area_template_present"] or set(TARGET_SOURCES) - set(facts["target_sources_on_area_page"]):
            raise FirmsApiError("The live area page no longer shows the documented template or target sources. No area URL was opened.")
        requests, comparison = execute_requests(archives, key)
    _drop_response_text(requests, key)
    for archive in archives:
        archive.pop("monthly_path", None)
        archive.pop("path", None)
    safe_archives = []
    for archive in archives:
        safe_archives.append({key_name: value for key_name, value in archive.items() if key_name != "monthly_path"})
    report = build_report(
        created_at=created_at,
        archives=safe_archives,
        monthly_checks=monthly,
        pages=pages,
        facts=facts,
        credential=credential,
        requests=requests,
        comparison=comparison,
    )
    report["documentation_fetch_errors"] = page_errors
    before = {archive["filename"]: archive["sha256"] for archive in safe_archives}
    after = {spec["path"].name: sha256_file(spec["path"]) for spec in ARCHIVES}
    report["original_day_files_unchanged"] = before == after
    report["checksums_after_run"] = after
    if key:
        encoded = json.dumps(report)
        if key in encoded:
            report = json.loads(redact(encoded, key))
    write_reports(report)
    append_manifest_record(
        INGESTION_MANIFEST,
        {
            "id": "firms-api-2024-07-07-noaa20-noaa21",
            "created_at": created_at,
            "report": "reports/firms_api_provenance_2024_07_07.json",
            "authenticated_requests_sent": report["authenticated_requests_sent"],
            "processing_stream": "unresolved",
            "same_fire": "not_assessed",
            "original_sensor_records_modified": False,
            "original_day_files_unchanged": report["original_day_files_unchanged"],
        },
    )
    finished = utc_now()
    timing = {
        "milestone": 13,
        "started_at": created_at,
        "finished_at": finished,
        "wall_clock_seconds": round(perf_counter() - started, 6),
        "cpu_seconds": round(process_time() - cpu_started, 6),
        "peak_working_set_bytes": peak_working_set(),
        "python": python_environment(),
        "authenticated_requests_sent": report["authenticated_requests_sent"],
        "retries": sum(int(item.get("retries") or 0) for item in requests),
        "documentation_pages": report["documentation"]["pages"],
        "data_requests": [
            {
                "source": item.get("source"),
                "kind": item.get("kind", "area"),
                "sent": item.get("sent"),
                "http_status": item.get("http_status"),
                "elapsed_seconds": item.get("elapsed_seconds"),
                "network_wait_seconds": item.get("network_wait_seconds"),
                "retries": item.get("retries"),
                "body_bytes": item.get("body_bytes"),
                "rows": item.get("rows"),
                "sha256": item.get("sha256"),
            }
            for item in requests
        ],
        "pytest": None,
    }
    TIMING_JSON.parent.mkdir(parents=True, exist_ok=True)
    TIMING_JSON.write_text(json.dumps(timing, indent=2) + "\n", encoding="utf-8")
    return report


def render_timing_markdown(timing: dict[str, object]) -> str:
    python = timing["python"]
    lines = [
        "# Milestone 13 timing",
        "",
        f"Started: {timing['started_at']}",
        f"Finished: {timing['finished_at']}",
        "",
        "The MAP_KEY is not in this file.",
        "",
        "## Python",
        "",
        f"Interpreter: `{python['executable']}`.",
        f"Version: `{python['version']}`.",
        f"Windows Store stub: `{str(python['windows_store_stub']).lower()}`.",
        "",
        "## Accounting",
        "",
        f"Wall clock: {timing['wall_clock_seconds']} seconds.",
        f"CPU seconds: {timing['cpu_seconds']}.",
        f"Peak working set: {timing['peak_working_set_bytes']} bytes."
        if timing["peak_working_set_bytes"] is not None
        else "Peak working set was not measured.",
        f"Authenticated data requests sent: `{str(timing['authenticated_requests_sent']).lower()}`.",
        f"Retries on data requests: {timing['retries']}.",
        "",
        "## Documentation fetches",
        "",
        "| URL | HTTP | Seconds | Bytes | Retries |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for page in timing["documentation_pages"]:
        lines.append(
            f"| {page['url']} | {page['http_status']} | {page['elapsed_seconds']} | {page['body_bytes']} | {page['retries']} |"
        )
    lines.extend(
        [
            "",
            "## Data requests",
            "",
            "| Source | Kind | Sent | HTTP | Seconds | Bytes | Rows |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in timing["data_requests"]:
        lines.append(
            f"| {item['source']} | {item['kind']} | {str(item['sent']).lower()} | {item['http_status']} | "
            f"{item['elapsed_seconds']} | {item['body_bytes']} | {item['rows']} |"
        )
    pytest_result = timing.get("pytest")
    lines.extend(["", "## pytest", ""])
    if pytest_result is None:
        lines.append("The full backend suite had not been recorded in this file yet.")
    else:
        lines.append(
            f"Exit code {pytest_result['exit_code']}. Collected {pytest_result.get('collected')}. "
            f"Wall {pytest_result.get('wall_clock_seconds')} seconds. Interpreter `{pytest_result.get('executable')}`."
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record the 7 July 2024 FIRMS area-API provenance check.")
    parser.parse_args(argv)
    report = run()
    timing = json.loads(TIMING_JSON.read_text(encoding="utf-8"))
    TIMING_MD.write_text(render_timing_markdown(timing), encoding="utf-8")
    print(
        f"result={report['result']} authenticated_requests_sent={str(report['authenticated_requests_sent']).lower()} "
        f"processing_stream={report['processing_stream']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
