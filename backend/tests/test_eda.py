import csv
import hashlib
from pathlib import Path

import numpy as np
import pytest

from fire_data.contract import COLUMNS, RAW_DIR, SOURCES, SourceContract
from fire_data.eda import run_eda
from fire_data.eda_figures import FIGURE_NAMES, write_figures
from fire_data.eda_report import render_report
from fire_data.eda_spatial import (
    EARTH_RADIUS_M,
    cell_area_km2,
    count_grid,
    haversine_m,
    nearest_distances_m,
)
from fire_data.eda_summary import (
    CAVEATS,
    build_summary,
    summarize_confidence,
    summarize_hours,
    summarize_numeric,
)
from fire_data.eda_table import DetectionTable, load_source, read_source_rows

MODIS = SOURCES[0]


def _lookup(table: DetectionTable, line_numbers: set[int]) -> dict[int, dict[str, str]]:
    positions = {int(line): index for index, line in enumerate(table.line_number.tolist())}
    found = {}
    for line in line_numbers:
        index = positions[line]
        found[line] = {column: "" for column in COLUMNS}
        found[line]["latitude"] = format(float(table.latitude[index]), ".17g")
        found[line]["longitude"] = format(float(table.longitude[index]), ".17g")
        found[line]["frp"] = format(float(table.frp[index]), ".17g")
        found[line]["confidence"] = str(table.confidence[index])
        found[line]["satellite"] = str(table.satellite[index])
        found[line]["acq_time"] = f"{int(table.acq_hhmm[index]):04d}"
        found[line]["daynight"] = str(table.daynight[index])
        found[line]["scan"] = "1"
        found[line]["track"] = "1"
    return found


def make_table(
    *,
    source_id: str,
    satellite: str | list[str],
    latitude: list[float],
    longitude: list[float],
    frp: list[float],
    confidence: list[str],
    kind: str,
    daynight: list[str] | None = None,
    hour: list[int] | None = None,
) -> DetectionTable:
    count = len(frp)
    satellites = satellite if isinstance(satellite, list) else [satellite] * count
    hours = np.zeros(count, dtype=np.int8) if hour is None else np.asarray(hour, dtype=np.int8)
    nights = ["D"] * count if daynight is None else daynight
    return DetectionTable(
        source_id=source_id,
        archive=f"{source_id}.csv",
        archive_path="",
        confidence_kind=kind,
        line_number=np.arange(2, count + 2, dtype=np.int32),
        latitude=np.asarray(latitude, dtype=np.float64),
        longitude=np.asarray(longitude, dtype=np.float64),
        brightness=np.full(count, 300.0),
        scan=np.ones(count),
        track=np.ones(count),
        bright_t31=np.full(count, 290.0),
        frp=np.asarray(frp, dtype=np.float64),
        acq_hhmm=(hours.astype(np.uint16) * 100),
        hour_utc=hours,
        satellite=np.asarray(satellites, dtype="U8"),
        confidence=np.asarray(confidence, dtype="U8"),
        daynight=np.asarray(nights, dtype="U1"),
        dates=("2024-07-07",),
    )


def test_numeric_summary_keeps_zeros_and_the_maximum():
    values = np.array([0.0, 0.0, 1.0, 3.0, 10.0])

    stats = summarize_numeric(values)

    assert stats["count"] == 5
    assert stats["zero_count"] == 2
    assert stats["minimum"] == 0.0
    assert stats["maximum"] == 10.0
    assert stats["quantiles"]["0.000"] == 0.0
    assert stats["quantiles"]["1.000"] == 10.0
    assert stats["extreme_count"] >= 1
    assert stats["std"] == pytest.approx(float(np.std(values, ddof=1)))


