import numpy as np

from fire_data.eda_spatial import EARTH_RADIUS_M, haversine_m, lonlat_to_ecef
from fire_data.spatiotemporal_analysis import (
    ObservationTable,
    candidate_pairs,
    match_sensor_pair,
    summarize_days,
)


def _table(satellite: str, rows: list[dict[str, float | int | str]]) -> ObservationTable:
    count = len(rows)
    modis = satellite in {"Terra", "Aqua"}
    return ObservationTable(
        satellite=satellite,
        instrument="MODIS" if modis else "VIIRS",
        confidence_scale="modis_0_100" if modis else "viirs_flag",
        day=np.array([int(row["day"]) for row in rows], dtype=np.int8),
        minute=np.array([int(row["minute"]) for row in rows], dtype=np.int16),
        latitude=np.array([float(row["lat"]) for row in rows], dtype=np.float64),
        longitude=np.array([float(row["lon"]) for row in rows], dtype=np.float64),
        frp=np.array([float(row.get("frp", 10.0)) for row in rows], dtype=np.float64),
        brightness=np.full(count, 320.0),
        scan=np.full(count, 0.4),
        track=np.full(count, 0.4),
        daynight=np.array([0 if row.get("daynight", "D") == "D" else 1 for row in rows], dtype=np.int8),
        confidence=np.array([int(row.get("confidence", 0)) for row in rows], dtype=np.int16),
    )


def _east(distance_m: float) -> float:
    return float(np.degrees(distance_m / EARTH_RADIUS_M))


def test_geodesic_matches_haversine_and_uses_the_tree() -> None:
    separation = 1_000.0
    longitude = _east(separation)
    ecef_a = lonlat_to_ecef(np.array([0.0]), np.array([0.0]))
    ecef_b = lonlat_to_ecef(np.array([0.0]), np.array([longitude]))
    idx_a, idx_b, distance, delta = candidate_pairs(
        ecef_a,
        np.array([600]),
        np.array([0.0]),
        np.array([0.0]),
        ecef_b,
        np.array([605]),
        np.array([0.0]),
        np.array([longitude]),
        max_geodesic_m=5_000.0,
        max_delta_minutes=60,
    )
    assert idx_a.tolist() == [0]
    assert idx_b.tolist() == [0]
    assert abs(float(distance[0]) - haversine_m(0.0, 0.0, 0.0, longitude)) < 0.05
    assert int(delta[0]) == 5


def test_thresholds_keep_direction_and_drop_far_pairs() -> None:
    tables = {
        "Terra": _table("Terra", [{"day": 16, "minute": 720, "lat": 0.0, "lon": 0.0}]),
        "Aqua": _table("Aqua", [{"day": 16, "minute": 730, "lat": 0.0, "lon": _east(800.0)}]),
    }
    result = match_sensor_pair(tables, ("Terra", "Aqua"), 16, radii_m=(375.0, 750.0, 1_000.0), windows_min=(5, 15))
    assert result["status"] == "compared"
    assert result["thresholds"]["375_15"]["candidate_pairs"] == 0
    assert result["thresholds"]["750_5"]["candidate_pairs"] == 0
    assert result["thresholds"]["1000_15"]["candidate_pairs"] == 1
    assert result["thresholds"]["1000_15"]["reference_detections_with_candidate"] == 1
    assert result["same_fire"] == "not_assessed"


def test_tile_boundary_and_antimeridian_are_found() -> None:
    boundary = candidate_pairs(
        lonlat_to_ecef(np.array([9.999]), np.array([0.0])),
        np.array([0]),
        np.array([9.999]),
        np.array([0.0]),
        lonlat_to_ecef(np.array([10.001]), np.array([0.0])),
        np.array([1]),
        np.array([10.001]),
        np.array([0.0]),
        max_geodesic_m=1_000.0,
        max_delta_minutes=5,
    )
    assert boundary[0].size == 1
    wrapped = candidate_pairs(
        lonlat_to_ecef(np.array([0.0]), np.array([179.99])),
        np.array([0]),
        np.array([0.0]),
        np.array([179.99]),
        lonlat_to_ecef(np.array([0.0]), np.array([-179.99])),
        np.array([2]),
        np.array([0.0]),
        np.array([-179.99]),
        max_geodesic_m=5_000.0,
        max_delta_minutes=60,
    )
    assert wrapped[0].size == 1
    assert float(wrapped[2][0]) < 5_000.0
    too_far = candidate_pairs(
        lonlat_to_ecef(np.array([0.0]), np.array([179.99])),
        np.array([0]),
        np.array([0.0]),
        np.array([179.99]),
        lonlat_to_ecef(np.array([0.0]), np.array([-179.99])),
        np.array([2]),
        np.array([0.0]),
        np.array([-179.99]),
        max_geodesic_m=2_000.0,
        max_delta_minutes=60,
    )
    assert too_far[0].size == 0


