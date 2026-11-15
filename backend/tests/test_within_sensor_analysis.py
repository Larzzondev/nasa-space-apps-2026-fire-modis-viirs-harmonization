import numpy as np
import pytest

from fire_data.eda_spatial import EARTH_RADIUS_M, haversine_m
from fire_data.spatiotemporal_analysis import AnalysisError, ObservationTable
from fire_data.within_sensor_analysis import (
    analyze_sensor,
    coordinate_inventory,
    dbscan_labels,
    duplicate_inventory,
    labels_from_pairs,
    margin_indices,
    nearest_other,
    render_markdown,
    representative_day,
    write_figures,
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
        brightness=np.array([float(row.get("brightness", 320.0)) for row in rows], dtype=np.float64),
        scan=np.array([float(row.get("scan", 0.4)) for row in rows], dtype=np.float64),
        track=np.array([float(row.get("track", 0.36)) for row in rows], dtype=np.float64),
        daynight=np.array([0 if row.get("daynight", "D") == "D" else 1 for row in rows], dtype=np.int8),
        confidence=np.array([int(row.get("confidence", 80 if modis else 2)) for row in rows], dtype=np.int16),
    )


def _east(distance_m: float) -> float:
    return float(np.degrees(distance_m / EARTH_RADIUS_M))


def _north(distance_m: float) -> float:
    return float(np.degrees(distance_m / EARTH_RADIUS_M))


def _neighborhood(sensor: dict, radius: float, window: int) -> dict:
    return next(item for item in sensor["neighborhoods"] if item["radius_m"] == radius and item["max_delta_minutes"] == window)


def test_exact_duplicates_are_counted_and_retained() -> None:
    table = _table(
        "Terra",
        [
            {"day": 2, "minute": 100, "lat": 0.0, "lon": 0.0, "frp": 5.0, "confidence": 80},
            {"day": 2, "minute": 100, "lat": 0.0, "lon": 0.0, "frp": 5.0, "confidence": 80},
            {"day": 2, "minute": 100, "lat": 0.0, "lon": 0.0, "frp": 9.0, "confidence": 80},
        ],
    )
    inventory = duplicate_inventory(table)
    coordinates = coordinate_inventory(table)
    assert inventory["extra_rows"] == 1
    assert inventory["groups"] == 1
    assert inventory["rows_removed"] == 0
    assert inventory["rows_retained"] == 3
    assert coordinates["same_coordinate_and_time_extra_rows"] == 2
    assert coordinates["multi_epoch_locations"] == 0
    assert coordinates["same_fire"] == "not_assessed"


def test_coordinate_groups_do_not_borrow_the_previous_coordinate_epoch() -> None:
    table = _table(
        "N20",
        [
            {"day": 1, "minute": 10, "lat": 0.0, "lon": 0.0},
            {"day": 1, "minute": 10, "lat": 1.0, "lon": 1.0, "frp": 1.0},
            {"day": 1, "minute": 40, "lat": 1.0, "lon": 1.0, "frp": 2.0},
            {"day": 1, "minute": 10, "lat": 2.0, "lon": 2.0, "frp": 3.0},
            {"day": 1, "minute": 10, "lat": 2.0, "lon": 2.0, "frp": 4.0},
        ],
    )
    coordinates = coordinate_inventory(table)
    assert coordinates["same_coordinate_and_time_extra_rows"] == 1
    assert coordinates["same_coordinate_and_time_groups"] == 1
    assert coordinates["multi_epoch_locations"] == 1
    assert coordinates["rows_at_multi_epoch_locations"] == 2


def test_same_coordinate_at_another_minute_is_temporally_separated() -> None:
    table = _table(
        "N20",
        [
            {"day": 4, "minute": 10, "lat": 1.0, "lon": 2.0, "frp": 3.0},
            {"day": 5, "minute": 10, "lat": 1.0, "lon": 2.0, "frp": 30.0},
            {"day": 5, "minute": 11, "lat": 4.0, "lon": 4.0, "frp": 8.0},
        ],
    )
    coordinates = coordinate_inventory(table)
    assert duplicate_inventory(table)["extra_rows"] == 0
    assert coordinates["same_coordinate_and_time_extra_rows"] == 0
    assert coordinates["multi_epoch_locations"] == 1
    assert coordinates["rows_at_multi_epoch_locations"] == 2
    assert coordinates["max_epochs_at_one_coordinate"] == 2
    assert coordinates["temporally_separated_means_same_fire"] is False


def test_nearest_other_uses_geodesic_distance_and_skips_itself() -> None:
    separation = 800.0
    table = _table(
        "Aqua",
        [
            {"day": 7, "minute": 600, "lat": 0.0, "lon": 0.0},
            {"day": 7, "minute": 640, "lat": 0.0, "lon": _east(separation)},
        ],
    )
    distance, delta = nearest_other(table.ecef, table.epoch)
    expected = haversine_m(0.0, 0.0, 0.0, _east(separation))
    assert abs(distance[0] - expected) < 0.05
    assert abs(distance[1] - expected) < 0.05
    assert delta[0] == 40
    assert np.all(np.isfinite(distance))


