from pathlib import Path

import numpy as np

from fire_data.contract import COLUMNS
from fire_data.monthly import smallest_positive_days
from fire_data.monthly_figures import FIGURE_NAMES, write_figures
from fire_data.monthly_report import LIMITATIONS, render_coverage, render_eda
from fire_data.monthly_scan import (
    build_coverage,
    count_sorted_duplicates,
    coverage_cell,
    investigate_snpp,
    scan_csv,
    week_label,
)


def test_zero_delivered_rows_are_separate_from_a_missing_file() -> None:
    present = coverage_cell(True, 0)
    missing = coverage_cell(False, None)
    assert present["status"] == "zero_rows_delivered"
    assert present["delivered_rows"] == 0
    assert "not a measurement of zero fire activity" in present["meaning"]
    assert missing["status"] == "source_file_missing"
    assert missing["delivered_rows"] is None


def test_snpp_window_keeps_a_partly_covered_date() -> None:
    delivered = {
        "SNPP": {"2024-07-16": 15},
        "Terra": {"2024-07-10": 4},
        "Aqua": {"2024-07-10": 5},
        "N20": {"2024-07-10": 6, "2024-07-25": 7},
        "N21": {"2024-07-10": 8, "2024-07-25": 9},
    }
    present = {sensor: True for sensor in ("modis", "viirs_snpp", "viirs_noaa20", "viirs_noaa21")}
    windows = investigate_snpp(delivered, present)
    first, second = windows
    assert first["snpp_zero_rows_delivered"] == [
        "2024-07-10",
        "2024-07-11",
        "2024-07-12",
        "2024-07-13",
        "2024-07-14",
        "2024-07-15",
    ]
    assert first["snpp_dates_with_rows"] == ["2024-07-16"]
    assert second["snpp_zero_rows_delivered"] == ["2024-07-25", "2024-07-26", "2024-07-27", "2024-07-28"]
    assert "not evidence of an S-NPP outage" in first["inference"]


def test_duplicate_digest_counts_extra_copies_only() -> None:
    first = bytes(range(16))
    second = bytes(range(16, 32))
    buf = bytearray(first + first + second + first)
    assert count_sorted_duplicates(buf) == 2


def test_week_label_and_smallest_days() -> None:
    assert week_label("2024-07-07") == "2024-07-01 to 2024-07-07"
    assert week_label("2024-07-29") == "2024-07-29 to 2024-07-31"
    smallest = smallest_positive_days({"2024-07-02": 5, "2024-07-03": 1, "2024-07-04": 9})
    assert [item["date"] for item in smallest] == ["2024-07-03", "2024-07-02", "2024-07-04"]


def test_coverage_matrix_splits_terra_and_aqua() -> None:
    delivered = {"Terra": {"2024-07-01": 2}, "Aqua": {}, "N20": {}, "N21": {}, "SNPP": {}}
    present = {sensor: True for sensor in ("modis", "viirs_snpp", "viirs_noaa20", "viirs_noaa21")}
    matrix = build_coverage(delivered, present)
    july1 = matrix[0]["satellites"]
    assert july1["Terra"]["status"] == "rows_delivered"
    assert july1["Aqua"]["status"] == "zero_rows_delivered"
    assert july1["SNPP"]["delivered_rows"] == 0


def _csv(rows: list[dict[str, str]]) -> str:
    lines = [",".join(COLUMNS)]
    for row in rows:
        lines.append(",".join(row[column] for column in COLUMNS))
    return "\n".join(lines) + "\n"


def _row(satellite: str = "SNPP", day: str = "2024-07-01", confidence: str = "n", frp: str = "1.5") -> dict[str, str]:
    instrument = "MODIS" if satellite in {"Terra", "Aqua"} else "VIIRS"
    if satellite == "SNPP":
        instrument = "SNPP"
    return {
        "latitude": "10.0",
        "longitude": "20.0",
        "brightness": "367" if satellite == "SNPP" else "320.0",
        "scan": "0.4",
        "track": "0.4",
        "acq_date": day,
        "acq_time": "0123",
        "satellite": satellite,
        "instrument": instrument,
        "confidence": confidence,
        "version": "61.03" if instrument == "MODIS" else "2",
        "bright_t31": "290.0",
        "frp": frp,
        "daynight": "N",
        "type": "0",
    }


def test_scan_retains_duplicate_and_malformed_rows(tmp_path: Path) -> None:
    path = tmp_path / "fire_archive_SV-C2_1.csv"
    good = _row()
    path.write_text(_csv([good, good, _row(day="2024-07-02", frp="4.0")]) + "short\n", encoding="utf-8")
    scan = scan_csv(
        path,
        {
            "sensor": "viirs_snpp",
            "satellites": frozenset({"SNPP"}),
            "confidence": "viirs_lnh",
        },
    )
    assert scan["record_count"] == 4
    assert scan["malformed"]["column_count"] == 1
    assert scan["exact_duplicate_rows"] == 1
    assert scan["duplicates_removed"] == 0
    assert scan["daily"]["SNPP"]["2024-07-01"] == 2
    assert "2024-07-10" in scan["weekly_dates_with_zero_rows"]["SNPP"]["2024-07-08 to 2024-07-14"]
    assert scan["brightness_text_367_by_confidence"]["n"] == 3
    assert scan["arrays"]["SNPP"]["frp"].tolist() == [1.5, 1.5, 4.0]


