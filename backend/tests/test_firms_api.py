"""Offline checks for the FIRMS area client.

These tests do not open a network connection and do not read the July CSVs.
"""

import json
from pathlib import Path
from urllib.error import URLError

import pytest

from fire_data.firms_api import (
    FirmsApiError,
    append_manifest_record,
    compare_tables,
    credential_status,
    documentation_facts,
    format_bbox,
    load_map_key,
    parse_fire_csv,
    planned_requests,
    redact,
    redacted_area_url,
    redacted_availability_url,
    write_reports,
    _call,
)


SECRET = "super-secret-key"


def test_credential_status_never_records_the_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    monkeypatch.delenv("MAP_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"FIRMS_MAP_KEY={SECRET}\n", encoding="utf-8")
    status = credential_status({}, env_file)
    assert status["present"] is True
    assert status["selected_source"] == "env_file:FIRMS_MAP_KEY"
    assert status["value_recorded"] is False
    assert SECRET not in json.dumps(status)
    value, source = load_map_key({}, env_file)
    assert value == SECRET
    assert source == "env_file:FIRMS_MAP_KEY"


def test_environment_takes_precedence_over_the_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("FIRMS_MAP_KEY=from-file\n", encoding="utf-8")
    value, source = load_map_key({"FIRMS_MAP_KEY": "from-env"}, env_file)
    assert value == "from-env"
    assert source == "environment:FIRMS_MAP_KEY"


def test_area_template_keeps_the_key_placeholder() -> None:
    url = redacted_area_url("VIIRS_NOAA20_SP", "world", "2024-07-07", 1)
    assert url == (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        "[MAP_KEY]/VIIRS_NOAA20_SP/world/1/2024-07-07"
    )
    availability = redacted_availability_url("VIIRS_NOAA21_SP")
    assert availability.endswith("/api/data_availability/csv/[MAP_KEY]/VIIRS_NOAA21_SP")
    assert SECRET not in url


def test_undocumented_source_and_date_are_rejected() -> None:
    with pytest.raises(FirmsApiError, match="not a source"):
        redacted_area_url("VIIRS_NOAA20_STANDARD", "world", "2024-07-07", 1)
    with pytest.raises(FirmsApiError, match="YYYY-MM-DD"):
        redacted_area_url("VIIRS_NOAA20_SP", "world", "07-07-2024", 1)
    with pytest.raises(FirmsApiError, match="DAY_RANGE"):
        redacted_area_url("VIIRS_NOAA20_SP", "world", "2024-07-07", 7)


def test_bbox_uses_the_documented_order_and_rejects_a_wrapped_box() -> None:
    assert format_bbox("-175.0715", "-50.57444", "175.63397", "71.25928") == (
        "-175.0715,-50.57444,175.63397,71.25928"
    )
    with pytest.raises(FirmsApiError, match="wrapped"):
        format_bbox("175", "-10", "-175", "10")


def test_empty_and_header_only_responses_are_not_zero_fires() -> None:
    _header, _rows, empty = parse_fire_csv("")
    assert empty["zero_fire_activity"] is False
    assert empty["parsed_as_fire_table"] is False
    header, rows, parsed = parse_fire_csv("latitude,longitude\n")
    assert header == ["latitude", "longitude"]
    assert rows == []
    assert parsed["header_only"] is True
    assert parsed["zero_fire_activity"] is False


def test_error_body_is_not_counted_as_a_fire_table() -> None:
    _header, rows, parsed = parse_fire_csv("Invalid API call.")
    assert rows == []
    assert parsed["parsed_as_fire_table"] is False
    assert parsed["zero_fire_activity"] is False
    assert SECRET not in json.dumps(parsed)


def test_field_names_are_not_aliased() -> None:
    archive_header = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "brightness", "type"]
    api_header = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "bright_ti4"]
    archive_rows = [
        {
            "latitude": "1.0",
            "longitude": "2",
            "acq_date": "2024-07-07",
            "acq_time": "1",
            "satellite": "N20",
            "brightness": "300",
            "type": "0",
        }
    ]
    api_rows = [
        {
            "latitude": "1",
            "longitude": "2.0",
            "acq_date": "2024-07-07",
            "acq_time": "0001",
            "satellite": "N20",
            "bright_ti4": "300",
        }
    ]
    result = compare_tables(archive_header, archive_rows, api_header, api_rows)
    assert result["brightness_renamed_to_bright_ti4"] is False
    assert result["archive_only_columns"] == ["brightness", "type"]
    assert result["api_only_columns"] == ["bright_ti4"]
    assert result["exact_shared_field_matches"] == 1
    assert result["product_equivalence"] == "not_assessed"
    assert result["same_fire"] == "not_assessed"
    assert result["records_are_unique_fires"] is False
    assert result["zero_fire_activity"] is False


def test_two_empty_tables_are_not_zero_detections() -> None:
    header = ["latitude", "longitude", "acq_date", "acq_time", "satellite"]
    result = compare_tables(header, [], header, [])
    assert result["archive_rows"] == 0
    assert result["api_rows"] == 0
    assert result["exact_shared_field_matches"] == 0
    assert result["empty_api_table_is_zero_detections"] is False


def test_missing_key_plans_a_request_and_does_not_mark_it_sent() -> None:
    archive = {
        "platform": "NOAA-20",
        "api_source": "VIIRS_NOAA20_SP",
        "observed_bbox": "-1,-2,3,4",
        "bbox_meaning": "stored points",
    }
    planned = planned_requests([archive])
    assert planned[0]["sent"] is False
    assert planned[0]["http_status"] is None
    assert planned[0]["rows"] is None
    assert "[MAP_KEY]" in planned[0]["url"]
    assert planned[0]["zero_fire_activity"] is False
    assert SECRET not in json.dumps(planned)