def test_coincident_rows_are_each_others_nearest_neighbor() -> None:
    table = _table(
        "SNPP",
        [
            {"day": 2, "minute": 10, "lat": 0.0, "lon": 0.0},
            {"day": 2, "minute": 10, "lat": 0.0, "lon": 0.0},
            {"day": 2, "minute": 10, "lat": 0.0, "lon": 0.0},
            {"day": 2, "minute": 80, "lat": 0.0, "lon": _east(4_000.0)},
        ],
    )
    distance, delta = nearest_other(table.ecef, table.epoch)
    assert np.all(distance[:3] == 0.0)
    assert np.all(delta[:3] == 0.0)
    assert abs(distance[3] - haversine_m(0.0, 0.0, 0.0, _east(4_000.0))) < 0.05
    assert delta[3] == 70


def test_nearest_other_crosses_the_antimeridian() -> None:
    table = _table(
        "SNPP",
        [
            {"day": 8, "minute": 100, "lat": 0.0, "lon": 179.995},
            {"day": 8, "minute": 100, "lat": 0.0, "lon": -179.995},
        ],
    )
    distance, _ = nearest_other(table.ecef, table.epoch)
    expected = haversine_m(0.0, 179.995, 0.0, -179.995)
    assert expected < 2_000.0
    assert abs(distance[0] - expected) < 0.05


def test_time_window_keeps_the_farther_row_when_the_close_row_is_late() -> None:
    table = _table(
        "Terra",
        [
            {"day": 3, "minute": 100, "lat": 0.0, "lon": 0.0, "frp": 12.0, "confidence": 90, "daynight": "D"},
            {"day": 3, "minute": 150, "lat": 0.0, "lon": _east(100.0), "frp": 4.0, "confidence": 20, "daynight": "N"},
            {"day": 3, "minute": 100, "lat": 0.0, "lon": _east(800.0), "frp": 7.0, "confidence": 70, "daynight": "D"},
            {"day": 3, "minute": 100, "lat": 10.0, "lon": 10.0, "frp": 1.0, "confidence": 10, "daynight": "D"},
        ],
    )
    sensor = analyze_sensor(table, common_days=[3])
    short = _neighborhood(sensor, 1_000.0, 30)
    long = _neighborhood(sensor, 1_000.0, 180)
    assert short["rows_with_neighbor"] == 2
    assert long["rows_with_neighbor"] == 3
    assert short["nearest_distance"]["p50"] > 500.0
    assert long["nearest_distance"]["min"] < 200.0
    assert sensor["same_fire"] == "not_assessed"
    assert sensor["rows_removed"] == 0
    assert sensor["characteristics"]["neighborhood_1km_30min"]["rows"] == 2
    assert sensor["characteristics"]["isolated_1km_30min"]["rows"] == 2
    assert sensor["characteristics"]["all"]["confidence"]["90"] == 1
    assert sensor["characteristics"]["all"]["day_rows"] == 3
    assert sensor["characteristics"]["all"]["night_rows"] == 1
    assert sensor["dates_without_rows"][0] == "2024-07-01"
    assert all(day["rows"] is None or day["zero_detections"] is False for day in sensor["daily"])
    empty = sensor["daily"][0]
    assert empty["rows"] is None
    assert empty["status"] == "no_rows_delivered"


def test_midnight_margin_uses_the_window_and_does_not_invent_august() -> None:
    table = _table(
        "N21",
        [
            {"day": 16, "minute": 23 * 60 + 50, "lat": 0.0, "lon": 0.0},
            {"day": 17, "minute": 40, "lat": 0.0, "lon": _east(200.0)},
            {"day": 31, "minute": 10, "lat": 5.0, "lon": 5.0},
        ],
    )
    sensor = analyze_sensor(table, common_days=[])
    assert _neighborhood(sensor, 1_000.0, 30)["rows_with_neighbor"] == 0
    assert _neighborhood(sensor, 1_000.0, 180)["rows_with_neighbor"] == 2
    by_day = {16: np.array([0]), 17: np.array([1]), 31: np.array([2])}
    margin = margin_indices(by_day, table.minute, 16, 180)
    assert list(margin) == [1]
    assert list(margin_indices(by_day, table.minute, 16, 30)) == []
    july31 = sensor["daily"][30]
    assert july31["next_date"]["status"] == "next_date_outside_period"
    assert july31["next_date"]["rows_with_next_date_neighbor_1km"] is None
    assert sensor["next_date_neighbor"]["excluded_because_next_date_is_outside_july"] == 1
    assert sensor["next_date_neighbor"]["within_1km"] == 1
    assert sensor["next_date_neighbor"]["excluded_because_next_date_has_no_rows"] == 1