def test_reports_state_the_scientific_limits() -> None:
    coverage = {
        "integrity": {
            "manifest_passed": True,
            "archives": [
                {
                    "sensor": "viirs_snpp",
                    "expected_rows": 2,
                    "record_count": 2,
                    "difference": 0,
                    "csv_sha256": "abc",
                }
            ],
            "total_rows": 2,
            "expected_total": 2,
            "total_difference": 0,
            "exact_duplicate_rows": 0,
            "location_time_duplicate_rows": 0,
            "empty_cells": {},
            "malformed": {},
        },
        "matrix": [
            {
                "date": "2024-07-10",
                "satellites": {
                    satellite: {
                        "status": "zero_rows_delivered" if satellite == "SNPP" else "rows_delivered",
                        "delivered_rows": 0 if satellite == "SNPP" else 3,
                    }
                    for satellite in ("Terra", "Aqua", "N20", "N21", "SNPP")
                },
            }
        ],
        "snpp_windows": [
            {
                "window": {"start": "2024-07-10", "end": "2024-07-16"},
                "snpp_zero_rows_delivered": ["2024-07-10"],
                "snpp_dates_with_rows": ["2024-07-16"],
                "dates": [
                    {
                        "date": "2024-07-10",
                        "snpp": {"status": "zero_rows_delivered", "delivered_rows": 0},
                        "other_archives": {
                            satellite: {"status": "rows_delivered", "delivered_rows": 3}
                            for satellite in ("Terra", "Aqua", "N20", "N21")
                        },
                    }
                ],
                "inference": "Rows in the other archives are not evidence of an S-NPP outage.",
            }
        ],
        "smallest_positive_days": {"SNPP": [{"date": "2024-07-16", "delivered_rows": 15}]},
    }
    text = render_coverage(coverage)
    assert "0 rows delivered" in text
    assert "not a measurement of zero fire activity" in text
    assert "No coefficient is calculated." in text
    eda = {
        "satellites": {
            "SNPP": {
                "sensor": "viirs_snpp",
                "delivered_rows": 2,
                "frp_zero_rows": 0,
                "frp": {
                    "median": 1.5,
                    "mean": 1.5,
                    "maximum": 4.0,
                    "quantiles": {"0.050": 1.5, "0.950": 4.0, "0.990": 4.0},
                },
                "brightness": {
                    "median": 367.0,
                    "mean": 367.0,
                    "maximum": 367.0,
                    "quantiles": {"0.050": 367.0, "0.950": 367.0, "0.990": 367.0},
                },
                "extreme_frp": {
                    "stored_text": "4.0",
                    "rows_with_this_stored_value": 1,
                    "example_row": {
                        "line_number": "4",
                        "acq_date": "2024-07-02",
                        "acq_time": "0123",
                        "latitude": "10.0",
                        "longitude": "20.0",
                        "confidence": "n",
                        "brightness": "367",
                    },
                },
            }
        },
        "daynight": {"SNPP": {"N": 2}},
        "confidence_note": "The two summaries are separate.",
        "confidence": {"SNPP": {"kind": "viirs_lnh", "counts": {"n": 2}}},
        "brightness_367": {
            "viirs_snpp": {"by_confidence": {"n": 2}, "above_367": 0, "from_360_until_367": 0}
        },
        "weekly": {"SNPP": {"counts": {"2024-07-01 to 2024-07-07": 2}, "dates_with_zero_rows": ["2024-07-03"]}},
        "spatial": {
            "SNPP": {
                "occupied_cells": 1,
                "rows_in_cells": 2,
                "top_cells": [{"latitude_floor": 10, "longitude_floor": 20, "delivered_rows": 2}],
            }
        },
        "july7": {"SNPP": {"monthly_rows": 1, "sample_rows": 1, "difference": 0}},
    }
    rendered = render_eda(eda)
    assert "not fire size" in rendered
    assert "not interchangeable" in rendered
    for item in LIMITATIONS:
        assert item in rendered


def test_figures_write_the_monthly_names(tmp_path: Path) -> None:
    values = {
        "frp": np.array([1.0, 2.0]),
        "brightness": np.array([300.0, 367.0]),
        "latitude": np.array([10.0, -10.0]),
        "longitude": np.array([20.0, 30.0]),
    }
    scans = []
    for satellite, sensor in (("Terra", "modis"), ("Aqua", "modis"), ("N20", "viirs_noaa20"), ("N21", "viirs_noaa21"), ("SNPP", "viirs_snpp")):
        scans.append(
            {
                "sensor": sensor,
                "daily": {satellite: {"2024-07-01": 2}},
                "confidence": {f"{satellite}|80": 2} if sensor == "modis" else {f"{satellite}|n": 2},
                "daynight": {f"{satellite}|D": 1, f"{satellite}|N": 1},
                "arrays": {satellite: values},
            }
        )
    scans = [scans[0] | {"daily": {"Terra": scans[0]["daily"]["Terra"], "Aqua": scans[1]["daily"]["Aqua"]}, "confidence": {**scans[0]["confidence"], **scans[1]["confidence"]}, "daynight": {**scans[0]["daynight"], **scans[1]["daynight"]}, "arrays": {"Terra": values, "Aqua": values}}, scans[4], scans[2], scans[3]]
    names = write_figures(scans, tmp_path)
    assert names == list(FIGURE_NAMES)
    assert all((tmp_path / name).is_file() for name in FIGURE_NAMES)


def test_digest_buffer_rejects_a_partial_block() -> None:
    try:
        count_sorted_duplicates(bytearray(b"abc"))
    except ValueError as error:
        assert "16" in str(error)
    else:
        raise AssertionError("partial digest buffer was accepted")
