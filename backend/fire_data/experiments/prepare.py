"""Create an isolated experiment directory without reading source rows."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter
from typing import Any

from fire_data.contract import BACKEND_ROOT
from fire_data.experiments.validate import SchemaError, load_schema, validate_instance

RUN_ID_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,63}$"
PACKAGES = ("numpy", "scipy", "matplotlib", "pytest")


class ExperimentConfigError(ValueError):
    """A configuration cannot be prepared."""


def prepare_run(config: dict[str, Any], work_root: Path, run_id: str, *, schema: dict[str, Any] | None = None) -> Path:
    """Write ``config.json`` and ``manifest.json`` under the experiment directory.

    The source CSVs are not opened. An existing run directory is left unchanged.
    """

    document = schema or load_schema()
    errors = validate_instance(config, document, document)
    if errors:
        raise SchemaError(errors)
    if not isinstance(run_id, str) or _invalid_run_id(run_id):
        raise ExperimentConfigError("run_id must be 1 to 64 characters of lowercase letters, digits, dots, underscores, or hyphens")

    started = perf_counter()
    destination = _run_directory(config, work_root, run_id)
    try:
        destination.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ExperimentConfigError(f"run directory already exists: {destination}") from exc
    config_path = destination / "config.json"
    manifest_path = destination / "manifest.json"
    config_bytes = _canonical_bytes(config)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1.0.0",
        "record_type": "experiment_run",
        "experiment_id": config["experiment_id"],
        "run_id": run_id,
        "status": "prepared",
        "science_executed": False,
        "results": None,
        "same_fire": "not_assessed",
        "scientific_locks": config["scientific_locks"],
        "harmonization_coefficient": None,
        "xgboost_trained": False,
        "missing_dates_filled": False,
        "processing_level": "unresolved",
        "source_rows_read": 0,
        "source_bytes_read": 0,
        "records_processed": 0,
        "output_directory": _relative_posix(destination, work_root),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "software": _software(work_root),
        "timing": {
            "prepare_seconds": perf_counter() - started,
            "science_wall_clock_seconds": None,
            "cpu_seconds": None,
            "peak_working_set_bytes": None,
        },
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_errors = validate_instance(manifest, document["$defs"]["experimentRun"], document)
    if manifest_errors:
        raise SchemaError(manifest_errors)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return destination


def _run_directory(config: dict[str, Any], work_root: Path, run_id: str) -> Path:
    relative = config["outputs"]["relative_directory"]
    expected = f"experiments/{config['experiment_id']}/runs"
    if relative != expected:
        raise ExperimentConfigError(f"output directory must be {expected}")
    root = work_root.resolve()
    destination = (root / "experiments" / config["experiment_id"] / "runs" / run_id).resolve()
    if not destination.is_relative_to(root):
        raise ExperimentConfigError("run directory escapes the work root")
    protected = root / "data"
    if destination == protected or protected in destination.parents or destination in protected.parents:
        raise ExperimentConfigError("run directory must not be inside data/")
    reports = root / "reports"
    if destination == reports or reports in destination.parents:
        raise ExperimentConfigError("run directory must not be inside reports/")
    return destination


def _invalid_run_id(run_id: str) -> bool:
    import re

    return re.fullmatch(RUN_ID_PATTERN, run_id) is None


def _canonical_bytes(config: dict[str, Any]) -> bytes:
    return json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _software(work_root: Path) -> dict[str, Any]:
    packages: dict[str, str | None] = {}
    for name in PACKAGES:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "python": sys.version.split()[0],
        "packages": packages,
        "git_commit": _git_head(work_root),
    }


def _git_head(work_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=work_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    commit = completed.stdout.strip()
    if len(commit) == 40 and all(character in "0123456789abcdef" for character in commit):
        return commit
    return None


def default_work_root() -> Path:
    return BACKEND_ROOT