def test_confidence_summaries_keep_the_original_scales():
    modis = summarize_confidence(np.array(["0", "0", "100"]), "modis_0_100")
    viirs = summarize_confidence(np.array(["l", "n", "h", "h"]), "viirs_lnh")

    assert modis["counts"] == {"0": 2, "100": 1}
    assert modis["proportions"]["0"] == pytest.approx(2 / 3)
    assert modis["median_integer"] == 0
    assert set(viirs["counts"]) == {"l", "n", "h"}
    assert viirs["median_integer"] is None
    assert set(modis["counts"]).isdisjoint(viirs["counts"])
    assert sum(viirs["proportions"].values()) == pytest.approx(1)


def test_utc_hour_uses_the_first_two_digits():
    summary = summarize_hours(
        np.array([0, 0, 1, 23], dtype=np.int8),
        np.array([0, 59, 100, 2359], dtype=np.uint16),
    )

    assert summary["counts"][0] == 2
    assert summary["counts"][1] == 1
    assert summary["counts"][23] == 1
    assert sum(summary["counts"]) == 4
    assert summary["distinct_timestamps"] == 4
    assert len(summary["counts"]) == 24


def test_degree_grid_places_edges_and_reports_spherical_area():
    interior, lat_edges, lon_edges = count_grid(np.array([0.5]), np.array([0.5]), 1.0)
    north_pole, _, _ = count_grid(np.array([90.0]), np.array([180.0]), 1.0)
    south_pole, _, _ = count_grid(np.array([-90.0]), np.array([-180.0]), 1.0)
    lat_bin = int(np.searchsorted(lat_edges, 0.5, side="right") - 1)
    lon_bin = int(np.searchsorted(lon_edges, 0.5, side="right") - 1)

    assert interior[lat_bin, lon_bin] == 1
    assert interior.sum() == 1
    assert north_pole[-1, -1] == 1
    assert south_pole[0, 0] == 1
    area = cell_area_km2(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    expected = (EARTH_RADIUS_M / 1000.0) ** 2 * np.radians(1.0) * np.sin(np.radians(1.0))
    assert area[0] == pytest.approx(expected)


def test_overlap_distance_matches_the_great_circle_at_five_kilometres():
    delta = float(np.degrees(5000.0 / EARTH_RADIUS_M))
    chord = nearest_distances_m(np.array([0.0]), np.array([0.0]), np.array([0.0]), np.array([delta]), 20_000.0)
    arc = haversine_m(0.0, 0.0, 0.0, delta)
    high_latitude = nearest_distances_m(
        np.array([70.0]),
        np.array([0.0]),
        np.array([70.0]),
        np.array([0.05]),
        20_000.0,
    )

    assert chord[0] == pytest.approx(arc, abs=0.001)
    assert arc == pytest.approx(5000.0, abs=0.001)
    assert high_latitude[0] == pytest.approx(haversine_m(70.0, 0.0, 70.0, 0.05), abs=0.001)
    missed = nearest_distances_m(np.array([0.0]), np.array([0.0]), np.array([0.0]), np.array([delta]), chord[0] - 1.0)
    assert np.isinf(missed[0])


def test_overlap_is_ordered_and_terra_is_separate_from_aqua():
    separation = float(
        nearest_distances_m(np.array([0.0]), np.array([0.0]), np.array([0.0]), np.array([0.002]), 20_000.0)[0]
    )
    modis = make_table(
        source_id="modis",
        satellite=["Terra", "Terra", "Aqua", "Aqua"],
        latitude=[0.0, 40.0, 0.0, 1.0],
        longitude=[0.0, 40.0, 0.002, 1.0],
        frp=[0.0, 10.0, 5.0, 1.0],
        confidence=["0", "100", "50", "50"],
        kind="modis_0_100",
        daynight=["D", "N", "D", "N"],
        hour=[0, 1, 23, 12],
    )
    noaa20 = make_table(
        source_id="viirs_noaa20",
        satellite="N20",
        latitude=[70.0],
        longitude=[10.0],
        frp=[3.0],
        confidence=["n"],
        kind="viirs_lnh",
        hour=[0],
    )

    summary = build_summary([modis, noaa20], (separation - 1.0, separation + 1.0, 5000.0), _lookup)
    pairs = {
        (pair["satellite_a"], pair["satellite_b"]): pair["thresholds"]
        for pair in summary["spatial_overlap"]["pairs"]
    }

    assert ("Terra", "Terra") not in pairs
    assert pairs[("Terra", "Aqua")][0]["detections_with_neighbor"] == 0
    assert pairs[("Terra", "Aqua")][1]["proportion"] == pytest.approx(0.5)
    assert pairs[("Aqua", "Terra")][1]["proportion"] == pytest.approx(0.5)
    assert pairs[("N20", "Terra")][2]["detections_with_neighbor"] == 0
    assert summary["sources"]["modis"]["satellites"]["Terra"]["detection_count"] == 2
    assert summary["sources"]["modis"]["satellites"]["Aqua"]["detection_count"] == 2
    assert summary["satellites"]["Terra"]["frp"]["zero_count"] == 1
    assert summary["satellites"]["Terra"]["frp"]["maximum"] == 10.0
    assert set(summary["satellites"]["Terra"]["confidence"]["counts"]).isdisjoint({"l", "n", "h"})
    assert summary["satellites"]["N20"]["confidence"]["median_integer"] is None
    assert "harmonization_factor" not in summary


def test_report_states_the_one_day_limits():
    modis = make_table(
        source_id="modis",
        satellite=["Terra", "Aqua"],
        latitude=[0.0, 1.0],
        longitude=[0.0, 1.0],
        frp=[0.0, 4.0],
        confidence=["20", "80"],
        kind="modis_0_100",
    )
    noaa20 = make_table(
        source_id="viirs_noaa20",
        satellite="N20",
        latitude=[2.0],
        longitude=[2.0],
        frp=[1.0],
        confidence=["h"],
        kind="viirs_lnh",
    )

    summary = build_summary([modis, noaa20], (1000.0,), _lookup)
    report = render_report(summary)

    for caveat in CAVEATS:
        assert caveat in report
    assert "one-day global observations" in report
    assert "2024-07-07" in report
    assert "acq_time is read as UTC HHMM" in report
    lowered = report.lower()
    for phrase in ("better sensor", "more fires", "harmonization factor of", "seasonal pattern"):
        assert phrase not in lowered


def test_small_summary_writes_figures(tmp_path: Path):
    modis = make_table(
        source_id="modis",
        satellite=["Terra", "Terra", "Aqua"],
        latitude=[0.0, 10.0, 0.0],
        longitude=[0.0, 10.0, 0.01],
        frp=[0.0, 8.0, 2.0],
        confidence=["0", "90", "40"],
        kind="modis_0_100",
    )
    noaa20 = make_table(
        source_id="viirs_noaa20",
        satellite=["N20", "N20"],
        latitude=[5.0, 6.0],
        longitude=[5.0, 6.0],
        frp=[1.0, 3.0],
        confidence=["l", "h"],
        kind="viirs_lnh",
    )
    summary = build_summary([modis, noaa20], (1000.0, 5000.0), _lookup)

    names = write_figures([modis, noaa20], summary, tmp_path)

    assert names == list(FIGURE_NAMES)
    for name in names:
        assert (tmp_path / name).read_bytes().startswith(b"\x89PNG")


def test_extreme_rows_keep_the_source_text(tmp_path: Path):
    archive = tmp_path / "mini.csv"
    archive.write_text(
        "\n".join(
            [
                ",".join(COLUMNS),
                "19.9768,41.4337,302.8,1.8,1.3,2024-07-07,0000,Aqua,MODIS,44,61.03,292.8,7.2,N,0",
                "20.0000,42.0000,310.0,1.1,1.1,2024-07-07,0031,Aqua,MODIS,80,61.03,290.0,7956.3,D,0",
                "21.0000,43.0000,305.0,1.2,1.2,2024-07-07,0100,Terra,MODIS,10,61.03,291.0,1.0,D,0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    source = SourceContract(
        source_id="modis",
        relative_path=Path("mini.csv"),
        satellites=frozenset({"Aqua", "Terra"}),
        instrument="MODIS",
        version="61.03",
        confidence="modis_0_100",
    )

    table = load_source(source, archive)
    summary = build_summary(
        [table],
        (1000.0,),
        lambda item, lines: read_source_rows(Path(item.archive_path), lines),
    )
    record = max(summary["extreme_frp"]["records"], key=lambda item: item["frp"])

    assert table.hour_utc.tolist() == [0, 0, 1]
    assert int(table.acq_hhmm[1]) == 31
    assert record["line_number"] == 3
    assert record["satellite"] == "Aqua"
    assert record["row"]["frp"] == "7956.3"
    assert record["row"]["latitude"] == "20.0000"
    assert record["row"]["acq_time"] == "0031"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest


def test_eda_refuses_to_write_into_the_raw_directory():
    with pytest.raises(ValueError, match="raw archive"):
        run_eda(RAW_DIR)
    with pytest.raises(ValueError, match="raw archive"):
        run_eda(RAW_DIR / "modis")


def test_extracted_archives_eda(tmp_path: Path):
    before = {source.relative_path.as_posix(): hashlib.sha256(source.path.read_bytes()).hexdigest() for source in SOURCES}

    summary = run_eda(tmp_path)

    after = {source.relative_path.as_posix(): hashlib.sha256(source.path.read_bytes()).hexdigest() for source in SOURCES}
    assert after == before
    assert summary["scope"] == {
        "label": "one-day global observations",
        "dates": ["2024-07-07"],
        "detection_count": 277_259,
        "caveats": list(CAVEATS),
        "populations": summary["scope"]["populations"],
    }
    assert summary["sources"]["modis"]["detection_count"] == 20_410
    assert summary["sources"]["viirs_noaa20"]["detection_count"] == 82_372
    assert summary["sources"]["viirs_noaa21"]["detection_count"] == 87_637
    assert summary["sources"]["viirs_snpp"]["detection_count"] == 86_840
    terra = summary["satellites"]["Terra"]["detection_count"]
    aqua = summary["satellites"]["Aqua"]["detection_count"]
    assert terra + aqua == 20_410
    assert terra > 0 and aqua > 0
    assert summary["sources"]["modis"]["frp"]["maximum"] == pytest.approx(7956.3)
    assert summary["sources"]["viirs_noaa20"]["frp"]["maximum"] == pytest.approx(1168.99)
    assert summary["sources"]["viirs_noaa21"]["frp"]["maximum"] == pytest.approx(1740.42)
    assert summary["sources"]["viirs_snpp"]["frp"]["maximum"] == pytest.approx(974.25)
    for source_id in ("modis", "viirs_noaa20", "viirs_noaa21", "viirs_snpp"):
        assert summary["sources"][source_id]["frp"]["zero_count"] > 0
        assert summary["sources"][source_id]["frp"]["extreme_count"] >= 1
    assert set(summary["sources"]["modis"]["confidence"]["counts"]).isdisjoint({"l", "n", "h"})
    for source_id in ("viirs_noaa20", "viirs_noaa21", "viirs_snpp"):
        assert set(summary["sources"][source_id]["confidence"]["counts"]) <= {"l", "n", "h"}
    assert summary["spatial_overlap"]["thresholds_m"] == [375.0, 1000.0, 5000.0]
    assert all(pair["satellite_a"] != pair["satellite_b"] for pair in summary["spatial_overlap"]["pairs"])
    report = (tmp_path / "eda_report.md").read_text(encoding="utf-8")
    for caveat in CAVEATS:
        assert caveat in report
    assert "7956.3" in report
    maximum = max(summary["extreme_frp"]["records"], key=lambda item: item["frp"])
    with next(source.path for source in SOURCES if source.source_id == maximum["source_id"]).open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = csv.reader(handle)
        next(rows)
        stored = None
        for line_number, row in enumerate(rows, start=2):
            if line_number == maximum["line_number"]:
                stored = row
                break
    assert stored == [maximum["row"][column] for column in COLUMNS]
    for name in FIGURE_NAMES:
        figure = tmp_path / "figures" / name
        assert figure.read_bytes().startswith(b"\x89PNG")
