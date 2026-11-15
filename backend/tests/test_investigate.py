import hashlib
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest

from fire_data.contract import COLUMNS, RAW_DIR, SOURCES
from fire_data.eda_spatial import haversine_m
from fire_data.investigate import (
    build_investigation,
    decimal_places,
    great_circle_distance_m,
    run_investigation,
    scan_archives,
    select_nearby,
    utc_minutes,
)
from fire_data.investigate_report import classify, render_report

VIIRS = [source for source in SOURCES if source.source_id.startswith("viirs")]
MODIS = SOURCES[0]


def _row(**overrides: str) -> str:
    values = {
        "latitude": "48.1499",
        "longitude": "-120.4706",
        "brightness": "367",
        "scan": "0.40",
        "track": "0.36",
        "acq_date": "2024-07-07",
        "acq_time": "2232",
        "satellite": "N20",
        "instrument": "VIIRS",
        "confidence": "h",
        "version": "2",
        "bright_t31": "300.00",
        "frp": "10.00",
        "daynight": "D",
        "type": "0",
    }
    values.update(overrides)
    return ",".join(values[column] for column in COLUMNS)


def _write(path: Path, rows: list[str]) -> None:
    path.write_text(",".join(COLUMNS) + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_decimal_places_and_utc_minutes_keep_the_stored_text_rules():
    assert decimal_places("367") == 0
    assert decimal_places("367.0") == 1
    assert decimal_places("366.99") == 2
    assert utc_minutes("0031") == 31
    assert utc_minutes("2232") == 22 * 60 + 32


def test_great_circle_distance_matches_the_scalar_haversine():
    distance = great_circle_distance_m(48.0, -120.0, np.array([48.0]), np.array([-120.01]))

    assert distance[0] == pytest.approx(haversine_m(48.0, -120.0, 48.0, -120.01))


def test_brightness_strings_stay_distinct_when_they_parse_to_the_same_number(tmp_path: Path):
    archive = tmp_path / "viirs.csv"
    _write(
        archive,
        [
            _row(brightness="366.99", confidence="n", frp="1.00"),
            _row(brightness="367", confidence="h", frp="2.00"),
            _row(brightness="367.0", confidence="n", frp="3.00"),
            _row(brightness="367.00", confidence="l", frp="4.00"),
            _row(brightness="368", confidence="h", frp="5.00"),
        ],
    )
    source = next(item for item in VIIRS if item.source_id == "viirs_noaa20")

    scan = scan_archives((source,), {source.source_id: archive})
    record = scan["brightness"][source.source_id]

    assert record["numeric_ceiling"] == 3
    assert record["above_ceiling"] == 1
    assert record["ceiling_texts"] == {"367": 1, "367.0": 1, "367.00": 1}
    assert record["string_counts_from_366"]["366.99"] == 1
    assert record["confidence_at_ceiling"] == {"h": 1, "n": 1, "l": 1}
    assert record["high_confidence_below_ceiling"] == 0
    assert record["high_confidence_at_ceiling"] == 1


def test_nearby_search_excludes_the_target_and_does_not_assign_a_fire():
    target = {
        "source_id": "modis",
        "line_number": 10,
        "row": {
            "latitude": "48.1499",
            "longitude": "-120.4706",
            "acq_time": "2232",
            "frp": "7956.3",
        },
    }
    same_row = {
        "source_id": "modis",
        "archive": "modis.csv",
        "line_number": 10,
        "row": dict(target["row"]),
    }
    close = {
        "source_id": "modis",
        "archive": "modis.csv",
        "line_number": 11,
        "row": {
            "latitude": "48.1577",
            "longitude": "-120.4744",
            "acq_time": "2232",
            "satellite": "Aqua",
            "frp": "7328.1",
        },
    }
    later = {
        "source_id": "viirs_noaa20",
        "archive": "n20.csv",
        "line_number": 4,
        "row": {
            "latitude": "48.15",
            "longitude": "-120.47",
            "acq_time": "2302",
            "satellite": "N20",
            "frp": "12.0",
        },
    }

    nearby = select_nearby([same_row, close, later], [target], radius_m=5_000)

    assert [item["line_number"] for item in nearby] == [4, 11]
    assert nearby[0]["delta_minutes"] == 30
    assert nearby[1]["same_utc_minute"] is True
    assert nearby[1]["row"]["frp"] == "7328.1"
    assert all("same_fire" not in item for item in nearby)
    assert nearby[1]["distance_m"] == pytest.approx(
        haversine_m(48.1499, -120.4706, 48.1577, -120.4744)
    )


def test_report_keeps_facts_hypotheses_and_open_questions_apart():
    summary = {
        "brightness": {
            "satellites": [
                {
                    "source_id": "viirs_noaa20",
                    "detection_count": 4,
                    "decimal_place_counts": {"0": 1, "2": 3},
                    "maximum_text": "367",
                    "numeric_equal_367": 2,
                    "share_equal_367": 0.5,
                    "above_367": 0,
                    "ceiling_texts": {"367": 2},
                    "frequency_from_366_k": [
                        {"text": "366.99", "value": "366.99", "count": 2},
                        {"text": "367", "value": "367", "count": 2},
                    ],
                    "confidence_at_367": {"h": 1, "n": 1},
                    "high_confidence_below_367": 3,
                    "daynight_at_367": {"D": 2},
                    "from_366_below_367": 2,
                    "bright_t31_at_367": {"minimum": 290.0, "median": 300.0, "maximum": 310.0},
                    "frp_at_367": {"minimum": 1.0, "median": 4.0, "maximum": 9.0},
                }
            ]
        },
        "extreme_frp": {
            "distance_method": "Great-circle distance on the exploratory sphere.",
            "pair_distance_m": 900.0,
            "pair_delta_minutes": 0,
            "targets": [
                {
                    "source_id": "modis",
                    "archive": "modis/fire.csv",
                    "line_number": 20,
                    "row": {column: "0" for column in COLUMNS},
                }
            ],
            "nearby_counts": [
                {
                    "target_line_number": 20,
                    "target_frp": "7956.3",
                    "counts": [
                        {
                            "radius_m": 1000.0,
                            "max_delta_minutes": 0,
                            "count": 1,
                            "by_satellite": {"Aqua": 1},
                        }
                    ],
                }
            ],
            "nearby": [],
        },
    }
    summary["extreme_frp"]["targets"][0]["row"].update(
        {
            "latitude": "48.1499",
            "longitude": "-120.4706",
            "acq_time": "2232",
            "acq_date": "2024-07-07",
            "frp": "7956.3",
            "confidence": "75",
            "brightness": "400.0",
            "bright_t31": "320.0",
            "scan": "3.9",
            "track": "1.8",
            "daynight": "D",
            "type": "0",
            "version": "61.03",
            "satellite": "Aqua",
            "instrument": "MODIS",
        }
    )

    report = render_report(summary)
    labels = classify(summary)

    assert "## Verified facts" in report
    assert "## Hypotheses" in report
    assert "## Unresolved questions" in report
    assert "nominal saturation temperature of 367 K" in report
    assert "not classified as the same fire" in report
    assert "7956.3" in report
    assert "366.99" in report
    assert all("same fire" not in fact.lower() or "not" in fact.lower() for fact in labels["facts"])
    assert any("not classified as the same fire" in item for item in labels["unresolved"])


def test_small_archives_preserve_the_extreme_source_text(tmp_path: Path):
    n20 = tmp_path / "n20.csv"
    n21 = tmp_path / "n21.csv"
    snpp = tmp_path / "snpp.csv"
    modis = tmp_path / "modis.csv"
    _write(n20, [_row(brightness="367", satellite="N20", frp="8.00")])
    _write(n21, [_row(brightness="366.50", satellite="N21", instrument="VIIRS", confidence="n", frp="8.00")])
    _write(snpp, [_row(brightness="367.00", satellite="SNPP", instrument="SNPP", confidence="h", frp="8.00")])
    _write(
        modis,
        [
            _row(
                latitude="48.1499",
                longitude="-120.4706",
                brightness="480.5",
                scan="3.9",
                track="1.8",
                acq_time="2232",
                satellite="Aqua",
                instrument="MODIS",
                confidence="75",
                version="61.03",
                bright_t31="330.0",
                frp="7956.3",
            ),
            _row(
                latitude="48.1577",
                longitude="-120.4744",
                brightness="470.0",
                scan="3.9",
                track="1.8",
                acq_time="2232",
                satellite="Aqua",
                instrument="MODIS",
                confidence="0",
                version="61.03",
                bright_t31="329.0",
                frp="7328.1",
            ),
            _row(
                latitude="48.20",
                longitude="-120.50",
                brightness="320.0",
                scan="1.0",
                track="1.0",
                acq_time="1900",
                satellite="Terra",
                instrument="MODIS",
                confidence="50",
                version="61.03",
                frp="20.0",
            ),
        ],
    )
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (n20, n21, snpp, modis)}
    paths = {
        "viirs_noaa20": n20,
        "viirs_noaa21": n21,
        "viirs_snpp": snpp,
        "modis": modis,
    }

    summary = build_investigation(tuple(SOURCES), paths)

    assert hashlib.sha256(n20.read_bytes()).hexdigest() == before[n20]
    assert [Decimal(item["row"]["frp"]) for item in summary["extreme_frp"]["targets"]] == [
        Decimal("7956.3"),
        Decimal("7328.1"),
    ]
    assert summary["extreme_frp"]["targets"][0]["row"]["confidence"] == "75"
    assert summary["extreme_frp"]["targets"][1]["row"]["confidence"] == "0"
    assert summary["extreme_frp"]["pair_delta_minutes"] == 0
    assert summary["extreme_frp"]["pair_distance_m"] == pytest.approx(
        haversine_m(48.1499, -120.4706, 48.1577, -120.4744)
    )
    aqua_neighbors = [
        item
        for item in summary["extreme_frp"]["nearby"]
        if item["target_frp"] == "7956.3" and item["satellite"] == "Aqua"
    ]
    assert aqua_neighbors[0]["row"]["frp"] == "7328.1"
    assert summary["brightness"]["satellites"][0]["numeric_equal_367"] == 1
    assert summary["brightness"]["satellites"][0]["above_367"] == 0


