import json
from copy import deepcopy
from pathlib import Path

import pytest

from fire_data.contract import BACKEND_ROOT
from fire_data.eda_spatial import EARTH_RADIUS_M
from fire_data.experiments.__main__ import main
from fire_data.experiments.prepare import ExperimentConfigError, prepare_run
from fire_data.experiments.validate import EXAMPLES_DIR, SchemaError, load_schema, validate_config, validate_instance
from fire_data.monthly_scan import EXPECTED_ROWS

EXAMPLE_NAMES = ("experiment_a.json", "experiment_b.json", "experiment_c.json", "experiment_d.json")


def _load(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def _examples() -> list[dict]:
    return [_load(name) for name in EXAMPLE_NAMES]


def test_schema_and_examples_validate() -> None:
    schema = load_schema()
    assert schema["$id"].endswith("/experiment_config.schema.json")
    for config in _examples():
        assert validate_config(config, schema) == []


def test_examples_share_the_input_contract_and_write_apart() -> None:
    configs = _examples()
    inputs = [config["inputs"] for config in configs]
    locks = [config["scientific_locks"] for config in configs]
    assert all(item == inputs[0] for item in inputs)
    assert all(item == locks[0] for item in locks)
    directories = [config["outputs"]["relative_directory"] for config in configs]
    assert directories == [f"experiments/{config['experiment_id']}/runs" for config in configs]
    assert len(set(directories)) == 4
    assert sum(archive["rows"] for archive in inputs[0]["archives"]) == 7_985_467
    assert {archive["sensor"]: archive["rows"] for archive in inputs[0]["archives"]} == EXPECTED_ROWS


def test_archive_checksums_match_the_ingestion_manifest() -> None:
    manifest = json.loads((BACKEND_ROOT / "reports" / "ingestion_2024_07.json").read_text(encoding="utf-8"))
    recorded = {sensor["sensor"]: sensor for sensor in manifest["sensors"]}
    for archive in _examples()[0]["inputs"]["archives"]:
        source = recorded[archive["sensor"]]
        assert archive["sha256"] == source["csv_sha256"]
        assert archive["rows"] == source["record_count"]
        assert archive["processing_stream"] is None
        assert source["processing_stream"] is None


def test_clustering_radius_and_representative_dates_match_published_results() -> None:
    parameters = _load("experiment_a.json")["parameters"]
    assert parameters["earth_radius_m"] == EARTH_RADIUS_M
    metrics = json.loads((BACKEND_ROOT / "reports" / "milestones" / "milestone_09_metrics.json").read_text(encoding="utf-8"))
    published = {sensor["satellite"]: sensor["representative_date"] for sensor in metrics["sensors"]}
    assert parameters["representative_dates"] == published
    assert metrics["same_fire"] == "not_assessed"


def test_forbidden_scientific_actions_are_rejected() -> None:
    schema = load_schema()
    base = _load("experiment_a.json")

    same_fire = deepcopy(base)
    same_fire["scientific_locks"]["same_fire"] = "same"
    filled = deepcopy(base)
    filled["scientific_locks"]["missing_dates_filled"] = True
    coefficient = deepcopy(base)
    coefficient["scientific_locks"]["harmonization_coefficient"] = 1.2
    trained = deepcopy(base)
    trained["scientific_locks"]["xgboost_trained"] = True
    crossed = deepcopy(base)
    crossed["outputs"]["relative_directory"] = "experiments/B/runs"
    extra = deepcopy(base)
    extra["parameters"]["calibration_slope"] = 0.3
    unknown = deepcopy(base)
    unknown["experiment_id"] = "E"

    for config in (same_fire, filled, coefficient, trained, crossed, extra, unknown):
        assert validate_config(config, schema)

    clustering = _load("experiment_b.json")
    clustering["parameters"]["estimate_calibration_coefficient"] = True
    assert validate_config(clustering, schema)

    temporal = _load("experiment_c.json")
    temporal["parameters"]["fill_absent_dates"] = True
    assert validate_config(temporal, schema)

    spatial = _load("experiment_d.json")
    spatial["parameters"]["h3_selected"] = True
    assert validate_config(spatial, schema)


def test_prepare_writes_an_isolated_manifest_and_does_not_require_csvs(tmp_path: Path) -> None:
    schema = load_schema()
    config = _load("experiment_a.json")
    destination = prepare_run(config, tmp_path, "m10-a", schema=schema)
    assert destination == tmp_path / "experiments" / "A" / "runs" / "m10-a"
    assert sorted(path.name for path in destination.iterdir()) == ["config.json", "manifest.json"]
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert validate_instance(manifest, schema["$defs"]["experimentRun"], schema) == []
    assert manifest["science_executed"] is False
    assert manifest["results"] is None
    assert manifest["same_fire"] == "not_assessed"
    assert manifest["source_rows_read"] == 0
    assert manifest["records_processed"] == 0
    assert manifest["harmonization_coefficient"] is None
    assert manifest["xgboost_trained"] is False
    assert manifest["missing_dates_filled"] is False
    assert manifest["output_directory"] == "experiments/A/runs/m10-a"
    assert manifest["timing"]["science_wall_clock_seconds"] is None
    assert manifest["timing"]["prepare_seconds"] >= 0
    commit = manifest["software"]["git_commit"]
    assert commit is None or (len(commit) == 40 and commit.isalnum())
    assert not (tmp_path / "data").exists()

    original = (destination / "manifest.json").read_bytes()
    with pytest.raises(ExperimentConfigError):
        prepare_run(config, tmp_path, "m10-a", schema=schema)
    assert (destination / "manifest.json").read_bytes() == original


def test_parallel_prepares_do_not_share_a_directory(tmp_path: Path) -> None:
    schema = load_schema()
    written = [prepare_run(_load(name), tmp_path, "batch-1", schema=schema) for name in EXAMPLE_NAMES]
    assert len({path.parent.parent for path in written}) == 4
    for path in written:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["output_directory"].startswith(f"experiments/{manifest['experiment_id']}/")


def test_cli_validates_and_prepares(tmp_path: Path) -> None:
    example = EXAMPLES_DIR / "experiment_c.json"
    assert main(["validate", str(example)]) == 0
    assert main(["prepare", str(example), "--run-id", "m10-c", "--work-root", str(tmp_path)]) == 0
    assert (tmp_path / "experiments" / "C" / "runs" / "m10-c" / "manifest.json").is_file()
    assert main(["validate", str(tmp_path / "missing.json")]) == 1


def test_unsupported_keyword_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.schema.json"
    path.write_text(json.dumps({"type": "object", "format": "date"}), encoding="utf-8")
    with pytest.raises(SchemaError):
        load_schema(path)
