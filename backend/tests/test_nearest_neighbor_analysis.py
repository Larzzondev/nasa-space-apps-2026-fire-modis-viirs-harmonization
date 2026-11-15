import numpy as np

from fire_data.eda_spatial import EARTH_RADIUS_M, haversine_m
from fire_data.nearest_neighbor_analysis import (
    PAIR_WINDOWS,
    assignment_comparison,
    analyze_pair,
    detail_window,
    group_nearest,
)
from fire_data.spatiotemporal_analysis import ObservationTable


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
        confidence=np.array([int(row.get("confidence", 80 if modis else 2)) for row in rows], dtype=np.int16),
    )


def _east(distance_m: float) -> float:
    return float(np.degrees(distance_m / EARTH_RADIUS_M))


def _pair(tables, pair, windows, days, radii=(375.0, 1_000.0, 5_000.0)):
    return analyze_pair(
        tables,
        pair,
        windows,
        radii_m=radii,
        days=days,
        compare_assignment=False,
    )


def _threshold(result, radius, window):
    return next(item for item in result["thresholds"] if item["radius_m"] == radius and item["max_delta_minutes"] == window)


def test_windows_follow_the_sensor_pair() -> None:
    assert detail_window((30,)) == 30
    assert detail_window((60,)) == 60
    specs = dict(PAIR_WINDOWS)
    assert specs[("Terra", "Aqua")] == (30,)
    assert specs[("MODIS", "SNPP")] == (30,)
    assert specs[("SNPP", "N20")] == (30, 60)
    assert specs[("N20", "N21")] == (60,)


def test_nearest_neighbor_uses_geodesic_distance_and_the_closer_row() -> None:
    separation = 800.0
    tables = {
        "Terra": _table("Terra", [{"day": 16, "minute": 600, "lat": 0.0, "lon": 0.0, "frp": 20.0}]),
        "Aqua": _table(
            "Aqua",
            [
                {"day": 16, "minute": 610, "lat": 0.0, "lon": _east(separation), "frp": 10.0},
                {"day": 16, "minute": 610, "lat": 0.0, "lon": _east(2_000.0), "frp": 8.0},
            ],
        ),
    }
    result = _pair(tables, ("Terra", "Aqua"), (30,), [16])
    near = _threshold(result, 1_000.0, 30)
    far = _threshold(result, 375.0, 30)
    wide = _threshold(result, 5_000.0, 30)
    assert near["matched_reference_detections"] == 1
    assert near["unmatched_reference_detections"] == 0
    assert far["matched_reference_detections"] == 0
    assert wide["ambiguity"]["two_to_five_candidates"] == 1
    assert wide["eligible_candidate_pairs"] == 2
    assert abs(near["nearest_distance_m"]["bin_start"]) <= 800.0
    expected = haversine_m(0.0, 0.0, 0.0, _east(separation))
    assert near["nearest_distance_m"]["bin_end"] > expected
    assert near["same_fire"] == "not_assessed"
    assert near["nearest_neighbor_is_same_fire"] is False
    ratio = near["frp_directed"]["ratio_other_over_reference"]
    assert ratio["count"] == 1
    assert abs(ratio["p50"] - 0.5) < 1e-9
    assert ratio["ratio_is_a_harmonization_coefficient"] is False


def test_time_limit_skips_a_closer_row_and_sixty_minutes_keeps_it() -> None:
    tables = {
        "N20": _table("N20", [{"day": 7, "minute": 600, "lat": 0.0, "lon": 0.0}]),
        "N21": _table(
            "N21",
            [
                {"day": 7, "minute": 650, "lat": 0.0, "lon": _east(400.0)},
                {"day": 7, "minute": 610, "lat": 0.0, "lon": _east(1_500.0)},
            ],
        ),
    }
    short = _pair(tables, ("N20", "N21"), (30,), [7])
    long = _pair(tables, ("N20", "N21"), (60,), [7])
    assert _threshold(short, 5_000.0, 30)["nearest_distance_m"]["bin_start"] >= 1_000.0
    assert _threshold(long, 1_000.0, 60)["matched_reference_detections"] == 1
    assert _threshold(long, 1_000.0, 60)["nearest_distance_m"]["bin_end"] <= 1_000.0


