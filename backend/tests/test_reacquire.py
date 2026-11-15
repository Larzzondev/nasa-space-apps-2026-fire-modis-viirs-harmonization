import json
from pathlib import Path

import pytest

from fire_data.contract import COLUMNS
from fire_data.reacquire import (
    ReacquireError,
    archive_date_supported,
    area_request_template,
    build_report,
    compare_deliveries,
    load_rows,
    parse_missing_standard,
    refuse_network_download,
)


def record(**overrides: str) -> dict[str, str]:
    values = {
        "latitude": "1",
        "longitude": "2",
        "brightness": "300",
        "scan": "0.4",
        "track": "0.4",
        "acq_date": "2024-07-16",
        "acq_time": "1742",
        "satellite": "SNPP",
        "instrument": "SNPP",
        "confidence": "n",
        "version": "2",
        "bright_t31": "290",
        "frp": "1.5",
        "daynight": "N",
        "type": "0",
    }
    values.update(overrides)
    return values


def test_published_coverage_includes_both_target_dates() -> None:
    assert archive_date_supported("2024-07-16")
    assert archive_date_supported("2024-07-25")
    assert not archive_date_supported("2012-01-19")


def test_area_template_does_not_embed_a_key() -> None:
    template = area_request_template("2024-07-16")
    assert "[MAP_KEY]" in template
    assert template.endswith("/VIIRS_SNPP_SP/world/1/2024-07-16")


def test_network_download_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAP_KEY", raising=False)
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    with pytest.raises(ReacquireError, match="No MAP_KEY"):
        refuse_network_download()


def test_a_present_key_is_not_used_as_permission_to_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAP_KEY", "not-a-real-key")
    with pytest.raises(ReacquireError, match="was not confirmed"):
        refuse_network_download()


def test_empty_numeric_field_is_not_zero(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text(",".join(COLUMNS) + "\n" + ",".join([""] * len(COLUMNS)) + "\n", encoding="utf-8")
    with pytest.raises(ReacquireError, match="not converted to zero"):
        load_rows(path)


def test_compare_exact_missing_additional_and_changed() -> None:
    original = [
        record(),
        record(frp="9"),
        record(latitude="3", longitude="4", acq_time="1800"),
    ]
    independent = [
        record(latitude="1.0", longitude="2.0", brightness="300.0"),
        record(frp="8"),
        record(latitude="5", longitude="6", acq_time="1900"),
    ]
    result = compare_deliveries(list(COLUMNS), original, list(COLUMNS), independent)
    assert result["exact_record_matches"] == 1
    assert result["same_identity_changed_values"] == 1
    assert result["missing_from_independent"] == 1
    assert result["additional_in_independent"] == 1
    assert result["records_are_unique_fires"] is False
    assert result["empty_original_is_zero_detections"] is False


def test_two_empty_tables_are_not_zero_detections() -> None:
    result = compare_deliveries(list(COLUMNS), [], list(COLUMNS), [])
    assert result["original_rows"] == 0
    assert result["independent_rows"] == 0
    assert result["exact_record_matches"] == 0
    assert result["empty_original_is_zero_detections"] is False
    assert result["empty_independent_is_zero_detections"] is False


def test_missing_table_distinguishes_the_two_dates() -> None:
    html = """
    <tr><td>2024-07-25</td><td>Suomi NPP (VIIRS)</td><td>2024-03-01</td><td>NOAA-21 (VIIRS)</td></tr>
    <tr><td>2024-07-16</td><td>NOAA-20 (VIIRS)</td><td></td><td></td></tr>
    """
    parsed = parse_missing_standard({"html": html})
    assert parsed["2024-07-25_listed"] is True
    assert parsed["2024-07-16_listed"] is False
    assert "not a fire count of zero" in parsed["does_not_prove"]


def test_report_without_a_second_file_does_not_invent_differences(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAP_KEY", raising=False)
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    local = {
        "filename": "fire_archive_SV-C2_850322.csv",
        "sha256": "abc",
        "rows": 2,
        "latitude_min": "-1",
        "latitude_max": "1",
        "longitude_min": "-2",
        "longitude_max": "2",
        "dates": {
            "2024-07-16": {
                "rows_in_this_file": 1,
                "absent": False,
                "acq_time_min": "1742",
                "acq_time_max": "1742",
            },
            "2024-07-25": {
                "rows_in_this_file": 0,
                "absent": True,
                "acq_time_min": None,
                "acq_time_max": None,
            },
        },
    }
    report = build_report(local, None, created_at="2026-11-15T00:00:00Z")
    assert report["comparison_status"] == "not_performed"
    assert report["comparison"] is None
    assert report["independent_file_retrieved"] is False
    assert report["area_api"]["called"] is False
    assert report["area_api"]["credential"]["present"] is False
    encoded = json.dumps(report)
    assert "not-a-real-key" not in encoded
    assert "MAP_KEY=" not in encoded
