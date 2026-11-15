"""Shared read-only scanning and run accounting for the July experiments.

The four CSVs stay unmodified. A date with no stored row is left out of every
denominator. ``same_fire`` stays ``not_assessed``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, process_time
from typing import Any

import numpy as np

from fire_data.contract import BACKEND_ROOT, COLUMNS
from fire_data.experiments.prepare import prepare_run
from fire_data.experiments.validate import load_schema, validate_instance
from fire_data.fields import is_valid_acq_time
from fire_data.ingest import DESTINATION_DIR
from fire_data.monthly_scan import ARCHIVES, EXPECTED_ROWS, sha256_file
from fire_data.readers import read_archive
from fire_data.spatiotemporal_analysis import VIIRS_FLAGS, _peak_working_set

PUBLISH_DIRECTORIES = {
    "A": "experiments/A_clustering",
    "B": "experiments/B_measurements",
    "C": "experiments/C_overpasses",
    "D": "experiments/D_resolution",
}
EXAMPLES = {
    "A": "experiment_a.json",
    "B": "experiment_b.json",
    "C": "experiment_c.json",
    "D": "experiment_d.json",
}
DISPLAY = {
    "Terra": "Terra",
    "Aqua": "Aqua",
    "SNPP": "S-NPP",
    "N20": "NOAA-20",
    "N21": "NOAA-21",
}
SATELLITE_ORDER = ("Terra", "Aqua", "SNPP", "N20", "N21")
QUANTILE_LEVELS = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)
INDEX = {name: COLUMNS.index(name) for name in COLUMNS}


class ExperimentRunError(RuntimeError):
    """A scientific run cannot be accepted."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_ready(value.tolist())
    if isinstance(value, np.floating):
        number = float(value)
        if not np.isfinite(number):
            return None
        return number
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(payload), indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def example_config(experiment_id: str) -> dict[str, Any]:
    path = BACKEND_ROOT / "research" / "examples" / EXAMPLES[experiment_id]
    return read_json(path)


def archive_by_sensor() -> dict[str, dict[str, Any]]:
    return {str(spec["sensor"]): spec for spec in ARCHIVES}