def test_investigation_refuses_the_raw_directory():
    with pytest.raises(ValueError, match="raw archive"):
        run_investigation(RAW_DIR)


def test_extracted_archives_anomaly_investigation(tmp_path: Path):
    raw_before = {
        source.relative_path.as_posix(): hashlib.sha256(source.path.read_bytes()).hexdigest() for source in SOURCES
    }
    eda_paths = [
        Path("reports/eda_report.md"),
        Path("reports/eda_summary.json"),
    ]
    eda_before = {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in eda_paths if path.exists()}

    summary = run_investigation(tmp_path)

    raw_after = {
        source.relative_path.as_posix(): hashlib.sha256(source.path.read_bytes()).hexdigest() for source in SOURCES
    }
    eda_after = {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in eda_paths if path.exists()}
    assert raw_after == raw_before
    assert eda_after == eda_before
    by_source = {item["source_id"]: item for item in summary["brightness"]["satellites"]}
    for source_id in ("viirs_noaa20", "viirs_noaa21", "viirs_snpp"):
        assert by_source[source_id]["above_367"] == 0
        assert by_source[source_id]["numeric_equal_367"] > 0
        assert Decimal(by_source[source_id]["maximum_value"]) == Decimal("367")
    frp_values = {Decimal(item["row"]["frp"]) for item in summary["extreme_frp"]["targets"]}
    assert frp_values == {Decimal("7956.3"), Decimal("7328.1")}
    assert summary["extreme_frp"]["pair_delta_minutes"] == 0
    report = (tmp_path / "anomaly_investigation.md").read_text(encoding="utf-8")
    assert "## Verified facts" in report
    assert "## Hypotheses" in report
    assert "## Unresolved questions" in report
    assert "not classified as the same fire" in report
    assert (tmp_path / "anomaly_summary.json").exists()
