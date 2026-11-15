"""Checks for the July experiment batch that do not need the monthly CSVs."""

import json

import numpy as np

from fire_data.contract import BACKEND_ROOT
from fire_data.experiments.clustering import neighbor_flags
from fire_data.experiments.common import concurrency_limit, quantiles
from fire_data.experiments.overpasses import _closest_minutes
from fire_data.experiments.validate import load_schema, validate_instance


def test_quantiles_keep_zero_and_negative_values() -> None:
    summary = quantiles(np.array([0.0, -2.0, 4.0, 8.0]))
    assert summary["count"] == 4
    assert summary["minimum"] == -2.0
    assert summary["p00"] == -2.0
    assert summary["maximum"] == 8.0


def test_margin_only_neighbor_ignores_direction() -> None:
    left = np.array([0, 1, 5], dtype=np.int64)
    right = np.array([5, 2, 0], dtype=np.int64)
    distance = np.array([100.0, 100.0, 100.0])
    delta = np.array([10, 10, 10], dtype=np.int32)
    has_same, has_margin = neighbor_flags(left, right, distance, delta, owned=4, eps_m=150.0, window_min=30)
    assert has_margin[0] and not has_same[0]
    assert has_same[1] and has_same[2]
    assert not has_margin[1] and not has_margin[2]
    assert not has_same[3] and not has_margin[3]


def test_closest_minutes_are_a_clock_difference() -> None:
    assert _closest_minutes(np.array([10, 80]), np.array([60, 200])) == 20
    assert _closest_minutes(np.array([], dtype=np.int32), np.array([5])) is None


def test_concurrency_stays_bounded() -> None:
    wide = concurrency_limit({"available_physical_memory_bytes": 16 * 1024**3})
    tight = concurrency_limit({"available_physical_memory_bytes": 7 * 1024**3})
    unknown = concurrency_limit({"available_physical_memory_bytes": None})
    assert wide["max_concurrent_experiments"] == 4
    assert tight["max_concurrent_experiments"] == 1
    assert unknown["max_concurrent_experiments"] == 2
    assert wide["full_month_rebuild"] is False


def test_completed_manifest_can_carry_results() -> None:
    schema = load_schema()
    prepared = {
        "schema_version": "1.0.0",
        "record_type": "experiment_run",
        "experiment_id": "B",
        "run_id": "m11",
        "status": "completed",
        "science_executed": True,
        "results": {"same_fire": "not_assessed", "harmonization_coefficient": None},
        "same_fire": "not_assessed",
        "scientific_locks": json.loads((BACKEND_ROOT / "research" / "examples" / "experiment_b.json").read_text(encoding="utf-8"))[
            "scientific_locks"
        ],
        "harmonization_coefficient": None,
        "xgboost_trained": False,
        "missing_dates_filled": False,
        "processing_level": "unresolved",
        "source_rows_read": 1,
        "source_bytes_read": 1,
        "records_processed": 1,
        "output_directory": "experiments/B/runs/m11",
        "config_sha256": "a" * 64,
        "software": {
            "python": "3.12.14",
            "packages": {"numpy": "2.5.4", "scipy": "1.18.1", "matplotlib": "3.11.2", "pytest": "9.2.0"},
            "git_commit": None,
        },
        "timing": {
            "prepare_seconds": 0.01,
            "science_wall_clock_seconds": 1.0,
            "cpu_seconds": 0.5,
            "peak_working_set_bytes": 10,
        },
        "created_utc": "2026-11-15T00:00:00+00:00",
    }
    assert validate_instance(prepared, schema["$defs"]["experimentRun"], schema) == []


def test_published_batch_locks_hold_when_the_results_exist() -> None:
    names = {
        "A": "A_clustering",
        "B": "B_measurements",
        "C": "C_overpasses",
        "D": "D_resolution",
    }
    for experiment_id, directory in names.items():
        path = BACKEND_ROOT / "experiments" / directory / "results.json"
        if not path.is_file():
            continue
        results = json.loads(path.read_text(encoding="utf-8"))
        manifest = json.loads((path.parent / "manifest.json").read_text(encoding="utf-8"))
        assert results["same_fire"] == "not_assessed"
        assert results["harmonization_coefficient"] is None
        assert results["xgboost_trained"] is False
        assert results["missing_dates_filled"] is False
        assert results["h3_selected"] is False
        assert manifest["experiment_id"] == experiment_id
        assert manifest["status"] == "completed"
        assert manifest["science_executed"] is True
        assert manifest["output_directory"] == f"experiments/{experiment_id}/runs/m11"
        forbidden = [key for key in _keys(results) if key in {"slope", "intercept", "calibration_coefficient"}]
        assert forbidden == []


def _keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(str(key) for key in value)
        for item in value.values():
            found.update(_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_keys(item))
    return found
