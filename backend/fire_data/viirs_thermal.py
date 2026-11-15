"""Compare 7 July 2024 VIIRS archive and area-API thermal columns without renaming them.

Archive headers store ``brightness`` and ``bright_t31``. Area-API headers store
``bright_ti4`` and ``bright_ti5``. This module reads the official wording that
defines those names, then compares the stored numbers on rows that already share
the non-thermal columns. It does not rename a column, apply a scale, or fit a
coefficient. ``same_fire`` stays ``not_assessed``.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import perf_counter, process_time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fire_data.firms_api import (
    ARCHIVES,
    AREA_PAGE,
    AREA_TEMPLATE,
    INGESTION_MANIFEST,
    TARGET_DAY,
    USER_AGENT,
    FirmsApiError,
    _call,
    _decimal_key,
    _header_map,
    _load_rows,
    _monthly_check,
    credential_status,
    fetch_public,
    load_map_key,
    measure_archive,
    parse_fire_csv,
    peak_working_set,
    python_environment,
    redact,
    redacted_area_url,
    sha256_bytes,
    sha256_file,
    utc_now,
)

REPORT_JSON = Path(__file__).resolve().parents[1] / "reports" / "viirs_thermal_field_mapping_2024_07_07.json"
REPORT_MD = Path(__file__).resolve().parents[1] / "reports" / "viirs_thermal_field_mapping_2024_07_07.md"

VIIRS_ATTRIBUTE_PAGE = "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html"
MODIS_ATTRIBUTE_PAGE = "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html"
EARTHDATA_ATTRIBUTES_PAGE = "https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs"
USER_GUIDE_PDF = "https://www.earthdata.nasa.gov/s3fs-public/2025-06/VIIRS_C2_AF-375m_User_Guide_1.2.pdf"
VJ114IMG_PAGE = "https://www.earthdata.nasa.gov/data/catalog/lpcloud-vj114img-002"
VJ214IMG_PAGE = "https://www.earthdata.nasa.gov/data/catalog/lpcloud-vj214img-002"

IDENTITY_FIELDS = ("latitude", "longitude", "acq_date", "acq_time", "satellite")
OBSERVATION_FIELDS = (
    "latitude",
    "longitude",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "frp",
    "daynight",
    "type",
)
CANDIDATE_PAIRS = (
    ("brightness", "bright_ti4"),
    ("bright_t31", "bright_ti5"),
)
CONTROL_PAIRS = (
    ("brightness", "bright_ti5"),
    ("bright_t31", "bright_ti4"),
)
QUANTILE_PROBABILITIES = (
    Decimal("0"),
    Decimal("0.25"),
    Decimal("0.5"),
    Decimal("0.75"),
    Decimal("0.95"),
    Decimal("0.99"),
    Decimal("1"),
)

CONFIRMED = "confirmed_equivalent_fields_and_matching_observations"
UNRESOLVED = "same_observations_field_equivalence_unresolved"
DIFFERENT = "different_product_or_processing_stream"
INSUFFICIENT = "insufficient_evidence"

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text).lower()


def _plain(text: str) -> str:
    stripped = re.sub(r"</?[A-Za-z][^>]*>", " ", text)
    stripped = stripped.replace("μ", "µ").replace("\u00b5", "µ")
    return _norm(stripped)


def _phrase_near(text: str, left: str, right: str, window: int = 220) -> bool:
    start = 0
    while True:
        found = text.find(left, start)
        if found < 0:
            return False
        if right in text[found : found + window] or right in text[max(0, found - window) : found + len(left)]:
            return True
        start = found + len(left)


def extract_viirs_attribute_statements(text: str) -> dict[str, object]:
    """Read VIIRS thermal wording that is present in the retrieved page text."""

    norm = _plain(text)
    i4_alias = "bright_ti4 / brightness (in web services)" in norm
    i5_alias = "bright_ti5 / brightness_2 (in web services)" in norm
    i4_kelvin = "i-4 channel brightness temperature of the fire pixel measured in kelvin" in norm
    i5_kelvin = "i-5 channel brightness temperature of the fire pixel measured in kelvin" in norm
    wavelength = None
    for token in ("3.55-3.93 µm", "3.55-3.93 μm", "3.55–3.93 µm", "3.55–3.93 μm"):
        if token in norm:
            wavelength = token
            break
    return {
        "bright_ti4_present": "bright_ti4" in norm,
        "bright_ti5_present": "bright_ti5" in norm,
        "brightness_web_service_alias_of_bright_ti4": i4_alias,
        "brightness_2_web_service_alias_of_bright_ti5": i5_alias,
        "i4_brightness_temperature_kelvin": i4_kelvin,
        "i5_brightness_temperature_kelvin": i5_kelvin,
        "i4_wavelength_on_page": wavelength,
        "i4_called_mid_infrared": "mid-infrared" in norm and "i4" in norm,
        "bright_t31_present": "bright_t31" in norm,
        "bright_t31_named_beside_i5": _phrase_near(norm, "bright_t31", "i-5") or _phrase_near(norm, "bright_t31", "bright_ti5"),
        "scale_factor_mentioned": "scale factor" in norm or "scale_factor" in norm,
        "archive_download_equated_to_area_api": "archive download" in norm and "area api" in norm,
    }


def extract_modis_bright_t31_statement(text: str) -> dict[str, object]:
    """Record the MODIS definition of bright_t31. It is not applied to VIIRS."""

    norm = _plain(text)
    return {
        "bright_t31_present": "bright_t31" in norm,
        "channel_31_kelvin": "channel 31 brightness temperature of the fire pixel measured in kelvin" in norm,
        "applied_to_viirs_archive": False,
    }


def extract_user_guide_statements(text: str) -> dict[str, object]:
    """Record Collection 2 location-product wording. Those column names stay distinct."""

    norm = _plain(text)
    return {
        "fp_t4_i4_kelvin": "fp_t4" in norm and "fire pixel i4 brightness temperature" in norm and "kelvin" in norm,
        "fp_t5_i5_kelvin": "fp_t5" in norm and "fire pixel i5 brightness temperature" in norm and "kelvin" in norm,
        "monthly_t4_i4_kelvin": "fire pixel brightness temperature on channel i4 (k)" in norm,
        "monthly_t5_i5_kelvin": "fire pixel brightness temperature on channel i5 (k)" in norm,
        "i5_called_long_wave_infrared": "long-wave infrared (channel i5)" in norm or "long-wave infrared (channel i5)" in norm,
        "i4_nominal_saturation_367k": "nominal saturation temperature of 367 k" in norm,
        "monthly_columns_include_brightness": "brightness" in norm and "bright_t31" in norm,
        "guide_names_firms_archive_columns": "bright_ti4" in norm or "bright_t31" in norm,
        "scale_factor_mentioned": "scale factor" in norm,
    }


def fetch_binary(url: str, *, timeout: float = 120) -> dict[str, object]:
    """GET a documentation file and keep the response bytes. No map key is added."""

    if "MAP_KEY" in url or "[MAP_KEY]" in url:
        raise FirmsApiError("A documentation fetch does not carry a MAP_KEY")
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
            attempts.append(
                {
                    "attempt": attempt,
                    "url": url,
                    "http_status": status,
                    "elapsed_seconds": round(elapsed, 6),
                    "body_bytes": len(body),
                    "retrieved_at": utc_now(),
                }
            )
            return {
                "url": url,
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
        except HTTPError as error:
            body = error.read()
            elapsed = perf_counter() - attempt_started
            status = int(error.code)
            attempts.append(
                {
                    "attempt": attempt,
                    "url": url,
                    "http_status": status,
                    "elapsed_seconds": round(elapsed, 6),
                    "body_bytes": len(body),
                    "retrieved_at": utc_now(),
                }
            )
            if status < 500 or attempt == 2:
                return {
                    "url": url,
                    "http_status": status,
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
            elapsed = perf_counter() - attempt_started
            last_error = str(getattr(error, "reason", error))
            attempts.append(
                {
                    "attempt": attempt,
                    "url": url,
                    "http_status": None,
                    "elapsed_seconds": round(elapsed, 6),
                    "error": last_error,
                    "retrieved_at": utc_now(),
                }
            )
            if attempt == 2:
                break
    raise FirmsApiError(f"Documentation request failed after 2 attempts: {last_error}")


def pdf_text(payload: bytes) -> str:
    """Read a PDF text layer. Custom-encoded glyph streams are not treated as words."""

    if not payload.startswith(b"%PDF"):
        return payload.decode("utf-8", errors="replace")
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(payload))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def extract_level2_temperature_encoding(html: str) -> dict[str, dict[str, str]]:
    """Read FP_T4 and FP_T5 cells from an Earthdata variable table."""

    found: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, re.IGNORECASE | re.DOTALL):
        cells = [
            _WS.sub(" ", re.sub(r"<[^>]+>", " ", cell)).strip()
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", match.group(1), re.IGNORECASE | re.DOTALL)
        ]
        if not cells or cells[0] not in {"FP_T4", "FP_T5"} or len(cells) < 8:
            continue
        found[cells[0]] = {
            "description": cells[1],
            "units": cells[2],
            "data_type": cells[3],
            "fill_value": cells[4],
            "valid_range": cells[5],
            "scale_factor": cells[6],
            "offset": cells[7],
        }
    return found


def _parse_kelvin(raw: str) -> tuple[str, Decimal | None]:
    text = raw.strip()
    if text == "":
        return "missing", None
    try:
        return "numeric", Decimal(text)
    except InvalidOperation:
        return "invalid", None


def quantile_type7(values: list[Decimal], probability: Decimal) -> Decimal | None:
    """Hyndman-Fan type 7 quantile. The sample is sorted here."""

    if probability < 0 or probability > 1:
        raise ValueError("A quantile probability is between 0 and 1")
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = Decimal(len(ordered) - 1) * probability
    lower = int(position)
    if lower >= len(ordered) - 1:
        return ordered[-1]
    fraction = position - Decimal(lower)
    return ordered[lower] + (ordered[lower + 1] - ordered[lower]) * fraction


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    rendered = format(value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _observation_fields(archive_header: list[str], api_header: list[str]) -> list[str]:
    archive_set = set(archive_header)
    api_set = set(api_header)
    return [field for field in OBSERVATION_FIELDS if field in archive_set and field in api_set]


def _group(rows: list[dict[str, str]], fields: list[str]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for row in rows:
        key = tuple(_decimal_key(field, row.get(field, "")) for field in fields)
        grouped.setdefault(key, []).append(row)
    return grouped


def _pair_status(archive_raw: str, api_raw: str) -> tuple[str, Decimal | None]:
    archive_state, archive_value = _parse_kelvin(archive_raw)
    api_state, api_value = _parse_kelvin(api_raw)
    if archive_state == "missing" or api_state == "missing":
        return "missing", None
    if archive_state == "invalid" or api_state == "invalid":
        return "invalid", None
    assert archive_value is not None and api_value is not None
    return "numeric", api_value - archive_value


def _summarize_differences(differences: list[Decimal], exact: int, counts: dict[str, int]) -> dict[str, object]:
    absolute = [abs(value) for value in differences]
    distinct = Counter(differences)
    if not differences:
        offset = "not_computed"
    elif all(value == 0 for value in differences):
        offset = "none_observed"
    elif len(distinct) == 1:
        offset = "constant_difference_observed"
    else:
        offset = "not_a_single_constant"
    mean_signed = None
    mean_absolute = None
    if differences:
        total = sum(differences, Decimal(0))
        mean_signed = total / Decimal(len(differences))
        mean_absolute = sum(absolute, Decimal(0)) / Decimal(len(absolute))
    distinct_report: list[str] | None
    if len(distinct) <= 5:
        distinct_report = [_decimal_text(value) or "0" for value, _count in sorted(distinct.items())]
    else:
        distinct_report = None
    return {
        "numeric_pairs": len(differences),
        "exact_numeric_equality": exact,
        "maximum_absolute_difference": _decimal_text(max(absolute) if absolute else None),
        "mean_signed_difference_api_minus_archive": _decimal_text(mean_signed),
        "mean_absolute_difference": _decimal_text(mean_absolute),
        "signed_difference_quantiles_type7": {
            format(probability, "f"): _decimal_text(quantile_type7(differences, probability))
            for probability in QUANTILE_PROBABILITIES
        },
        "absolute_difference_quantiles_type7": {
            format(probability, "f"): _decimal_text(quantile_type7(absolute, probability))
            for probability in QUANTILE_PROBABILITIES
        },
        "distinct_signed_differences": len(distinct) if differences else 0,
        "signed_differences_when_few": distinct_report,
        "systematic_offset": offset,
        "scale_or_other_transformation": "not_calculated",
        "harmonization_coefficient_calculated": False,
        **counts,
    }


def _joint_thermal(rows: list[dict[str, str]], side: str) -> Counter[tuple[str, ...]]:
    if side == "archive":
        return Counter(tuple(row.get(field, "").strip() for field, _api in CANDIDATE_PAIRS) for row in rows)
    return Counter(tuple(row.get(field, "").strip() for _archive, field in CANDIDATE_PAIRS) for row in rows)


def _column_counts(
    pairs: list[tuple[dict[str, str], dict[str, str]]],
    archive_field: str,
    api_field: str,
) -> tuple[list[Decimal], int, int, dict[str, int]]:
    differences: list[Decimal] = []
    exact = 0
    raw_exact = 0
    counts = {
        "missing_archive": 0,
        "missing_api": 0,
        "missing_both": 0,
        "invalid_archive": 0,
        "invalid_api": 0,
        "invalid_rows": 0,
    }
    for archive_row, api_row in pairs:
        archive_raw = archive_row.get(archive_field, "")
        api_raw = api_row.get(api_field, "")
        if archive_raw.strip() == api_raw.strip():
            raw_exact += 1
        archive_state, _archive_value = _parse_kelvin(archive_raw)
        api_state, _api_value = _parse_kelvin(api_raw)
        if archive_state == "missing" and api_state == "missing":
            counts["missing_both"] += 1
        if archive_state == "missing":
            counts["missing_archive"] += 1
        if api_state == "missing":
            counts["missing_api"] += 1
        if archive_state == "invalid":
            counts["invalid_archive"] += 1
        if api_state == "invalid":
            counts["invalid_api"] += 1
        status, difference = _pair_status(archive_raw, api_raw)
        if status == "numeric" and difference is not None:
            differences.append(difference)
            if difference == 0:
                exact += 1
        elif status == "invalid":
            counts["invalid_rows"] += 1
    return differences, exact, raw_exact, counts


def compare_thermal_tables(
    archive_header: list[str],
    archive_rows: list[dict[str, str]],
    api_header: list[str],
    api_rows: list[dict[str, str]],
) -> dict[str, object]:
    """Pair rows on shared non-thermal columns and compare thermal candidates in place."""

    observation = _observation_fields(archive_header, api_header)
    missing_identity = [field for field in IDENTITY_FIELDS if field not in observation]
    result: dict[str, object] = {
        "fields_renamed": False,
        "observation_fields": observation,
        "candidate_pairs": [{"archive_field": left, "api_field": right} for left, right in CANDIDATE_PAIRS],
        "archive_rows": len(archive_rows),
        "api_rows": len(api_rows),
        "same_fire": "not_assessed",
        "harmonization_coefficient_calculated": False,
    }
    if missing_identity:
        result.update(
            {
                "alignment": "not_performed",
                "reason": "Identity fields are missing from one of the headers.",
                "pairs": [],
                "controls": [],
            }
        )
        return result

    archive_groups = _group(archive_rows, observation)
    api_groups = _group(api_rows, observation)
    unique_pairs: list[tuple[dict[str, str], dict[str, str]]] = []
    matched_duplicate_groups: list[tuple[list[dict[str, str]], list[dict[str, str]]]] = []
    unaligned_archive = 0
    unaligned_api = 0
    for key in set(archive_groups) | set(api_groups):
        left = archive_groups.get(key, [])
        right = api_groups.get(key, [])
        if not left:
            unaligned_api += len(right)
            continue
        if not right:
            unaligned_archive += len(left)
            continue
        if len(left) == 1 and len(right) == 1:
            unique_pairs.append((left[0], right[0]))
            continue
        if len(left) == len(right) and _joint_thermal(left, "archive") == _joint_thermal(right, "api"):
            matched_duplicate_groups.append((left, right))
            continue
        unaligned_archive += len(left)
        unaligned_api += len(right)

    duplicate_rows = sum(len(left) for left, _right in matched_duplicate_groups)
    paired_rows = len(unique_pairs) + duplicate_rows

    def one_pair(archive_field: str, api_field: str, include_distribution: bool) -> dict[str, object]:
        present = archive_field in archive_header and api_field in api_header
        item: dict[str, object] = {
            "archive_field": archive_field,
            "api_field": api_field,
            "fields_present": present,
            "fields_renamed": False,
        }
        if not present:
            item["reason"] = "One of the named columns is absent. No substitute column was used."
            return item
        differences, exact, raw_exact, counts = _column_counts(unique_pairs, archive_field, api_field)
        if include_distribution:
            for left, _right in matched_duplicate_groups:
                copies = len(left)
                differences.extend([Decimal(0)] * copies)
                exact += copies
                raw_exact += copies
        else:
            for left, right in matched_duplicate_groups:
                left_values = Counter(row.get(archive_field, "").strip() for row in left)
                right_values = Counter(row.get(api_field, "").strip() for row in right)
                if left_values == right_values:
                    copies = len(left)
                    exact += copies
                    raw_exact += copies
                    differences.extend([Decimal(0)] * copies)
        item["raw_string_equality"] = raw_exact
        item["paired_rows"] = paired_rows
        if include_distribution:
            item.update(_summarize_differences(differences, exact, counts))
        else:
            item.update(
                {
                    "exact_numeric_equality": exact,
                    "numeric_pairs": len(differences),
                    "harmonization_coefficient_calculated": False,
                    **counts,
                }
            )
        return item

    result.update(
        {
            "alignment": "performed",
            "aligned_unique_rows": len(unique_pairs),
            "aligned_ambiguous_rows_with_matching_thermal_multiset": duplicate_rows,
            "ambiguous_groups": len(matched_duplicate_groups),
            "unaligned_archive_rows": unaligned_archive,
            "unaligned_api_rows": unaligned_api,
            "observations_aligned": (
                unaligned_archive == 0
                and unaligned_api == 0
                and paired_rows == len(archive_rows) == len(api_rows)
            ),
            "pairs": [one_pair(archive_field, api_field, True) for archive_field, api_field in CANDIDATE_PAIRS],
            "controls": [
                {
                    **one_pair(archive_field, api_field, False),
                    "role": "crossed_control",
                    "documented_alias": False,
                }
                for archive_field, api_field in CONTROL_PAIRS
            ],
            "records_are_unique_fires": False,
        }
    )
    return result


def names_documented(statements: dict[str, object], archive_field: str, api_field: str) -> bool:
    """A name is documented only when the VIIRS attribute page states that alias."""

    if archive_field == "brightness" and api_field == "bright_ti4":
        return bool(
            statements.get("brightness_web_service_alias_of_bright_ti4")
            and statements.get("i4_brightness_temperature_kelvin")
        )
    if archive_field == "bright_t31" and api_field == "bright_ti5":
        return bool(statements.get("bright_t31_named_beside_i5") and statements.get("i5_brightness_temperature_kelvin"))
    return False


def classify_thermal_relationship(
    comparison: dict[str, object] | None,
    statements: dict[str, object] | None,
    *,
    request_ok: bool,
) -> str:
    """Classify one platform. The API source label is not an input and is not used."""

    if not request_ok or comparison is None or statements is None:
        return INSUFFICIENT
    if comparison.get("alignment") != "performed":
        return INSUFFICIENT
    if not comparison.get("observations_aligned"):
        return INSUFFICIENT
    pairs = comparison.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != 2:
        return INSUFFICIENT
    documented = []
    values_match = []
    for pair in pairs:
        if not isinstance(pair, dict) or not pair.get("fields_present"):
            return INSUFFICIENT
        numeric = int(pair.get("numeric_pairs") or 0)
        exact = int(pair.get("exact_numeric_equality") or 0)
        paired = int(pair.get("paired_rows") or 0)
        missing = int(pair.get("missing_archive") or 0) + int(pair.get("missing_api") or 0)
        invalid = int(pair.get("invalid_rows") or 0)
        clean = numeric == paired and exact == paired and missing == 0 and invalid == 0 and paired > 0
        values_match.append(clean)
        documented.append(
            names_documented(statements, str(pair.get("archive_field")), str(pair.get("api_field")))
        )
    if all(values_match) and all(documented):
        return CONFIRMED
    if statements.get("archive_and_area_are_different_products") and not all(values_match):
        return DIFFERENT
    if comparison.get("observations_aligned"):
        return UNRESOLVED
    return INSUFFICIENT


def semantics_support_comparison(statements: dict[str, object]) -> bool:
    """The area request is sent only after the API thermal fields are defined in Kelvin."""

    return bool(
        statements.get("i4_brightness_temperature_kelvin")
        and statements.get("i5_brightness_temperature_kelvin")
        and statements.get("bright_ti4_present")
        and statements.get("bright_ti5_present")
    )


def _page_record(fetched: dict[str, object] | None, error: str | None = None) -> dict[str, object]:
    if fetched is None:
        return {"retrieved": False, "error": error}
    text = str(fetched.get("body_text") or "")
    return {
        "url": fetched.get("url"),
        "http_status": fetched.get("http_status"),
        "body_bytes": fetched.get("body_bytes"),
        "sha256": fetched.get("sha256"),
        "elapsed_seconds": fetched.get("elapsed_seconds"),
        "retries": fetched.get("retries"),
        "retrieved_at": fetched.get("retrieved_at"),
        "retrieved": fetched.get("http_status") == 200 and bool(text),
    }


def _json_ready(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    return value


def render_markdown(report: dict[str, object]) -> str:
    timing = report["timing"]
    docs = report["documentation"]
    lines = [
        "# VIIRS thermal field mapping, 7 July 2024",
        "",
        f"Created {report['created_at']}. Finished {report['finished_at']}.",
        "",
        "The MAP_KEY is not in this file. Archive columns were not renamed. "
        "No scale was applied. No harmonization coefficient was calculated. "
        "`same_fire` is `not_assessed`. The processing stream of each local archive stays `unresolved`.",
        "",
        "## Documented meaning",
        "",
        "Retrieved pages are listed with hashes in the JSON report. The sentences below are phrases found in those responses.",
        "",
    ]
    refresh = report.get("documentation_text_refresh")
    if isinstance(refresh, dict):
        lines.append(
            f"The user's guide text layer was read at `{refresh.get('retrieved_at')}` "
            f"from SHA-256 `{refresh.get('user_guide_sha256')}`. "
            f"It matches the comparison-pass hash: `{str(refresh.get('user_guide_sha256') == refresh.get('previous_user_guide_sha256')).lower()}`. "
            "Area requests were not repeated for that reading."
        )
        lines.append("")
    attribute = docs["viirs_attribute_page"]
    statements = attribute.get("statements") or {}
    lines.append(
        f"FIRMS VIIRS attribute page: `{attribute.get('url')}` HTTP `{attribute.get('http_status')}` "
        f"on `{attribute.get('retrieved_at')}`."
    )
    lines.append(
        f"I-4 Kelvin statement present: `{str(statements.get('i4_brightness_temperature_kelvin')).lower()}`. "
        f"Web-service alias `Bright_ti4 / Brightness (in web services)` present: "
        f"`{str(statements.get('brightness_web_service_alias_of_bright_ti4')).lower()}`."
    )
    lines.append(
        f"I-5 Kelvin statement present: `{str(statements.get('i5_brightness_temperature_kelvin')).lower()}`. "
        f"Web-service alias `Bright_ti5 / Brightness_2 (in web services)` present: "
        f"`{str(statements.get('brightness_2_web_service_alias_of_bright_ti5')).lower()}`."
    )
    lines.append(
        f"I-4 wavelength phrase on that page: `{statements.get('i4_wavelength_on_page')}`. "
        f"`bright_t31` occurs on that page: `{str(statements.get('bright_t31_present')).lower()}`. "
        f"`bright_t31` is named beside I-5: `{str(statements.get('bright_t31_named_beside_i5')).lower()}`. "
        f"A scale factor is mentioned: `{str(statements.get('scale_factor_mentioned')).lower()}`."
    )
    lines.append("")
    modis = docs["modis_attribute_page"]
    modis_statements = modis.get("statements") or {}
    lines.append(
        f"FIRMS MODIS attribute page: `{modis.get('url')}` HTTP `{modis.get('http_status')}`. "
        f"`bright_t31` present: `{str(modis_statements.get('bright_t31_present')).lower()}`. "
        f"Channel 31 Kelvin statement present: `{str(modis_statements.get('channel_31_kelvin')).lower()}`. "
        "That MODIS sentence is not applied to the VIIRS archive."
    )
    earthdata = docs.get("earthdata_attributes_page") or {}
    earth_statements = earthdata.get("statements") or {}
    lines.extend(
        [
            "",
            f"Earthdata active-fire attribute page: `{earthdata.get('url')}` HTTP `{earthdata.get('http_status')}`. "
            f"I-4 Kelvin statement present: `{str(earth_statements.get('i4_brightness_temperature_kelvin')).lower()}`. "
            f"I-5 Kelvin statement present: `{str(earth_statements.get('i5_brightness_temperature_kelvin')).lower()}`. "
            f"Web-service aliases present: `{str(earth_statements.get('brightness_web_service_alias_of_bright_ti4')).lower()}` "
            f"and `{str(earth_statements.get('brightness_2_web_service_alias_of_bright_ti5')).lower()}`. "
            f"`bright_t31` named beside I-5: `{str(earth_statements.get('bright_t31_named_beside_i5')).lower()}`.",
        ]
    )
    guide = docs["user_guide"]
    guide_statements = guide.get("statements") or {}
    lines.extend(
        [
            "",
            f"Collection 2 375 m user's guide, Version 1.2, June 2025: `{guide.get('url')}` "
            f"HTTP `{guide.get('http_status')}`, `{guide.get('body_bytes')}` bytes, SHA-256 `{guide.get('sha256')}`.",
            f"Level-2 `FP_T4` is I4 brightness temperature in kelvin: `{str(guide_statements.get('fp_t4_i4_kelvin')).lower()}`. "
            f"`FP_T5` is I5 brightness temperature in kelvin: `{str(guide_statements.get('fp_t5_i5_kelvin')).lower()}`.",
            f"Monthly location fields `T4` and `T5` are I4 and I5 brightness temperature in K: "
            f"`{str(guide_statements.get('monthly_t4_i4_kelvin')).lower()}` and "
            f"`{str(guide_statements.get('monthly_t5_i5_kelvin')).lower()}`.",
            f"The guide calls I5 long-wave infrared: `{str(guide_statements.get('i5_called_long_wave_infrared')).lower()}`. "
            f"Nominal I4 saturation 367 K: `{str(guide_statements.get('i4_nominal_saturation_367k')).lower()}`. "
            f"The guide names the FIRMS archive columns: `{str(guide_statements.get('guide_names_firms_archive_columns')).lower()}`. "
            f"A scale factor is mentioned: `{str(guide_statements.get('scale_factor_mentioned')).lower()}`.",
            "",
            "The user's guide monthly file uses `T4` and `T5`. The Level-2 swath uses `FP_T4` and `FP_T5`. "
            "The FIRMS archive CSV uses `brightness` and `bright_t31`. The area API CSV uses `bright_ti4` and `bright_ti5`. "
            "The attribute page's web-service names are `Brightness` and `Brightness_2`. "
            "These are separate names. This comparison does not treat them as one schema.",
            "",
            "Level-2 catalog pages were retrieved for the scale-factor cells of `FP_T4` and `FP_T5`. "
            "Those cells belong to the swath product. They are not a FIRMS CSV scale.",
            "",
        ]
    )
    for catalog in docs.get("level2_catalogs") or []:
        encoding = catalog.get("temperature_encoding") or {}
        lines.append(
            f"- `{catalog.get('url')}` HTTP `{catalog.get('http_status')}` bytes `{catalog.get('body_bytes')}`."
        )
        for name in ("FP_T4", "FP_T5"):
            row = encoding.get(name) or {}
            if not row:
                lines.append(f"  `{name}` row was not found in the variable table.")
                continue
            lines.append(
                f"  `{name}`: {row.get('description')}. Units `{row.get('units')}`, "
                f"type `{row.get('data_type')}`, fill `{row.get('fill_value')}`, "
                f"range `{row.get('valid_range')}`, scale factor `{row.get('scale_factor')}`, "
                f"offset `{row.get('offset')}`."
            )
    lines.extend(
        [
            "",
            "## Comparison",
            "",
            "Candidate pairs are `brightness` with `bright_ti4`, and `bright_t31` with `bright_ti5`. "
            "Rows are paired on the shared non-thermal columns. Difference is API minus archive, in the stored numeric units. "
            "Quantiles use Hyndman-Fan type 7. Crossed pairs are a control and are not a mapping.",
            "",
            f"Authenticated area requests sent: `{str(report['authenticated_requests_sent']).lower()}`.",
            f"Reason the requests were or were not sent: {report['request_gate']}",
            "",
        ]
    )
    for platform in report["platforms"]:
        lines.extend(
            [
                f"### {platform['platform']}",
                "",
                f"File `{platform['filename']}` SHA-256 before `{platform['sha256_before']}`. "
                f"SHA-256 after `{platform['sha256_after']}`. Unchanged: `{str(platform['sha256_before'] == platform['sha256_after']).lower()}`.",
                f"API source label recorded beside the file: `{platform['api_source_label']}`. "
                "That label is not a processing-stream assignment.",
                f"Thermal relationship: `{platform['thermal_relationship']}`.",
                f"Processing stream: `{platform['processing_stream']}`. Product equivalence: `{platform['product_equivalence']}`. "
                f"`same_fire`: `{platform['same_fire']}`.",
                "",
            ]
        )
        request = platform.get("request") or {}
        lines.append(
            f"Area request sent `{str(request.get('sent')).lower()}` HTTP `{request.get('http_status')}` "
            f"rows `{request.get('rows')}` bytes `{request.get('body_bytes')}` "
            f"seconds `{request.get('elapsed_seconds')}` retries `{request.get('retries')}`."
        )
        comparison = platform.get("comparison") or {}
        if comparison:
            lines.append(
                f"Archive rows `{comparison.get('archive_rows')}`. API rows `{comparison.get('api_rows')}`. "
                f"Aligned unique rows `{comparison.get('aligned_unique_rows')}`. "
                f"Ambiguous rows whose joint thermal multiset matched `{comparison.get('aligned_ambiguous_rows_with_matching_thermal_multiset')}`. "
                f"Unaligned archive rows `{comparison.get('unaligned_archive_rows')}`. "
                f"Unaligned API rows `{comparison.get('unaligned_api_rows')}`."
            )
            for pair in comparison.get("pairs") or []:
                lines.append(
                    f"`{pair.get('archive_field')}` versus `{pair.get('api_field')}`: "
                    f"name documented `{str(pair.get('name_documented')).lower()}`, "
                    f"exact numeric equality `{pair.get('exact_numeric_equality')}`, "
                    f"raw string equality `{pair.get('raw_string_equality')}`, "
                    f"numeric pairs `{pair.get('numeric_pairs')}`, "
                    f"maximum absolute difference `{pair.get('maximum_absolute_difference')}`, "
                    f"mean absolute difference `{pair.get('mean_absolute_difference')}`, "
                    f"mean signed difference `{pair.get('mean_signed_difference_api_minus_archive')}`, "
                    f"offset `{pair.get('systematic_offset')}`, "
                    f"missing archive/api/both `{pair.get('missing_archive')}`/`{pair.get('missing_api')}`/`{pair.get('missing_both')}`, "
                    f"invalid archive/api `{pair.get('invalid_archive')}`/`{pair.get('invalid_api')}`."
                )
                quantiles = pair.get("absolute_difference_quantiles_type7")
                if quantiles:
                    lines.append(f"Absolute-difference quantiles: `{quantiles}`.")
            for control in comparison.get("controls") or []:
                lines.append(
                    f"Crossed control `{control.get('archive_field')}` versus `{control.get('api_field')}`: "
                    f"exact numeric equality `{control.get('exact_numeric_equality')}` of `{control.get('numeric_pairs')}` numeric pairs. "
                    "This control is not a field mapping."
                )
        lines.append("")
    lines.extend(["## Checksums", ""])
    for item in report["monthly_checksums"]:
        lines.append(
            f"- `{item['filename']}` SHA-256 `{item['sha256']}` matches the ingestion manifest: "
            f"`{str(item['matches_ingestion_manifest']).lower()}`."
        )
    lines.extend(
        [
            "",
            "## Timing",
            "",
            f"Wall clock: {timing['wall_clock_seconds']} seconds.",
            f"CPU seconds: {timing['cpu_seconds']}.",
            f"Peak working set: {timing['peak_working_set_bytes']} bytes."
            if timing.get("peak_working_set_bytes") is not None
            else "Peak working set was not measured.",
            f"Authenticated data-request retries: {timing['authenticated_retries']}.",
            f"Cancellations: {timing['cancellations']}.",
            f"Documentation bytes: {timing['documentation_bytes']}. Area-response bytes: {timing['area_response_bytes']}.",
            "",
        ]
    )
    pytest_result = timing.get("pytest")
    if isinstance(pytest_result, dict):
        lines.append(
            f"Pytest exit code {pytest_result.get('exit_code')}. Passed {pytest_result.get('passed')}. "
            f"Failed {pytest_result.get('failed')}. Pytest reported {pytest_result.get('pytest_reported_seconds')} seconds. "
            f"The command stopwatch was {pytest_result.get('command_stopwatch_seconds')} seconds. "
            f"Interpreter: `{pytest_result.get('executable')}`."
        )
        lines.append("")
    lines.extend(
        [
            "Original day files and monthly files were read and hashed. They were not rewritten.",
            "",
        ]
    )
    return "\n".join(lines)


def _catalog_facts(fetched: dict[str, object]) -> dict[str, object]:
    html = str(fetched.get("body_text") or "")
    text = _plain(html)
    record = _page_record(fetched)
    record["mentions_fp_t4"] = "fp_t4" in text
    record["mentions_fp_t5"] = "fp_t5" in text
    record["mentions_kelvin"] = "kelvin" in text
    record["temperature_encoding"] = extract_level2_temperature_encoding(html)
    return record


def run(environ: dict[str, str] | None = None) -> dict[str, object]:
    """Fetch the field definitions, then the two 7 July area tables if those definitions are present."""

    started = perf_counter()
    cpu_started = process_time()
    created_at = utc_now()
    key, _source = load_map_key(environ)
    credential = credential_status(environ)
    pages: dict[str, dict[str, object]] = {}
    page_errors = []
    for url in (
        VIIRS_ATTRIBUTE_PAGE,
        MODIS_ATTRIBUTE_PAGE,
        EARTHDATA_ATTRIBUTES_PAGE,
        AREA_PAGE,
        VJ114IMG_PAGE,
        VJ214IMG_PAGE,
    ):
        try:
            pages[url] = fetch_public(url, timeout=120)
        except FirmsApiError as error:
            page_errors.append({"url": url, "error": str(error)})
    try:
        guide_binary = fetch_binary(USER_GUIDE_PDF)
    except FirmsApiError as error:
        page_errors.append({"url": USER_GUIDE_PDF, "error": str(error)})
        guide_binary = None
    if guide_binary is not None:
        body = guide_binary.get("body")
        text = pdf_text(body) if isinstance(body, bytes) else ""
        pages[USER_GUIDE_PDF] = {key_name: value for key_name, value in guide_binary.items() if key_name != "body"}
        pages[USER_GUIDE_PDF]["body_text"] = text

    attribute_fetch = pages.get(VIIRS_ATTRIBUTE_PAGE)
    attribute_record = _page_record(attribute_fetch)
    attribute_text = str(attribute_fetch.get("body_text") or "") if attribute_fetch else ""
    statements = extract_viirs_attribute_statements(attribute_text) if attribute_record.get("retrieved") else {}
    attribute_record["statements"] = statements

    modis_fetch = pages.get(MODIS_ATTRIBUTE_PAGE)
    modis_record = _page_record(modis_fetch)
    modis_record["statements"] = extract_modis_bright_t31_statement(str(modis_fetch.get("body_text") or "")) if modis_fetch else {}

    guide_fetch = pages.get(USER_GUIDE_PDF)
    guide_record = _page_record(guide_fetch)
    if guide_fetch and guide_fetch.get("http_status") == 200:
        guide_bytes = str(guide_fetch.get("body_text") or "")
        guide_record["statements"] = extract_user_guide_statements(guide_bytes)
        guide_record["text_extracted"] = bool(
            guide_record["statements"]["fp_t4_i4_kelvin"] and guide_record["statements"]["monthly_t4_i4_kelvin"]
        )
    else:
        guide_record["statements"] = {}
        guide_record["text_extracted"] = False

    earthdata_fetch = pages.get(EARTHDATA_ATTRIBUTES_PAGE)
    earthdata = _page_record(earthdata_fetch)
    earthdata["statements"] = (
        extract_viirs_attribute_statements(str(earthdata_fetch.get("body_text") or "")) if earthdata_fetch else {}
    )
    area_fetch = pages.get(AREA_PAGE)
    area_text = str(area_fetch.get("body_text") or "") if area_fetch else ""
    area_ok = bool(area_fetch and area_fetch.get("http_status") == 200 and AREA_TEMPLATE in area_text)
    sources_ok = "VIIRS_NOAA20_SP" in area_text and "VIIRS_NOAA21_SP" in area_text
    semantics_ok = semantics_support_comparison(statements)
    if key is None:
        gate = "FIRMS_MAP_KEY is not configured. No authenticated URL was opened."
        send = False
    elif not semantics_ok:
        gate = "The VIIRS attribute page did not state both thermal fields as brightness temperature in Kelvin. No area URL was opened."
        send = False
    elif not area_ok or not sources_ok:
        gate = "The live area page did not show the documented template and both source codes. No area URL was opened."
        send = False
    else:
        gate = "The attribute page defines bright_ti4 and bright_ti5 as Kelvin brightness temperatures. The two area requests were sent."
        send = True

    manifest = json.loads(INGESTION_MANIFEST.read_text(encoding="utf-8"))
    platforms = []
    area_bytes = 0
    authenticated_retries = 0
    for spec in ARCHIVES:
        before = sha256_file(spec["path"])
        measured = measure_archive(spec["path"])
        request_record: dict[str, object] = {
            "url": redacted_area_url(spec["api_source"], str(measured["observed_bbox"]), TARGET_DAY, 1),
            "sent": False,
            "http_status": None,
            "rows": None,
            "body_bytes": None,
            "elapsed_seconds": None,
            "retries": 0,
            "sha256": None,
            "kind": "area",
            "source": spec["api_source"],
        }
        comparison = None
        relationship = INSUFFICIENT
        if send and key is not None:
            called = _call(str(request_record["url"]), key, "area")
            request_record.update(
                {
                    "sent": called.get("sent"),
                    "http_status": called.get("http_status"),
                    "body_bytes": called.get("body_bytes"),
                    "elapsed_seconds": called.get("elapsed_seconds"),
                    "retries": called.get("retries"),
                    "sha256": called.get("sha256"),
                    "attempts": called.get("attempts"),
                }
            )
            authenticated_retries += int(called.get("retries") or 0)
            area_bytes += int(called.get("body_bytes") or 0)
            text = called.get("text")
            if called.get("http_status") == 200 and isinstance(text, str):
                header, rows, parsed = parse_fire_csv(text)
                request_record["rows"] = parsed["rows"]
                request_record["header"] = header
                request_record["parse"] = {key_name: value for key_name, value in parsed.items() if key_name != "body_prefix"}
                if parsed["parsed_as_fire_table"]:
                    archive_rows = _load_rows(spec["path"])
                    comparison = compare_thermal_tables(list(measured["header"]), archive_rows, header, rows)
                    for pair in comparison["pairs"]:
                        pair["name_documented"] = names_documented(
                            statements, str(pair["archive_field"]), str(pair["api_field"])
                        )
                    relationship = classify_thermal_relationship(comparison, statements, request_ok=True)
                else:
                    relationship = INSUFFICIENT
            else:
                relationship = INSUFFICIENT
            if isinstance(text, str) and key in text:
                request_record["body_contained_key_and_was_discarded"] = True
        after = sha256_file(spec["path"])
        monthly = _monthly_check(spec, manifest)
        platforms.append(
            {
                "platform": spec["platform"],
                "filename": spec["path"].name,
                "sha256_before": before,
                "sha256_after": after,
                "bytes": measured["bytes"],
                "rows": measured["rows"],
                "header": measured["header"],
                "api_source_label": spec["api_source"],
                "api_source_is_not_a_processing_stream_assignment": True,
                "processing_stream": "unresolved",
                "product_equivalence": "not_assessed",
                "same_fire": "not_assessed",
                "thermal_relationship": relationship,
                "fields_renamed": False,
                "harmonization_coefficient_calculated": False,
                "request": request_record,
                "comparison": comparison,
            }
        )
        platforms[-1]["monthly"] = {
            "filename": monthly["filename"],
            "sha256": monthly["sha256"],
            "matches_ingestion_manifest": monthly["matches_ingestion_manifest"],
        }

    finished = utc_now()
    documentation_bytes = sum(int(page.get("body_bytes") or 0) for page in pages.values())
    timing = {
        "wall_clock_seconds": round(perf_counter() - started, 6),
        "cpu_seconds": round(process_time() - cpu_started, 6),
        "peak_working_set_bytes": peak_working_set(),
        "authenticated_retries": authenticated_retries,
        "cancellations": 0,
        "documentation_bytes": documentation_bytes,
        "area_response_bytes": area_bytes,
        "python": python_environment(),
    }
    report: dict[str, object] = {
        "milestone": "13b",
        "created_at": created_at,
        "finished_at": finished,
        "target_day": TARGET_DAY,
        "credential": credential,
        "authenticated_requests_sent": send,
        "request_gate": gate,
        "documentation_errors": page_errors,
        "documentation": {
            "viirs_attribute_page": attribute_record,
            "modis_attribute_page": modis_record,
            "earthdata_attributes_page": earthdata,
            "area_page": {
                **_page_record(area_fetch),
                "template_present": area_ok,
                "target_sources_present": sources_ok,
            },
            "user_guide": guide_record,
            "level2_catalogs": [
                _catalog_facts(pages[url]) for url in (VJ114IMG_PAGE, VJ214IMG_PAGE) if url in pages
            ],
        },
        "platforms": platforms,
        "monthly_checksums": [item["monthly"] for item in platforms],
        "original_day_files_unchanged": all(item["sha256_before"] == item["sha256_after"] for item in platforms),
        "timing": timing,
        "same_fire": "not_assessed",
        "processing_stream": "unresolved",
        "harmonization_coefficient_calculated": False,
    }
    for item in platforms:
        item.pop("monthly", None)
    encoded = json.dumps(_json_ready(report), indent=2)
    if key and key in encoded:
        encoded = redact(encoded, key)
    if re.search(r"/csv/[^/\"\s]{16,}/", encoded) or re.search(r"MAP_KEY=(?!<)[^\s\"<]{8,}", encoded):
        raise FirmsApiError("Refusing to write a thermal report that embeds a MAP_KEY value")
    REPORT_JSON.write_text(encoded + "\n", encoding="utf-8")
    written = json.loads(encoded)
    REPORT_MD.write_text(render_markdown(written), encoding="utf-8")
    return written


def refresh_saved_documentation(path: Path | None = None) -> dict[str, object]:
    """Re-read public documents into an existing report. Area requests are not repeated."""

    started = perf_counter()
    target = REPORT_JSON if path is None else path
    report = json.loads(target.read_text(encoding="utf-8"))
    previous_guide = (report.get("documentation") or {}).get("user_guide") or {}
    previous_sha = previous_guide.get("sha256")
    guide_binary = fetch_binary(USER_GUIDE_PDF)
    body = guide_binary.get("body")
    text = pdf_text(body) if isinstance(body, bytes) else ""
    guide_record = _page_record({key_name: value for key_name, value in guide_binary.items() if key_name != "body"} | {"body_text": text})
    statements = extract_user_guide_statements(text)
    guide_record["statements"] = statements
    guide_record["text_extracted"] = bool(statements.get("fp_t4_i4_kelvin") and statements.get("monthly_t4_i4_kelvin"))
    guide_record["sha256_matches_comparison_pass"] = guide_record.get("sha256") == previous_sha
    pages = {}
    for url in (VIIRS_ATTRIBUTE_PAGE, MODIS_ATTRIBUTE_PAGE, EARTHDATA_ATTRIBUTES_PAGE, VJ114IMG_PAGE, VJ214IMG_PAGE):
        pages[url] = fetch_public(url, timeout=120)
    attribute = _page_record(pages[VIIRS_ATTRIBUTE_PAGE])
    attribute["statements"] = extract_viirs_attribute_statements(str(pages[VIIRS_ATTRIBUTE_PAGE].get("body_text") or ""))
    modis = _page_record(pages[MODIS_ATTRIBUTE_PAGE])
    modis["statements"] = extract_modis_bright_t31_statement(str(pages[MODIS_ATTRIBUTE_PAGE].get("body_text") or ""))
    earthdata = _page_record(pages[EARTHDATA_ATTRIBUTES_PAGE])
    earthdata["statements"] = extract_viirs_attribute_statements(str(pages[EARTHDATA_ATTRIBUTES_PAGE].get("body_text") or ""))
    report["documentation"]["viirs_attribute_page"] = attribute
    report["documentation"]["modis_attribute_page"] = modis
    report["documentation"]["earthdata_attributes_page"] = earthdata
    report["documentation"]["user_guide"] = guide_record
    report["documentation"]["level2_catalogs"] = [_catalog_facts(pages[url]) for url in (VJ114IMG_PAGE, VJ214IMG_PAGE)]
    report["documentation_text_refresh"] = {
        "retrieved_at": utc_now(),
        "wall_clock_seconds": round(perf_counter() - started, 6),
        "area_requests_repeated": False,
        "previous_user_guide_sha256": previous_sha,
        "user_guide_sha256": guide_record.get("sha256"),
        "reason": "The comparison pass hashed the user's guide PDF. Its text layer is read here, without another area request.",
    }
    encoded = json.dumps(report, indent=2)
    if re.search(r"/csv/[^/\"\s]{16,}/", encoded) or re.search(r"MAP_KEY=(?!<)[^\s\"<]{8,}", encoded):
        raise FirmsApiError("Refusing to write a thermal report that embeds a MAP_KEY value")
    target.write_text(encoded + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    report = run()
    relationships = ",".join(
        f"{item['platform']}={item['thermal_relationship']}" for item in report["platforms"]
    )
    print(
        f"authenticated_requests_sent={str(report['authenticated_requests_sent']).lower()} "
        f"relationships={relationships} day_files_unchanged={str(report['original_day_files_unchanged']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