def test_network_failure_redacts_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(request: object, timeout: float = 0) -> None:
        address = getattr(request, "full_url")
        raise URLError(f"timed out calling {address}")

    monkeypatch.setattr("fire_data.firms_api.urlopen", explode)
    template = redacted_area_url("VIIRS_NOAA21_SP", "world", "2024-07-07", 1)
    record = _call(template, SECRET, "area")
    encoded = json.dumps(record)
    assert SECRET not in encoded
    assert "[MAP_KEY]" in encoded
    assert record["sent"] is True
    assert record["retries"] == 1
    assert record["zero_fire_activity"] is False


def test_manifest_insert_preserves_sensor_records(tmp_path: Path) -> None:
    path = tmp_path / "ingestion.json"
    original = {
        "period": {"start": "2024-07-01", "end": "2024-07-31"},
        "sensors": [
            {
                "sensor": "viirs_noaa20",
                "processing_stream": None,
                "csv_sha256": "abc",
                "record_count": 3,
            }
        ],
        "passed": True,
    }
    path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")
    append_manifest_record(
        path,
        {
            "id": "firms-api-2024-07-07-noaa20-noaa21",
            "authenticated_requests_sent": False,
            "processing_stream": "unresolved",
            "same_fire": "not_assessed",
            "original_sensor_records_modified": False,
        },
    )
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["sensors"] == original["sensors"]
    assert written["passed"] is True
    assert written["firms_api_provenance"][0]["processing_stream"] == "unresolved"
    assert SECRET not in path.read_text(encoding="utf-8")


def test_documentation_facts_read_the_published_template() -> None:
    area = """
    <a href="/descriptions/VIIRS_NOAA20.html">Attribute table for VIIRS NOAA-20</a>
    /api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]/[DATE]
    YYYY-MM-DD
    1 .. 5
    world - [-180,-90,180,90]
    VIIRS_NOAA20_SP
    VIIRS_NOAA21_SP
    """
    pages = {
        "https://firms.modaps.eosdis.nasa.gov/api/area/": {"body_text": area},
        "https://firms.modaps.eosdis.nasa.gov/api/data_availability/": {"body_text": "VIIRS_NOAA20_SP"},
        "https://firms.modaps.eosdis.nasa.gov/api/": {"body_text": "CSV format. Feature currently not available."},
        "https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html": {
            "body_text": "/api/data_availability/csv/ bright_ti4"
        },
    }
    facts = documentation_facts(pages)
    assert facts["area_template_present"] is True
    assert facts["historical_date_syntax"] == "YYYY-MM-DD"
    assert facts["day_range_text"] == "1 .. 5"
    assert facts["world_token_present"] is True
    assert facts["target_sources_on_area_page"] == ["VIIRS_NOAA20_SP", "VIIRS_NOAA21_SP"]
    assert facts["archive_download_equated_to_area_csv"] is False
    assert facts["attribute_links"][0]["label"] == "VIIRS NOAA-20"
    assert facts["academy_nrt_example_uses_bright_ti4"] is True
    assert facts["country_service_marked_unavailable"] is True


def test_report_writer_accepts_placeholders_and_rejects_a_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fire_data.firms_api.REPORT_JSON", tmp_path / "report.json")
    monkeypatch.setattr("fire_data.firms_api.REPORT_MD", tmp_path / "report.md")
    report = {
        "created_at": "2026-11-15T00:00:00Z",
        "authenticated_requests_sent": False,
        "processing_stream": "unresolved",
        "same_fire": "not_assessed",
        "product_equivalence": "not_assessed",
        "configuration_needed": {
            "variable": "FIRMS_MAP_KEY",
            "also_accepted": "MAP_KEY",
            "file": "backend/.env",
            "line": "FIRMS_MAP_KEY=<MAP_KEY issued by FIRMS>",
            "issuer": "https://firms.modaps.eosdis.nasa.gov/api/map_key",
        },
        "documentation": {
            "facts": {
                "area_template_present": True,
                "historical_date_syntax": "YYYY-MM-DD",
                "day_range_text": "1 .. 5",
                "output_format_in_area_template": "csv",
                "transaction_limit_text": "5000 transactions",
                "target_sources_on_area_page": ["VIIRS_NOAA20_SP", "VIIRS_NOAA21_SP"],
            },
            "same_product_as_archive_download": "Equivalence stays not_assessed.",
        },
        "local_archives": [],
        "requests": [
            {
                "source": "VIIRS_NOAA20_SP",
                "url": "https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/VIIRS_NOAA20_SP/world/1/2024-07-07",
                "sent": False,
                "reason": "The authenticated URL was not opened.",
            }
        ],
        "comparison": None,
        "monthly_checksums": [],
        "does_not_prove": ["same_fire remains not_assessed."],
    }
    write_reports(report)
    assert SECRET not in (tmp_path / "report.json").read_text(encoding="utf-8")
    leaked = dict(report)
    leaked["requests"] = [
        {
            "source": "VIIRS_NOAA20_SP",
            "url": f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{SECRET}/VIIRS_NOAA20_SP/world/1/2024-07-07",
            "sent": False,
            "reason": "no",
        }
    ]
    with pytest.raises(FirmsApiError, match="MAP_KEY value"):
        write_reports(leaked)


def test_redact_removes_the_key_from_a_url() -> None:
    text = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{SECRET}/VIIRS_NOAA20_SP/world/1/2024-07-07"
    assert SECRET not in redact(text, SECRET)
    assert "[MAP_KEY]" in redact(text, SECRET)