def test_mutual_nearest_neighbors_are_not_every_directed_pair() -> None:
    tables = {
        "SNPP": _table(
            "SNPP",
            [
                {"day": 4, "minute": 700, "lat": 0.0, "lon": 0.0},
                {"day": 4, "minute": 700, "lat": 0.0, "lon": _east(250.0)},
            ],
        ),
        "N20": _table(
            "N20",
            [
                {"day": 4, "minute": 710, "lat": 0.0, "lon": _east(100.0)},
                {"day": 4, "minute": 710, "lat": 0.0, "lon": _east(500.0)},
            ],
        ),
    }
    result = _pair(tables, ("SNPP", "N20"), (30,), [4], radii=(1_000.0,))
    item = _threshold(result, 1_000.0, 30)
    assert item["matched_reference_detections"] == 2
    assert item["mutual_nearest_neighbors"] == 1
    assert item["mutual_proportion_of_directed"] == 0.5
    assert item["mutual_nearest_neighbor_is_same_fire"] is False


def test_ambiguity_bins_and_more_than_five_partners() -> None:
    partners = [{"day": 3, "minute": 400, "lat": 0.0, "lon": _east(100.0 * (index + 1))} for index in range(6)]
    tables = {
        "Terra": _table("Terra", [{"day": 3, "minute": 400, "lat": 0.0, "lon": 0.0}, {"day": 3, "minute": 400, "lat": 10.0, "lon": 10.0}]),
        "Aqua": _table("Aqua", partners),
    }
    result = _pair(tables, ("Terra", "Aqua"), (30,), [3], radii=(1_000.0,))
    ambiguity = _threshold(result, 1_000.0, 30)["ambiguity"]
    assert ambiguity["zero_candidates"] == 1
    assert ambiguity["more_than_five_candidates"] == 1
    assert sum(ambiguity[key] for key in ("zero_candidates", "one_candidate", "two_to_five_candidates", "more_than_five_candidates")) == 2


def test_one_to_one_uses_each_detection_once_and_keeps_calendar_order() -> None:
    tables = {
        "Terra": _table(
            "Terra",
            [
                {"day": 16, "minute": 23 * 60 + 50, "lat": 0.0, "lon": 0.0},
                {"day": 17, "minute": 20, "lat": 0.0, "lon": _east(100.0)},
            ],
        ),
        "Aqua": _table(
            "Aqua",
            [
                {"day": 16, "minute": 12 * 60, "lat": 30.0, "lon": 30.0},
                {"day": 17, "minute": 10, "lat": 0.0, "lon": _east(500.0)},
            ],
        ),
    }
    result = _pair(tables, ("Terra", "Aqua"), (30,), [16, 17], radii=(1_000.0,))
    item = _threshold(result, 1_000.0, 30)
    assert item["matched_reference_detections"] == 2
    assert item["assigned_one_to_one_pairs"] == 1
    assert result["daily"][0]["assigned_one_to_one_pairs"] == 1
    assert result["daily"][1]["assigned_one_to_one_pairs"] == 0
    assert item["one_to_one_is_physical_truth"] is False


def test_midnight_neighbor_is_counted_once_and_can_be_mutual() -> None:
    tables = {
        "Terra": _table("Terra", [{"day": 16, "minute": 23 * 60 + 50, "lat": 0.0, "lon": 0.0}]),
        "Aqua": _table(
            "Aqua",
            [
                {"day": 16, "minute": 12 * 60, "lat": 25.0, "lon": 25.0},
                {"day": 17, "minute": 10, "lat": 0.0, "lon": _east(200.0)},
            ],
        ),
    }
    result = _pair(tables, ("Terra", "Aqua"), (60,), [16, 17], radii=(1_000.0,))
    assert result["daily"][0]["status"] == "compared"
    assert result["daily"][0]["matched_reference_detections"] == 1
    assert result["daily"][1]["status"] == "reference_absent"
    assert result["daily"][1]["matched_reference_detections"] is None
    assert _threshold(result, 1_000.0, 60)["matched_reference_detections"] == 1
    assert _threshold(result, 1_000.0, 60)["mutual_nearest_neighbors"] == 1