def test_sensor_pairs_stay_separate_and_absent_dates_are_not_zero() -> None:
    tables = {
        "Terra": _table("Terra", [{"day": 16, "minute": 720, "lat": 0.0, "lon": 0.0, "confidence": 80}]),
        "Aqua": _table("Aqua", [{"day": 16, "minute": 725, "lat": 0.0, "lon": _east(200.0), "confidence": 90}]),
        "SNPP": _table(
            "SNPP",
            [{"day": 16, "minute": 722, "lat": 0.0, "lon": _east(100.0), "confidence": 2, "daynight": "N"}],
        ),
        "N20": _table("N20", [{"day": 16, "minute": 700, "lat": 20.0, "lon": 20.0, "confidence": 1}, {"day": 25, "minute": 700, "lat": 20.0, "lon": 20.0, "confidence": 0}]),
    }
    terra_aqua = match_sensor_pair(tables, ("Terra", "Aqua"), 16)
    modis_snpp = match_sensor_pair(tables, ("MODIS", "SNPP"), 16)
    snpp_same_day = match_sensor_pair(tables, ("SNPP", "N20"), 16)
    snpp_absent = match_sensor_pair(tables, ("SNPP", "N20"), 25)
    assert terra_aqua["thresholds"]["1000_30"]["candidate_pairs"] == 1
    assert modis_snpp["thresholds"]["1000_30"]["candidate_pairs"] == 2
    assert snpp_same_day["status"] == "compared"
    assert snpp_same_day["thresholds"]["5000_60"]["candidate_pairs"] == 0
    assert snpp_absent["status"] == "reference_absent"
    assert snpp_absent["candidate_pairs"] is None
    assert snpp_absent["zero_detections"] is False
    summary = summarize_days(("SNPP", "N20"), [snpp_same_day, snpp_absent])
    assert summary["thresholds"][0]["candidate_pairs"] == 0
    assert summary["excluded_dates"] == [{"date": "2024-07-25", "status": "reference_absent"}]
    assert summary["candidate_pairs_are_unique_fires"] is False


def test_one_target_can_form_two_candidate_pairs() -> None:
    tables = {
        "N20": _table(
            "N20",
            [
                {"day": 7, "minute": 100, "lat": 0.0, "lon": 0.0},
                {"day": 7, "minute": 101, "lat": 0.0, "lon": _east(100.0)},
            ],
        ),
        "N21": _table("N21", [{"day": 7, "minute": 102, "lat": 0.0, "lon": _east(40.0)}]),
    }
    result = match_sensor_pair(tables, ("N20", "N21"), 7, radii_m=(375.0,), windows_min=(5,))
    row = result["thresholds"]["375_5"]
    assert row["candidate_pairs"] == 2
    assert row["reference_detections_with_candidate"] == 2
    assert row["other_detections_on_this_date_with_candidate"] == 1


def test_midnight_window_is_counted_once_for_the_reference_date() -> None:
    tables = {
        "Terra": _table("Terra", [{"day": 16, "minute": 23 * 60 + 50, "lat": 0.0, "lon": 0.0}]),
        "Aqua": _table(
            "Aqua",
            [
                {"day": 16, "minute": 12 * 60, "lat": 40.0, "lon": 40.0},
                {"day": 17, "minute": 10, "lat": 0.0, "lon": _east(200.0)},
            ],
        ),
    }
    owned = match_sensor_pair(tables, ("Terra", "Aqua"), 16, radii_m=(1_000.0,), windows_min=(60,))
    other_day = match_sensor_pair(tables, ("Terra", "Aqua"), 17, radii_m=(1_000.0,), windows_min=(60,))
    assert owned["status"] == "compared"
    assert owned["thresholds"]["1000_60"]["candidate_pairs"] == 1
    assert other_day["status"] == "reference_absent"
    assert other_day["candidate_pairs"] is None
