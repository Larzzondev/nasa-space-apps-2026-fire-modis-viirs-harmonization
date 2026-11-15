import hashlib
from pathlib import Path

import numpy as np
import pytest

from fire_data.contract import BACKEND_ROOT, COLUMNS, RAW_DIR, SOURCES
from fire_data.readiness import (
    VARIABLE_CLASSES,
    acquisition_specification,
    build_readiness,
    classify_variables,
    count_duplicates,
    matching_audit,
    provenance_rows,
)
from fire_data.readiness_report import render_report, write_readiness
from fire_data.temporal import epoch_minutes, proximity_counts


def _row(**overrides: str) -> str:
    values = {
        "latitude": "0",
        "longitude": "0",
        "brightness": "320.00",
        "scan": "0.40",
        "track": "0.36",
        "acq_date": "2024-07-07",
        "acq_time": "1200",
        "satellite": "Aqua",
        "instrument": "MODIS",
        "confidence": "75",
        "version": "61.03",
        "bright_t31": "300",
        "frp": "10.0",
        "daynight": "D",
        "type": "0",
    }
    values.update(overrides)
    return ",".join(values[column] for column in COLUMNS)


def _write(path: Path, rows: list[str]) -> None:
    path.write_text(",".join(COLUMNS) + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_filename_and_version_do_not_fill_the_processing_stream():
    rows = provenance_rows(
        {
            "source_id": "viirs_noaa20",
            "filename": "fire_archive_J1V-C2_850119.csv",
            "columns": list(COLUMNS),
            "row_count": 4,
            "dates": {"2024-07-07": 4},
            "versions": {"2": 4},
            "satellites": {"N20": 4},
            "instruments": {"VIIRS": 4},
            "sha256": "abc",
            "byte_size": 12,
        }
    )
    by_field = {row["field"]: row for row in rows}
    assert set(row["status"] for row in rows) == {"verified", "unverified", "missing"}
    assert by_field["processing_stream"]["status"] == "missing"
    assert by_field["processing_stream"]["value"] is None
    assert by_field["product_short_name"]["status"] == "missing"
    assert by_field["version_values"]["status"] == "verified"
    assert by_field["version_values"]["value"] == {"2": 4}
    assert by_field["filename"]["status"] == "verified"
    assert by_field["version_suffix_rule"]["status"] == "unverified"


def test_matching_audit_counts_each_pair_once_and_keeps_same_fire_open():
    satellite = np.array(["Aqua", "N20", "N20", "Terra"], dtype=object)
    latitude = np.array([0.0, 0.0, 0.0, 10.0])
    longitude = np.array([0.0, 0.001, 0.002, 10.0])
    epoch = np.array(
        [
            epoch_minutes("2024-07-07", "1200"),
            epoch_minutes("2024-07-07", "1210"),
            epoch_minutes("2024-07-07", "1200"),
            epoch_minutes("2024-07-07", "1200"),
        ]
    )
    radii = (375.0,)
    windows = (0, 30)
    audited = matching_audit(satellite, latitude, longitude, epoch, radii, windows)
    counted = proximity_counts(satellite, latitude, longitude, epoch, radii, windows)
    aqua_n20 = [row for row in audited if {row["satellite_a"], row["satellite_b"]} == {"Aqua", "N20"}]
    by_window = {row["max_delta_minutes"]: row for row in aqua_n20}

    assert by_window[0]["raw_pair_count"] == 1
    assert by_window[30]["raw_pair_count"] == 2
    assert by_window[30]["unique_source_detections"] == 1
    assert by_window[30]["unique_target_detections"] == 2
    assert by_window[30]["detections_with_at_least_one_neighbor"] == 3
    assert by_window[30]["raw_pair_count"] != by_window[30]["detections_with_at_least_one_neighbor"]
    assert by_window[0]["nearest_neighbor_source_to_target_m"]["p50"] == pytest.approx(222.4, rel=0.02)
    assert by_window[30]["nearest_neighbor_source_to_target_m"]["p50"] == pytest.approx(111.2, rel=0.02)
    assert all(row["same_fire"] == "not_assessed" for row in audited)
    assert all(row["reverse_pairs_stored"] == 0 for row in audited)
    assert all(row["interpreted_as_unique_fires"] is False for row in audited)
    for left, right in zip(
        sorted(audited, key=lambda item: (item["satellite_a"], item["satellite_b"], item["max_delta_minutes"])),
        sorted(counted, key=lambda item: (item["satellite_a"], item["satellite_b"], item["max_delta_minutes"])),
        strict=True,
    ):
        assert left["raw_pair_count"] == right["proximity_pairs"]
        assert left["unique_source_detections"] == right["detections_a_with_neighbor"]
        assert left["unique_target_detections"] == right["detections_b_with_neighbor"]


def test_duplicate_rows_are_counted_and_retained(tmp_path: Path):
    path = tmp_path / "modis.csv"
    repeated = _row()
    _write(path, [repeated, repeated, _row(latitude="1")])
    source = next(item for item in SOURCES if item.source_id == "modis")
    counted = count_duplicates((source,), {source.source_id: path})

    assert counted["exact_duplicate_rows"] == 1
    assert counted["location_time_duplicate_rows"] == 1
    assert counted["duplicates_removed_before_matching"] == 0


def test_variables_have_one_class_and_no_coefficient():
    rows = classify_variables()
    assert {row["classification"] for row in rows} <= set(VARIABLE_CLASSES)
    assert {row["variable"] for row in rows} == {
        "frp",
        "scan",
        "track",
        "daynight",
        "brightness",
        "confidence",
        "satellite",
        "acquisition_time",
        "latitude_longitude",
    }
    by_name = {row["variable"]: row["classification"] for row in rows}
    assert by_name["frp"] == "candidate_measurement"
    assert by_name["scan"] == "observation_geometry"
    assert by_name["track"] == "observation_geometry"
    assert by_name["daynight"] == "stratification_variable"
    assert by_name["satellite"] == "stratification_variable"
    assert by_name["brightness"] == "excluded_until_further_evidence"
    assert by_name["confidence"] == "excluded_until_further_evidence"
    assert by_name["acquisition_time"] == "matching_key"
    assert by_name["latitude_longitude"] == "matching_key"
    assert all("coefficient" not in row for row in rows)


def test_acquisition_spec_asks_for_30_dates_and_does_not_invent_them():
    spec = acquisition_specification(["2024-07-07"])

    assert spec["target_date_count"] == 30
    assert spec["dates_acquired_for_this_spec"] == []
    assert spec["fabricated_dates"] is False
    assert spec["dates_present_in_current_archives"] == ["2024-07-07"]
    assert spec["product_identifiers"]["assigned_to_current_files"] is False
    assert spec["product_identifiers"]["download_readme"]["NOAA20_standard_in_download_readme"] is None
    assert spec["file_naming_and_checksums"]["checksum_algorithm"] == "SHA-256"


def test_report_states_the_stream_is_missing_and_writer_refuses_raw_archives(tmp_path: Path):
    summary = build_readiness(
        (next(item for item in SOURCES if item.source_id == "modis"),),
        {
            next(item for item in SOURCES if item.source_id == "modis").source_id: _prepared_modis(tmp_path)
        },
        radii_m=(1_000.0,),
        windows_min=(30,),
    )
    report = render_report(summary)
    assert "processing stream are missing" in report
    assert "not_assessed" in report
    assert "Fabricated dates: no." in report
    assert "unique fire" not in report.lower() or "not converted into a unique-fire total" in report
    write_readiness(summary, tmp_path / "out")
    with pytest.raises(ValueError, match="raw archive"):
        write_readiness(summary, RAW_DIR)


def _prepared_modis(directory: Path) -> Path:
    path = directory / "fire_archive_M-C61_1.csv"
    _write(
        path,
        [
            _row(satellite="Aqua", latitude="10", longitude="20"),
            _row(satellite="Terra", latitude="11", longitude="21", acq_time="0300", daynight="N"),
        ],
    )
    return path


def test_extracted_archives_remain_unidentified_and_previous_reports_stay_put(tmp_path: Path):
    preserved = [
        BACKEND_ROOT / "reports" / name
        for name in (
            "eda_report.md",
            "eda_summary.json",
            "anomaly_investigation.md",
            "anomaly_summary.json",
            "temporal_validation.md",
            "temporal_summary.json",
        )
    ]
    raw_before = {source.path.as_posix(): hashlib.sha256(source.path.read_bytes()).hexdigest() for source in SOURCES}
    report_before = {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in preserved if path.exists()}
    summary = build_readiness()
    write_readiness(summary, tmp_path)
    raw_after = {source.path.as_posix(): hashlib.sha256(source.path.read_bytes()).hexdigest() for source in SOURCES}
    report_after = {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in preserved if path.exists()}

    assert raw_after == raw_before
    assert report_after == report_before
    assert summary["scope"]["dates_present"] == ["2024-07-07"]
    assert summary["scope"]["temporal_validation"] == "not_performed"
    assert summary["scope"]["calibration_coefficients_calculated"] is False
    assert all(item["status"] == "missing" and item["value"] is None for item in summary["processing_stream_status"].values())
    assert summary["discrepancy"]["resolution"] == "unresolved"
    assert summary["acquisition_specification"]["dates_acquired_for_this_spec"] == []
    pair = next(
        row
        for row in summary["matching"]
        if row["satellite_a"] == "Terra"
        and row["satellite_b"] == "Aqua"
        and row["radius_m"] == 375.0
        and row["max_delta_minutes"] == 30
    )
    assert pair["raw_pair_count"] == 9
    assert pair["same_fire"] == "not_assessed"
    assert pair["interpreted_as_unique_fires"] is False
    assert pair["reverse_pairs_stored"] == 0
    assert all(row["same_fire"] == "not_assessed" for row in summary["matching"])
    text = (tmp_path / "data_readiness.md").read_text(encoding="utf-8")
    assert "Resolution: unresolved." in text
    assert "Candidate measurement" in text