def test_absent_date_is_not_stored_as_zero() -> None:
    tables = {
        "SNPP": _table("SNPP", [{"day": 16, "minute": 700, "lat": 0.0, "lon": 0.0}]),
        "N20": _table(
            "N20",
            [
                {"day": 16, "minute": 710, "lat": 0.0, "lon": _east(300.0)},
                {"day": 25, "minute": 700, "lat": 0.0, "lon": 1.0},
            ],
        ),
    }
    result = _pair(tables, ("SNPP", "N20"), (30,), [16, 25], radii=(1_000.0,))
    assert result["excluded_dates"] == [{"date": "2024-07-25", "status": "reference_absent"}]
    assert result["daily"][1]["matched_reference_detections"] is None
    assert result["daily"][1]["zero_detections"] is False
    assert result["missing_dates_filled"] is False
    assert _threshold(result, 1_000.0, 30)["matched_reference_detections"] == 1
    assert _threshold(result, 1_000.0, 30)["reference_rows_on_compared_dates"] == 1


def test_nonpositive_frp_stays_in_the_match_and_out_of_the_ratio() -> None:
    tables = {
        "Terra": _table(
            "Terra",
            [
                {"day": 2, "minute": 500, "lat": 0.0, "lon": 0.0, "frp": 0.0},
                {"day": 2, "minute": 500, "lat": 1.0, "lon": 1.0, "frp": 40.0},
            ],
        ),
        "Aqua": _table(
            "Aqua",
            [
                {"day": 2, "minute": 505, "lat": 0.0, "lon": _east(200.0), "frp": 12.0},
                {"day": 2, "minute": 505, "lat": 1.0, "lon": 1.0 + _east(200.0), "frp": 0.0},
            ],
        ),
    }
    result = _pair(tables, ("Terra", "Aqua"), (30,), [2], radii=(1_000.0,))
    item = _threshold(result, 1_000.0, 30)
    assert item["matched_reference_detections"] == 2
    ratio = item["frp_directed"]["ratio_other_over_reference"]
    assert ratio["count"] == 0
    assert item["frp_directed"]["excluded_nonpositive_frp_pairs"] == 2
    assert item["frp_directed"]["zero_frp_rows_removed_from_source"] is False
    assert tables["Terra"].count == 2


def test_hungarian_subset_can_assign_more_pairs_than_greedy() -> None:
    more_rows = assignment_comparison(
        np.array([10, 10, 20], dtype=np.int64),
        np.array([30, 40, 30], dtype=np.int64),
        np.array([1.0, 4.0, 2.0]),
    )
    assert more_rows["greedy_assigned_pairs"] == 1
    assert more_rows["hungarian_assigned_pairs"] == 2
    shorter = assignment_comparison(
        np.array([10, 10, 20, 20], dtype=np.int64),
        np.array([30, 40, 30, 40], dtype=np.int64),
        np.array([5.0, 6.0, 5.5, 100.0]),
    )
    assert shorter["greedy_assigned_pairs"] == shorter["hungarian_assigned_pairs"] == 2
    assert shorter["hungarian_distance_sum_m"] < shorter["greedy_distance_sum_m"]
    assert shorter["subset_is_the_full_month"] is False
    assert shorter["one_to_one_is_physical_truth"] is False


def test_group_nearest_reports_the_gap_and_breaks_ties_by_partner_id() -> None:
    nearest_a, nearest_b, distance, _, counts, second = group_nearest(
        np.array([5, 5, 5], dtype=np.int64),
        np.array([9, 3, 4], dtype=np.int64),
        np.array([100.0, 100.0, 250.0]),
        np.array([1, 1, 1], dtype=np.int32),
    )
    assert nearest_a.tolist() == [5]
    assert nearest_b.tolist() == [3]
    assert distance.tolist() == [100.0]
    assert counts.tolist() == [3]
    assert second.tolist() == [100.0]