def test_empty_next_date_is_not_stored_as_zero_neighbors() -> None:
    table = _table(
        "SNPP",
        [
            {"day": 9, "minute": 100, "lat": 0.0, "lon": 0.0},
            {"day": 16, "minute": 100, "lat": 0.0, "lon": _east(300.0)},
        ],
    )
    sensor = analyze_sensor(table, common_days=[])
    assert sensor["daily"][8]["next_date"]["status"] == "next_date_has_no_rows"
    assert sensor["daily"][8]["next_date"]["rows_with_next_date_neighbor_1km"] is None
    assert sensor["daily"][8]["zero_detections"] is False
    assert "2024-07-10" in sensor["dates_without_rows"]
    assert sensor["daily"][15]["next_date"]["status"] == "next_date_has_no_rows"
    assert sensor["next_date_neighbor"]["excluded_because_next_date_has_no_rows"] == 2
    assert sensor["next_date_neighbor"]["zero_detections"] is False


def test_viirs_confidence_stays_on_flags() -> None:
    table = _table(
        "SNPP",
        [
            {"day": 2, "minute": 10, "lat": 0.0, "lon": 0.0, "confidence": 0},
            {"day": 2, "minute": 10, "lat": 0.0, "lon": _east(100.0), "confidence": 1},
            {"day": 2, "minute": 10, "lat": 1.0, "lon": 1.0, "confidence": 2},
        ],
    )
    sensor = analyze_sensor(table, common_days=[2])
    assert sensor["characteristics"]["all"]["confidence"] == {"l": 1, "n": 1, "h": 1}


def test_representative_day_uses_the_earliest_day_on_a_tie() -> None:
    table = _table(
        "Aqua",
        [{"day": day, "minute": 1, "lat": 0.0, "lon": float(index)} for index, day in enumerate((1, 2, 3, 4)) for _ in range({1: 10, 2: 20, 3: 30, 4: 40}[day])],
    )
    assert representative_day(table) == 2


def test_dbscan_pair_is_one_component_and_a_far_row_is_noise() -> None:
    table = _table(
        "N20",
        [
            {"day": 6, "minute": 20, "lat": 0.0, "lon": 0.0},
            {"day": 6, "minute": 20, "lat": 0.0, "lon": _east(100.0)},
            {"day": 6, "minute": 20, "lat": 0.0, "lon": _east(20_000.0)},
        ],
    )
    labels = dbscan_labels(table.ecef, table.epoch, eps_m=1_000.0, window_min=30, min_samples=2)
    assert labels[0] == labels[1]
    assert labels[0] >= 0
    assert labels[2] == -1
    again = dbscan_labels(table.ecef, table.epoch, eps_m=1_000.0, window_min=30, min_samples=2)
    assert np.array_equal(labels, again)
    summary_labels = dbscan_labels(table.ecef, table.epoch, eps_m=1_000.0, window_min=30, min_samples=4)
    assert np.all(summary_labels == -1)


def test_border_row_joins_the_component_with_the_smaller_core_index() -> None:
    rows = []
    for north in (0.0, 80.0, 160.0, 240.0):
        rows.append({"day": 4, "minute": 10, "lat": _north(north), "lon": 0.0})
    for north in (0.0, 80.0, 160.0, 240.0):
        rows.append({"day": 4, "minute": 10, "lat": _north(north), "lon": _east(2_000.0)})
    rows.append({"day": 4, "minute": 10, "lat": 0.0, "lon": _east(1_000.0)})
    table = _table("N20", rows)
    labels = dbscan_labels(table.ecef, table.epoch, eps_m=1_000.5, window_min=0, min_samples=4)
    assert len(set(labels[:4].tolist())) == 1
    assert len(set(labels[4:8].tolist())) == 1
    assert labels[0] != labels[4]
    assert labels[0] >= 0
    assert labels[8] == labels[0]
    assert labels[8] != labels[4]
    with pytest.raises(AnalysisError):
        labels_from_pairs(
            1,
            np.empty(0, dtype=np.int64),
            np.empty(0, dtype=np.int64),
            np.empty(0),
            np.empty(0, dtype=np.int32),
            eps_m=100.0,
            window_min=0,
            min_samples=1,
        )


def test_report_language_and_figures(tmp_path) -> None:
    tables = {
        name: _table(name, [{"day": 4, "minute": 15, "lat": 0.0, "lon": _east(index * 250.0), "confidence": 2 if name not in {"Terra", "Aqua"} else 40}])
        for index, name in enumerate(("Terra", "Aqua", "SNPP", "N20", "N21"))
    }
    sensors = [analyze_sensor(tables[name], common_days=[4]) for name in ("Terra", "Aqua", "SNPP", "N20", "N21")]
    report = {
        "rows": 5,
        "dates_with_rows_in_every_sensor": ["2024-07-04"],
        "limitations": ["A nearest neighbor is not a confirmed physical fire.", "same_fire is not_assessed."],
        "sensors": sensors,
    }
    text = render_markdown(report)
    assert "not_assessed" in text
    assert "not a confirmed fire" in text
    assert "harmonization coefficient" in text.lower()
    assert "XGBoost is not trained" in text
    names = write_figures(report, tmp_path)
    assert len(names) == 8
    assert all((tmp_path / name).is_file() for name in names)