def verify_checksum_cache(cache_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Accept a digest measured earlier in this batch when the file size still matches."""

    measured = read_json(cache_path)
    expected = {archive["sensor"]: archive for archive in config["inputs"]["archives"]}
    found = {item["sensor"]: item for item in measured["archives"]}
    if set(found) != set(expected):
        raise ExperimentRunError("checksum cache does not list the four July archives")
    checked = []
    for sensor, archive in expected.items():
        path = DESTINATION_DIR / archive["relative_csv"]
        size = path.stat().st_size
        item = found[sensor]
        if item["sha256"] != archive["sha256"]:
            raise ExperimentRunError(f"{sensor} SHA-256 does not match the experiment configuration")
        if int(item["bytes"]) != size:
            raise ExperimentRunError(f"{sensor} file size changed after the checksum was measured")
        checked.append(
            {
                "sensor": sensor,
                "relative_csv": archive["relative_csv"],
                "sha256": item["sha256"],
                "bytes": size,
                "sha256_matches_configuration": True,
            }
        )
    return {
        "checksum_cache": cache_path.name,
        "measured_utc": measured["measured_utc"],
        "measurement_seconds": measured["seconds"],
        "archives": checked,
    }


def measure_checksums(destination: Path) -> dict[str, Any]:
    started = perf_counter()
    archives = []
    for spec in ARCHIVES:
        path = DESTINATION_DIR / spec["relative_csv"]
        archives.append(
            {
                "sensor": spec["sensor"],
                "relative_csv": Path(spec["relative_csv"]).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = {"measured_utc": utc_now(), "seconds": perf_counter() - started, "archives": archives}
    write_json(destination, payload)
    return payload


def confirm_checksums_unchanged(before: dict[str, Any]) -> dict[str, Any]:
    started = perf_counter()
    changed = []
    archives = []
    for item in before["archives"]:
        path = DESTINATION_DIR / item["relative_csv"]
        digest = sha256_file(path)
        size = path.stat().st_size
        same = digest == item["sha256"] and size == int(item["bytes"])
        if not same:
            changed.append(item["sensor"])
        archives.append({"sensor": item["sensor"], "sha256": digest, "bytes": size, "unchanged": same})
    return {
        "measured_utc": utc_now(),
        "seconds": perf_counter() - started,
        "unchanged": not changed,
        "changed_sensors": changed,
        "archives": archives,
    }


def quantiles(values: np.ndarray) -> dict[str, float | int | None]:
    """Linear quantiles. Non-finite values are excluded. Zeros and negatives stay."""

    sample = np.asarray(values, dtype=np.float64)
    sample = sample[np.isfinite(sample)]
    result: dict[str, float | int | None] = {"count": int(sample.size), "method": "numpy.quantile method=linear"}
    if sample.size == 0:
        for level in QUANTILE_LEVELS:
            result[f"p{int(round(level * 100)):02d}"] = None
        result["mean"] = None
        result["minimum"] = None
        result["maximum"] = None
        return result
    estimated = np.quantile(sample, QUANTILE_LEVELS, method="linear")
    for level, estimate in zip(QUANTILE_LEVELS, estimated, strict=True):
        result[f"p{int(round(level * 100)):02d}"] = float(estimate)
    result["mean"] = float(np.mean(sample))
    result["minimum"] = float(sample.min())
    result["maximum"] = float(sample.max())
    return result


def scan_archives(
    sensors: tuple[str, ...] | list[str],
    consume: Callable[[str, list[str], dict[str, int]], None],
) -> dict[str, int]:
    """Read the selected monthly CSVs from the first byte to the last.

    ``consume`` sees the sensor id, the raw row, and the column index. The file
    is opened read-only by the archive reader. Nothing is written beside it.
    """

    specs = archive_by_sensor()
    counts: dict[str, int] = {}
    bytes_read = 0
    for sensor in sensors:
        spec = specs[sensor]
        path = DESTINATION_DIR / spec["relative_csv"]
        bytes_read += path.stat().st_size
        seen = 0
        with read_archive(path) as (header, rows):
            if tuple(header) != COLUMNS:
                raise ExperimentRunError(f"{path.name} header does not match the local column contract")
            for line_number, row in rows:
                if len(row) != len(COLUMNS):
                    raise ExperimentRunError(f"{path.name} line {line_number} does not have {len(COLUMNS)} fields")
                seen += 1
                if seen > int(EXPECTED_ROWS[sensor]):
                    raise ExperimentRunError(f"{path.name} has more rows than the ingestion manifest")
                consume(sensor, row, INDEX)
        if seen != int(EXPECTED_ROWS[sensor]):
            raise ExperimentRunError(f"{path.name} has {seen} rows; the manifest records {EXPECTED_ROWS[sensor]}")
        counts[sensor] = seen
    counts["source_bytes_read"] = bytes_read
    return counts


def require_july_timestamp(row: list[str], path_name: str, line_hint: str) -> tuple[int, int]:
    date_text = row[INDEX["acq_date"]]
    clock = row[INDEX["acq_time"]]
    if not date_text.startswith("2024-07-") or not is_valid_acq_time(clock):
        raise ExperimentRunError(f"{path_name} {line_hint} has an unexpected acquisition time")
    return int(date_text[8:10]), int(clock[:2]) * 60 + int(clock[2:])


def require_satellite(row: list[str], allowed: set[str] | frozenset[str], path_name: str) -> str:
    satellite = row[INDEX["satellite"]]
    if satellite not in allowed:
        raise ExperimentRunError(f"{path_name} has satellite {satellite}")
    return satellite


def confidence_code(row: list[str], scale: str, path_name: str) -> int:
    flag = row[INDEX["confidence"]]
    if scale == "viirs_lnh":
        if flag not in VIIRS_FLAGS:
            raise ExperimentRunError(f"{path_name} has an unexpected VIIRS flag {flag}")
        return VIIRS_FLAGS.index(flag)
    if not flag.isdigit() or not 0 <= int(flag) <= 100:
        raise ExperimentRunError(f"{path_name} has an unexpected MODIS confidence {flag}")
    return int(flag)


def daynight_code(row: list[str], path_name: str) -> int:
    flag = row[INDEX["daynight"]]
    if flag == "D":
        return 0
    if flag == "N":
        return 1
    raise ExperimentRunError(f"{path_name} has an unexpected day/night flag {flag}")


def machine_resources() -> dict[str, Any]:
    """Measure the host. Unreadable fields stay null."""

    logical = os.cpu_count()
    physical = _physical_cores()
    memory = _memory()
    disk = shutil.disk_usage(BACKEND_ROOT)
    return {
        "measured_utc": utc_now(),
        "logical_processors": logical,
        "physical_cores": physical,
        "physical_memory_bytes": memory.get("total"),
        "available_physical_memory_bytes": memory.get("available"),
        "disk_total_bytes": int(disk.total),
        "disk_free_bytes": int(disk.free),
        "python": sys.version.split()[0],
    }


def concurrency_limit(resources: dict[str, Any]) -> dict[str, Any]:
    """Keep four full spatial indexes from sharing the machine.

    Each first-batch process is planned below 2 GiB because it streams the CSVs
    or labels one representative date. Four such processes fit when at least
    8 GiB is free after a 6 GiB reserve. A tighter machine runs two at a time.
    """

    available = resources.get("available_physical_memory_bytes")
    reserve = 6 * 1024**3
    planned = 2 * 1024**3
    if not isinstance(available, int):
        slots = 2
        reason = "available memory was not measured, so concurrency stays at 2"
    else:
        slots = int((available - reserve) // planned)
        slots = max(1, min(4, slots))
        reason = (
            f"{slots} experiment processes may run at once. "
            f"Available physical memory was {available} bytes. "
            "Each process is planned below 2147483648 bytes. "
            "6442450944 bytes stay in reserve. "
            "full_month_rebuild is not in this batch."
        )
    return {
        "max_concurrent_experiments": slots,
        "planned_peak_bytes_per_process": planned,
        "reserved_bytes": reserve,
        "full_month_rebuild": False,
        "reason": reason,
    }


def begin(experiment_id: str, work_root: Path, run_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    config = example_config(experiment_id)
    schema = load_schema()
    destination = prepare_run(config, work_root, run_id, schema=schema)
    return destination, config, schema


def finish(
    destination: Path,
    schema: dict[str, Any],
    *,
    status: str,
    science_executed: bool,
    results: dict[str, Any] | None,
    source_rows_read: int,
    source_bytes_read: int,
    records_processed: int,
    science_seconds: float | None,
    cpu_seconds: float | None,
) -> dict[str, Any]:
    manifest_path = destination / "manifest.json"
    manifest = read_json(manifest_path)
    manifest["status"] = status
    manifest["science_executed"] = science_executed
    manifest["results"] = results
    manifest["source_rows_read"] = source_rows_read
    manifest["source_bytes_read"] = source_bytes_read
    manifest["records_processed"] = records_processed
    manifest["timing"]["science_wall_clock_seconds"] = science_seconds
    manifest["timing"]["cpu_seconds"] = cpu_seconds
    peak = _peak_working_set()
    manifest["timing"]["peak_working_set_bytes"] = peak
    errors = validate_instance(manifest, schema["$defs"]["experimentRun"], schema)
    if errors:
        raise ExperimentRunError("completed manifest failed validation: " + "; ".join(errors))
    write_json(manifest_path, manifest)
    return manifest


def publish_run(destination: Path, experiment_id: str) -> Path:
    """Copy the committed deliverables out of the gitignored run directory."""

    published = BACKEND_ROOT / PUBLISH_DIRECTORIES[experiment_id]
    if published.exists():
        shutil.rmtree(published)
    published.mkdir(parents=True)
    for name in ("config.json", "manifest.json", "results.json", "report.md", "validation.json", "execution.json"):
        source = destination / name
        if source.is_file():
            shutil.copy2(source, published / name)
    figures = destination / "figures"
    if figures.is_dir():
        shutil.copytree(figures, published / "figures")
    return published


def assert_locks(config: dict[str, Any]) -> None:
    locks = config["scientific_locks"]
    if locks.get("same_fire") != "not_assessed":
        raise ExperimentRunError("same_fire must stay not_assessed")
    if locks.get("missing_dates_filled") is not False:
        raise ExperimentRunError("missing dates must stay unfilled")
    if locks.get("harmonization_coefficient") is not None:
        raise ExperimentRunError("a harmonization coefficient is not authorized")
    if locks.get("xgboost_trained") is not False:
        raise ExperimentRunError("XGBoost training is not authorized")
    if locks.get("modify_source_rows") is not False:
        raise ExperimentRunError("source rows are read-only")
    if locks.get("h3_selected") is not False:
        raise ExperimentRunError("H3 must stay unselected")
    if config["inputs"]["access"] != "read_only":
        raise ExperimentRunError("input access must be read_only")


def base_results(config: dict[str, Any], checksums: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_id": config["experiment_id"],
        "title": config["title"],
        "same_fire": "not_assessed",
        "harmonization_coefficient": None,
        "xgboost_trained": False,
        "missing_dates_filled": False,
        "processing_level": "unresolved",
        "clusters_are_confirmed_fires": False,
        "candidate_pairs_are_confirmed_fires": False,
        "proximity_establishes_same_fire": False,
        "h3_selected": False,
        "source_checksums": checksums,
        "scientific_locks": config["scientific_locks"],
    }


class Stopwatch:
    def __init__(self) -> None:
        self.wall_started = perf_counter()
        self.cpu_started = process_time()

    def wall(self) -> float:
        return perf_counter() - self.wall_started

    def cpu(self) -> float:
        return process_time() - self.cpu_started


def save_figure(figure: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    figure.clf()


def _memory() -> dict[str, int | None]:
    try:
        import ctypes

        class Status(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = Status()
        status.dwLength = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return {"total": None, "available": None}
        return {"total": int(status.ullTotalPhys), "available": int(status.ullAvailPhys)}
    except (AttributeError, OSError):
        return {"total": None, "available": None}


def _physical_cores() -> int | None:
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = completed.stdout.strip()
    if completed.returncode != 0 or not text.isdigit():
        return None
    return int(text)

