import hashlib
from pathlib import Path

import numpy as np
import pytest

from fire_data.contract import BACKEND_ROOT, COLUMNS, RAW_DIR, SOURCES
from fire_data.temporal import (
    build_temporal_validation,
    cluster_extremes,
    determine_processing_level,
    epoch_minutes,
    frp_by_group,
    proximity_counts,
    temporal_repeat_status,
)
from fire_data.temporal_report import render_report, write_temporal


def _row(**overrides: str) -> str:
    values = {
        "latitude": "10.0",
        "longitude": "20.0",
        "brightness": "320.00",
        "scan": "0.40",
        "track": "0.36",
        "acq_date": "2024-07-07",
        "acq_time": "1200",
        "satellite": "N20",
        "instrument": "VIIRS",
        "confidence": "n",
        "version": "2",
        "bright_t31": "300.00",
        "frp": "10.0",
        "daynight": "D",
        "type": "0",
    }
    values.update(overrides)
    return ",".join(values[column] for column in COLUMNS)


def _write(path: Path, rows: list[str]) -> None:
    path.write_text(",".join(COLUMNS) + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_filename_and_version_do_not_assign_a_processing_level():
    samples = (
        ("fire_archive_J1V-C2_850119.csv", ("2",)),
        ("fire_archive_J2V-C2_850120.csv", ("2",)),
        ("fire_archive_SV-C2_850121.csv", ("2",)),
        ("fire_archive_M-C61_850118.csv", ("61.03",)),
        ("fire_nrt_J1V-C2_1.csv", ("2",)),
    )
    for filename, versions in samples:
        result = determine_processing_level(filename=filename, version_values=versions, columns=COLUMNS)
        assert result["processing_level"] == "unresolved"
        assert result["determined"] is False
        assert result["processing_level_column_present"] is False


def test_one_date_is_not_a_temporal_repeat_and_two_dates_are():
    assert temporal_repeat_status(["2024-07-07"]) == "unavailable"
    assert temporal_repeat_status(["2024-07-07", "2024-07-08"]) == "available"
    assert epoch_minutes("2024-07-08", "0010") - epoch_minutes("2024-07-07", "2350") == 20


def test_brightness_repeat_keeps_dates_separate_and_does_not_confirm_saturation(tmp_path: Path):
    archive = tmp_path / "fire_archive_J1V-C2_1.csv"
    _write(
        archive,
        [
            _row(acq_date="2024-07-07", brightness="367", confidence="h"),
            _row(acq_date="2024-07-07", brightness="366.50", confidence="n"),
            _row(acq_date="2024-07-08", brightness="367", confidence="l"),
            _row(acq_date="2024-07-08", brightness="368", confidence="h"),
        ],
    )
    source = next(item for item in SOURCES if item.source_id == "viirs_noaa20")
    summary = build_temporal_validation((source,), {source.source_id: archive}, radii_m=(1_000.0,), windows_min=(0,))

    assert summary["scope"]["multi_date_validation"] == "available"
    by_date = {row["acq_date"]: row for row in summary["brightness"]}
    assert by_date["2024-07-07"]["numeric_equal_367"] == 1
    assert by_date["2024-07-07"]["from_360_below_367"] == 1
    assert by_date["2024-07-07"]["above_367"] == 0
    assert by_date["2024-07-08"]["above_367"] == 1
    assert by_date["2024-07-08"]["confirmed_saturated_count"] == 0
    assert by_date["2024-07-07"]["confirmed_saturated_count"] == 0
    assert all(archive_row["processing_level"] == "unresolved" for archive_row in summary["archives"])


def test_day_and_night_frp_stay_separate_and_clusters_count_rows():
    rows = {
        "satellite": np.array(["Aqua", "Aqua", "Aqua", "Terra"], dtype=object),
        "acq_date": np.array(["2024-07-07"] * 4, dtype=object),
        "daynight": np.array(["D", "D", "N", "D"], dtype=object),
        "frp": np.array([10.0, 100.0, 5.0, 50.0]),
        "frp_text": np.array(["10.0", "100.0", "5.0", "50.0"], dtype=object),
        "confidence": np.array(["75", "0", "80", "90"], dtype=object),
        "latitude": np.array([10.1, 10.2, 40.0, -10.0]),
        "longitude": np.array([20.1, 20.2, 30.0, 40.0]),
        "acq_time": np.array(["1200", "1200", "0100", "1300"], dtype=object),
        "brightness": np.array(["300", "400", "310", "320"], dtype=object),
        "scan": np.array(["1", "1", "1", "1"], dtype=object),
        "track": np.array(["1", "1", "1", "1"], dtype=object),
        "line_number": np.array([2, 3, 4, 5]),
    }
    records = {(row["satellite"], row["daynight"]): row for row in frp_by_group(rows)}

    assert records[("Aqua", "D")]["maximum_text"] == "100.0"
    assert records[("Aqua", "D")]["confidence_at_maximum"] == ["0"]
    assert records[("Aqua", "N")]["maximum_text"] == "5.0"
    assert records[("Terra", "D")]["maximum_text"] == "50.0"
    assert records[("Aqua", "N")]["detection_count"] == 1

    cluster = cluster_extremes(
        np.array([10.1, 10.8, 25.2]),
        np.array([20.1, 20.4, 21.0]),
        np.array(["1200", "1210", "1300"], dtype=object),
        np.array([True, True, True]),
    )
    assert cluster["extreme_cell_count"] == 2
    assert cluster["densest_cell_count"] == 2
    assert cluster["densest_cell_share"] == pytest.approx(2 / 3)


def test_proximity_respects_time_and_does_not_assign_a_fire():
    satellite = np.array(["Aqua", "N20", "N20", "Terra"], dtype=object)
    latitude = np.array([0.0, 0.0, 0.0, 10.0])
    longitude = np.array([0.0, 0.001, 0.001, 10.0])
    epoch = np.array(
        [
            epoch_minutes("2024-07-07", "1200"),
            epoch_minutes("2024-07-07", "1210"),
            epoch_minutes("2024-07-07", "1200"),
            epoch_minutes("2024-07-07", "1200"),
        ]
    )
    rows = proximity_counts(satellite, latitude, longitude, epoch, radii_m=(375.0, 1_000.0), windows_min=(0, 30))
    aqua_n20 = [row for row in rows if {row["satellite_a"], row["satellite_b"]} == {"Aqua", "N20"}]
    by_window = {(row["radius_m"], row["max_delta_minutes"]): row for row in aqua_n20}

    assert by_window[(375.0, 0)]["proximity_pairs"] == 1
    assert by_window[(375.0, 30)]["proximity_pairs"] == 2
    assert by_window[(1_000.0, 0)]["detections_a_with_neighbor"] == 1
    assert all(row["same_fire"] == "not_assessed" for row in rows)
    terra = [row for row in rows if "Terra" in {row["satellite_a"], row["satellite_b"]}]
    assert all(row["proximity_pairs"] == 0 for row in terra)


def test_report_keeps_the_single_date_limit_and_writes_no_coefficient(tmp_path: Path):
    archive = tmp_path / "fire_archive_M-C61_1.csv"
    _write(
        archive,
        [
            _row(satellite="Aqua", instrument="MODIS", version="61.03", confidence="75", frp="7956.3", daynight="D"),
            _row(
                satellite="Terra",
                instrument="MODIS",
                version="61.03",
                confidence="50",
                frp="20.0",
                daynight="N",
                acq_time="0300",
                latitude="11",
                longitude="21",
            ),
        ],
    )
    source = next(item for item in SOURCES if item.source_id == "modis")
    summary = build_temporal_validation((source,), {source.source_id: archive}, radii_m=(1_000.0,), windows_min=(30,))
    report = render_report(summary)

    assert summary["scope"]["multi_date_validation"] == "unavailable"
    assert "Multi-date temporal validation is unavailable." in report
    assert "Processing level is unresolved" in report
    assert "not_assessed" in report
    assert "harmonization coefficient" in report
    assert all("coefficient" not in row or row["variable"] == "frp" for row in summary["variables"])
    assert not any("harmonization_coefficient" in row for row in summary["variables"])
    assert {row["disposition"] for row in summary["variables"]} == {"calibration_candidate", "special_treatment"}
    assert "unique_fires" not in summary
    report_path, json_path = write_temporal(summary, tmp_path / "out")
    assert report_path.exists() and json_path.exists()
    assert (tmp_path / "out" / "temporal" / "proximity_matches.csv").exists()


def test_writer_refuses_the_raw_archive_directory():
    with pytest.raises(ValueError, match="raw archive"):
        write_temporal({"scope": {}, "archives": [], "brightness": [], "modis_frp": [], "modis_maxima": [], "proximity": [], "variables": [], "missing": [], "document_statements": []}, RAW_DIR)


def test_extracted_archives_have_one_date_and_unresolved_provenance(tmp_path: Path):
    raw_hashes = {
        source.relative_path.as_posix(): hashlib.sha256(source.path.read_bytes()).hexdigest() for source in SOURCES
    }
    preserved = [
        BACKEND_ROOT / "reports" / "eda_report.md",
        BACKEND_ROOT / "reports" / "eda_summary.json",
        BACKEND_ROOT / "reports" / "anomaly_investigation.md",
        BACKEND_ROOT / "reports" / "anomaly_summary.json",
    ]
    before = {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in preserved if path.exists()}
    summary = build_temporal_validation(radii_m=(375.0, 1_000.0, 5_000.0), windows_min=(0, 30, 180))
    write_temporal(summary, tmp_path)
    after_raw = {
        source.relative_path.as_posix(): hashlib.sha256(source.path.read_bytes()).hexdigest() for source in SOURCES
    }
    after_reports = {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in preserved if path.exists()}

    assert after_raw == raw_hashes
    assert after_reports == before
    assert summary["scope"]["dates"] == ["2024-07-07"]
    assert summary["scope"]["multi_date_validation"] == "unavailable"
    assert all(archive["processing_level"] == "unresolved" for archive in summary["archives"])
    assert all(archive["determined"] is False for archive in summary["archives"])
    brightness = {row["satellite"]: row for row in summary["brightness"]}
    assert brightness["N20"]["numeric_equal_367"] == 3190
    assert brightness["N21"]["numeric_equal_367"] == 7305
    assert brightness["SNPP"]["numeric_equal_367"] == 5600
    assert all(row["above_367"] == 0 and row["confirmed_saturated_count"] == 0 for row in summary["brightness"])
    aqua_day = next(row for row in summary["modis_frp"] if row["satellite"] == "Aqua" and row["daynight"] == "D")
    assert aqua_day["maximum_text"] == "7956.3"
    assert aqua_day["confidence_at_maximum"] == ["75"]
    assert all(row["same_fire"] == "not_assessed" for row in summary["proximity"])
    assert "unique_fires" not in summary
    report = (tmp_path / "temporal_validation.md").read_text(encoding="utf-8")
    assert "Multi-date temporal validation is unavailable." in report
    assert "Processing level is unresolved" in report
