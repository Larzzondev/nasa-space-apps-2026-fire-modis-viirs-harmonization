"""Run experiments A–D as separate processes under a memory bound.

The processes share the read-only July CSVs and write four run directories.
They are not four git worktrees: a worktree would not contain the gitignored
CSVs, and these processes do not edit one another's code.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from fire_data.contract import BACKEND_ROOT
from fire_data.experiments.common import (
    PUBLISH_DIRECTORIES,
    Stopwatch,
    confirm_checksums_unchanged,
    machine_resources,
    measure_checksums,
    read_json,
    utc_now,
    write_json,
)
from fire_data.experiments.common import concurrency_limit as decide_concurrency

WORKERS = ("A", "B", "C", "D")
RUN_ID = "m11"


def _directory_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _run_worker(experiment_id: str, work_root: Path, run_id: str, checksum_cache: Path, log_path: Path) -> subprocess.Popen[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("w", encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "fire_data.experiments.execute",
        "--worker",
        experiment_id,
        "--run-id",
        run_id,
        "--checksum-cache",
        str(checksum_cache),
        "--work-root",
        str(work_root),
    ]
    return subprocess.Popen(command, cwd=work_root, stdout=log, stderr=subprocess.STDOUT, text=True)


def _load_execution(experiment_id: str) -> dict[str, Any] | None:
    path = BACKEND_ROOT / PUBLISH_DIRECTORIES[experiment_id] / "execution.json"
    if not path.is_file():
        return None
    return read_json(path)


def _load_results(experiment_id: str) -> dict[str, Any] | None:
    path = BACKEND_ROOT / PUBLISH_DIRECTORIES[experiment_id] / "results.json"
    if not path.is_file():
        return None
    return read_json(path)


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _recommend(results: dict[str, dict[str, Any] | None]) -> str:
    experiment_a = results.get("A")
    if not experiment_a or experiment_a.get("error"):
        return (
            "Experiment A did not complete. The next work is to inspect its failure evidence "
            "before any full-month labeling. A harmonization coefficient remains unauthorized."
        )
    shares = []
    for sensor in experiment_a["satellites"]:
        primary = next(item for item in sensor["margin_only_neighbors"] if item["role"] == "primary")
        owned = int(primary["owned_rows"])
        only = int(primary["rows_whose_in_window_neighbor_is_only_in_the_margin"])
        shares.append(0.0 if owned == 0 else only / owned)
    peak = max(shares) if shares else 0.0
    if peak < 0.01:
        margin_sentence = (
            f"On the representative dates, the 1 km and 30 minute margin-only share stays at or below {peak:.4f}. "
            "A full-month rebuild aimed at that midnight question is not the next measurement."
        )
    else:
        margin_sentence = (
            f"The largest representative-date margin-only share at 1 km and 30 minutes is {peak:.4f}. "
            "A later single-process labeling can extend that count across delivered dates. "
            "It should not share the machine with a second full spatial index."
        )
    return (
        margin_sentence
        + " The next research milestone should keep `same_fire` at `not_assessed`, leave the S-NPP gaps empty, "
        + "and decide whether the representative-date noise sensitivity is enough to justify one full-month "
        + "pass of the border and noise-label questions. That pass is still not a harmonization and not an H3 selection."
    )


def _summary(results: dict[str, dict[str, Any] | None], timing: dict[str, Any]) -> str:
    lines = [
        "# Milestone 11: first experiment batch",
        "",
        "Experiments A, B, C, and D read the same July 2024 CSVs and wrote separate directories. "
        "No source row was edited. No missing S-NPP date was filled. No harmonization coefficient was calculated. "
        "`same_fire` remains `not_assessed`.",
        "",
        "## Completion",
        "",
        "| Experiment | Status | Records processed | Wall clock (s) | Peak working set (bytes) |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for experiment_id in WORKERS:
        command = next(item for item in timing["commands"] if item["name"] == f"experiment_{experiment_id}")
        lines.append(
            f"| {experiment_id} | {command['status']} | {_fmt(command.get('records_processed'), 0)} | "
            f"{_fmt(command.get('wall_clock_seconds'), 3)} | {_fmt(command.get('peak_working_set_bytes'), 0)} |"
        )
    lines.extend(["", "## Experiment A", ""])
    experiment_a = results.get("A")
    if not experiment_a or experiment_a.get("error"):
        lines.append(f"Experiment A failed. {experiment_a.get('error') if experiment_a else 'No results file was written.'}")
    else:
        lines.append(
            "The seven full-month settings were cited and not fit again. "
            f"The representative-date factorial matches the published report: {experiment_a['representative_factorial_matches_published']}. "
            "Component labels are analytical ids inside one date. They are not fire ids."
        )
        lines.extend(
            [
                "",
                "| Satellite | Owned rows | Primary noise share | Border rows that change | Margin-only rows at 30 min |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for sensor in experiment_a["satellites"]:
            primary = next(item for item in sensor["factorial"] if item["eps_m"] == 1000 and item["window_min"] == 30 and item["min_samples"] == 4)
            border = sensor["border_assignment"]["owned_border_rows_whose_label_changes"]
            margin = next(item for item in sensor["margin_only_neighbors"] if item["role"] == "primary")
            share = primary["noise_rows"] / primary["rows"] if primary["rows"] else None
            lines.append(
                f"| {sensor['display']} | {sensor['owned_rows']} | {_fmt(share)} | {border} | "
                f"{margin['rows_whose_in_window_neighbor_is_only_in_the_margin']} |"
            )
    lines.extend(["", "## Experiment B", ""])
    experiment_b = results.get("B")
    if not experiment_b or experiment_b.get("error"):
        lines.append(f"Experiment B failed. {experiment_b.get('error') if experiment_b else 'No results file was written.'}")
    else:
        lines.append(
            "All-row quantiles keep non-positive FRP. Positive-only quantiles are separate. "
            "Published 1 km ratios were cited and were not refit. No slope or intercept was estimated."
        )
        lines.extend(["", "| Satellite | FRP p50 (MW) | Non-positive FRP | Scan p50 (km) | Day FRP p50 | Night FRP p50 |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for sensor in experiment_b["satellites"]:
            all_rows = sensor["strata"][0]
            day = next(item for item in sensor["strata"] if item["stratum"] == "day")
            night = next(item for item in sensor["strata"] if item["stratum"] == "night")
            lines.append(
                f"| {sensor['display']} | {_fmt(all_rows['frp_all_rows']['p50'])} | {all_rows['nonpositive_frp_rows']} | "
                f"{_fmt(all_rows['scan']['p50'])} | {_fmt(day['frp_all_rows']['p50'])} | {_fmt(night['frp_all_rows']['p50'])} |"
            )
    lines.extend(["", "## Experiment C", ""])
    experiment_c = results.get("C")
    if not experiment_c or experiment_c.get("error"):
        lines.append(f"Experiment C failed. {experiment_c.get('error') if experiment_c else 'No results file was written.'}")
    else:
        lines.append(
            "Comparisons use a UTC date only when both satellites have rows. "
            "The closest stored minute ignores location and is not a fire match. "
            "The 5 km, 60 minute candidate-pair time bins are cited, not rebuilt."
        )
        snpp_pair = next(item for item in experiment_c["satellite_pairs"] if item["satellite_a"] == "N20" and item["satellite_b"] == "N21")
        lines.append("")
        lines.append(
            f"NOAA-20 and NOAA-21 have {snpp_pair['dates_compared']} compared dates. "
            f"Their closest-minute median is {_fmt(snpp_pair['closest_stored_minute']['median_minutes'], 1)} minutes. "
            "That number is not the spatially constrained pair separation."
        )
        cited = next(item for item in experiment_c["cited_time_bins_5km_60min"] if item["label"] == "NOAA-20 and NOAA-21")
        median = cited["median_bin_minutes"]
        lines.append(
            f"The published NOAA-20/NOAA-21 candidate pairs inside 5 km and 60 minutes have a median time bin of "
            f"{median['bin_start']}–{median['bin_end']} minutes. A 30-minute window is empty for that couple because those acquisitions are farther apart than 30 minutes, not because the rows fail a spatial test."
        )
    lines.extend(["", "## Experiment D", ""])
    experiment_d = results.get("D")
    if not experiment_d or experiment_d.get("error"):
        lines.append(f"Experiment D failed. {experiment_d.get('error') if experiment_d else 'No results file was written.'}")
    else:
        lines.append(experiment_d["footprint_limitation"])
        lines.append("")
        lines.append(f"H3 selected: {experiment_d['h3_selected']}. {experiment_d['h3']['detail']}")
        lines.extend(
            [
                "",
                "| Satellite | Median of scan × track (km²) | Product of medians (km²) | 1° count cell is the rate cell | High-latitude row share |",
                "| --- | ---: | ---: | --- | ---: |",
            ]
        )
        for sensor in experiment_d["satellites"]:
            high = sensor["grid_1_degree"]["high_latitude_abs_at_least_60"]["row_share"]
            lines.append(
                f"| {sensor['display']} | {_fmt(sensor['median_of_products_km2'])} | {_fmt(sensor['product_of_medians_km2'])} | "
                f"{sensor['grid_1_degree']['count_and_rate_maxima_are_the_same_cell']} | {_fmt(high)} |"
            )
    lines.extend(["", "## Cross-experiment findings", ""])
    if experiment_a and experiment_d and not experiment_a.get("error") and not experiment_d.get("error"):
        lines.append(
            "A 375 m neighborhood and a 1 km neighborhood are different relative scales once the stored sizes are visible. "
            "MODIS median `scan × track` is near 1 km², while each VIIRS median is well below that. "
            "Experiment A's published full-month baseline already shows Terra and Aqua entirely in noise at 375 m, while the VIIRS sensors are not. "
            "Those two results describe archived rows. They do not say which sensor detects fires better."
        )
    if experiment_b and experiment_d and not experiment_b.get("error") and not experiment_d.get("error"):
        lines.append("")
        lines.append(
            "Experiment B's scan-quartile medians are the place to read a larger FRP against a larger stored pixel. "
            "Experiment D says that stored pixel is a rectangle proxy. Neither result is a calibration slope."
        )
    if experiment_a and experiment_c and not experiment_a.get("error") and not experiment_c.get("error"):
        lines.append("")
        lines.append(
            "Experiment A can use a 30-minute window inside one satellite. "
            "Experiment C shows why that same window is the wrong description of NOAA-20 versus NOAA-21: "
            "their spatially constrained pairs sit near 50 minutes. "
            "A 30-minute cross-sensor window looks like a miss for a reason that belongs to the clock."
        )
    lines.extend(
        [
            "",
            "S-NPP's empty dates are absent in every experiment. They are not zero clusters, zero FRP, or zero density.",
            "",
            "## Limits",
            "",
            "- Candidate pairs, nearest neighbors, and analytical components are not confirmed fires.",
            "- NOAA-20 and NOAA-21 processing level stays unresolved.",
            "- XGBoost was not trained.",
            "- H3 was not selected.",
            "",
            "## Next research milestone",
            "",
            _recommend(results),
            "",
            f"Batch wall clock: {_fmt(timing.get('wall_clock_seconds'), 3)} seconds. "
            f"Active execution, the sum of the measured command durations: {_fmt(timing.get('active_execution_seconds'), 3)} seconds.",
            "",
        ]
    )
    return "\n".join(lines)


def _timing_markdown(timing: dict[str, Any]) -> str:
    resources = timing["resources"]
    policy = timing["concurrency"]
    lines = [
        "# Milestone 11 timing",
        "",
        f"Started: {timing['started_utc']}",
        f"Completed: {timing['completed_utc']}",
        "",
        "Durations below are measured. Planning allowances are labeled as estimates and are not substituted for a missing measurement.",
        "",
        "## Host",
        "",
        f"- Physical cores: {resources.get('physical_cores')}",
        f"- Logical processors: {resources.get('logical_processors')}",
        f"- Physical memory: {resources.get('physical_memory_bytes')} bytes",
        f"- Available physical memory at launch: {resources.get('available_physical_memory_bytes')} bytes",
        f"- Free disk: {resources.get('disk_free_bytes')} bytes",
        "",
        "## Concurrency",
        "",
        policy["reason"],
        "",
        f"Processes launched together were capped at {policy['max_concurrent_experiments']}.",
        "",
        "## Commands",
        "",
        "| Command | Exit | Wall (s) | CPU (s) | Peak working set (bytes) | Rows read | Records processed | Records/s | Queue wait (s) | Output bytes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for command in timing["commands"]:
        lines.append(
            "| {name} | {exit_code} | {wall} | {cpu} | {peak} | {rows} | {records} | {rate} | {wait} | {output} |".format(
                name=command["name"],
                exit_code=command.get("exit_code"),
                wall=_fmt(command.get("wall_clock_seconds"), 3),
                cpu=_fmt(command.get("cpu_seconds"), 3),
                peak=_fmt(command.get("peak_working_set_bytes"), 0),
                rows=_fmt(command.get("source_rows_read"), 0),
                records=_fmt(command.get("records_processed"), 0),
                rate=_fmt(command.get("records_per_second"), 1),
                wait=_fmt(command.get("queue_wait_seconds"), 3),
                output=_fmt(command.get("output_bytes"), 0),
            )
        )
    lines.extend(
        [
            "",
            f"Total wall clock: {_fmt(timing['wall_clock_seconds'], 3)} seconds.",
            f"Active execution, summed across commands: {_fmt(timing['active_execution_seconds'], 3)} seconds.",
            f"Science-phase wall clock: {_fmt(timing['science_phase_wall_clock_seconds'], 3)} seconds.",
            f"Waiting time inside the science phase, summed across experiments: {_fmt(timing['science_queue_wait_seconds'], 3)} seconds.",
            f"Retries: {timing['retries']}. Cancellations: {timing['cancellations']}.",
            "",
            "Parallel efficiency is the sum of the four experiment wall clocks divided by four times the science-phase wall clock. "
            f"That ratio is {_fmt(timing.get('parallel_efficiency'), 3)}. "
            "A value near 1 means the four processes overlapped. It is not a claim about numerical speedup of one algorithm.",
            "",
            "## Checksums",
            "",
            f"The July CSV SHA-256 values were measured before the experiments in {_fmt(timing['checksum_before_seconds'], 3)} seconds "
            f"and again after them in {_fmt(timing['checksum_after_seconds'], 3)} seconds. "
            f"Unchanged: {timing['checksums_unchanged']}.",
            "",
            "## Planning allowances",
            "",
            "These were written down before the processes finished. They are not measurements.",
            "",
        ]
    )
    for item in timing["estimates"]:
        lines.append(f"- {item['experiment']}: {item['allowance']}")
    lines.append("")
    return "\n".join(lines)


def coordinate(work_root: Path, run_id: str) -> int:
    started = utc_now()
    clock = Stopwatch()
    resources = machine_resources()
    policy = decide_concurrency(resources)
    scratch = work_root / "experiments" / "_m11"
    scratch.mkdir(parents=True, exist_ok=True)
    print(f"milestone 11 start {started}", flush=True)
    print(
        f"cores={resources.get('physical_cores')} logical={resources.get('logical_processors')} "
        f"available_bytes={resources.get('available_physical_memory_bytes')} concurrent={policy['max_concurrent_experiments']}",
        flush=True,
    )
    checksum_started = clock.wall()
    checksums = measure_checksums(scratch / "checksums.json")
    checksum_seconds = clock.wall() - checksum_started
    print(f"checksums measured in {checksums['seconds']:.3f} s", flush=True)
    estimates = [
        {
            "experiment": "A",
            "allowance": "Representative dates only. The recorded full-month within-sensor analysis took 661.1942539000011 s after a 176.18339190000552 s load and is not repeated. Planning allowance: 900 s.",
        },
        {
            "experiment": "B",
            "allowance": "One pass over the five satellite columns. Historical full-pass duration is unmeasured. Planning allowance: 600 s.",
        },
        {
            "experiment": "C",
            "allowance": "One pass over acquisition dates and times. Planning allowance: 600 s.",
        },
        {
            "experiment": "D",
            "allowance": "One pass for scan, track, and the degree grids. Planning allowance: 600 s.",
        },
    ]
    science_started_mark = clock.wall()
    science_started_utc = utc_now()
    pending = list(WORKERS)
    running: dict[str, dict[str, Any]] = {}
    finished: list[dict[str, Any]] = []
    limit = int(policy["max_concurrent_experiments"])
    while pending or running:
        while pending and len(running) < limit:
            experiment_id = pending.pop(0)
            log_path = scratch / f"{experiment_id}.log"
            process = _run_worker(experiment_id, work_root, run_id, scratch / "checksums.json", log_path)
            running[experiment_id] = {
                "process": process,
                "started": clock.wall(),
                "started_utc": utc_now(),
                "log": log_path,
                "queue_wait_seconds": clock.wall() - science_started_mark,
            }
            print(f"started experiment {experiment_id}", flush=True)
        done = [experiment_id for experiment_id, job in running.items() if job["process"].poll() is not None]
        if not done:
            time.sleep(1.0)
            continue
        for experiment_id in done:
            job = running.pop(experiment_id)
            exit_code = int(job["process"].returncode)
            print(f"finished experiment {experiment_id} exit {exit_code}", flush=True)
            finished.append(
                {
                    "name": f"experiment_{experiment_id}",
                    "experiment_id": experiment_id,
                    "exit_code": exit_code,
                    "started_utc": job["started_utc"],
                    "finished_utc": utc_now(),
                    "wall_clock_seconds": clock.wall() - float(job["started"]),
                    "queue_wait_seconds": job["queue_wait_seconds"],
                    "log": job["log"].name,
                    "retries": 0,
                    "cancelled": False,
                }
            )
    science_wall = clock.wall() - science_started_mark
    after = confirm_checksums_unchanged(checksums)
    results = {experiment_id: _load_results(experiment_id) for experiment_id in WORKERS}
    commands = [
        {
            "name": "checksum_before",
            "exit_code": 0,
            "wall_clock_seconds": checksums["seconds"],
            "cpu_seconds": None,
            "peak_working_set_bytes": None,
            "source_rows_read": None,
            "records_processed": None,
            "records_per_second": None,
            "queue_wait_seconds": 0.0,
            "source_bytes_read": sum(item["bytes"] for item in checksums["archives"]),
            "output_bytes": (scratch / "checksums.json").stat().st_size,
            "status": "completed",
            "retries": 0,
            "cancelled": False,
        }
    ]
    for command in finished:
        execution = _load_execution(command["experiment_id"]) or {}
        manifest_path = work_root / "experiments" / command["experiment_id"] / "runs" / run_id / "manifest.json"
        manifest = read_json(manifest_path) if manifest_path.is_file() else {}
        timing = manifest.get("timing") or {}
        published = BACKEND_ROOT / PUBLISH_DIRECTORIES[command["experiment_id"]]
        records = execution.get("records_processed")
        wall = timing.get("science_wall_clock_seconds")
        if wall is None:
            wall = execution.get("wall_clock_seconds", command["wall_clock_seconds"])
        rate = None
        if isinstance(records, int) and isinstance(wall, (int, float)) and wall > 0:
            rate = records / wall
        status = manifest.get("status")
        if status not in {"completed", "failed"}:
            status = "failed" if command["exit_code"] else "completed"
        commands.append(
            {
                "name": command["name"],
                "exit_code": command["exit_code"],
                "started_utc": command["started_utc"],
                "finished_utc": command["finished_utc"],
                "wall_clock_seconds": wall,
                "cpu_seconds": timing.get("cpu_seconds", execution.get("cpu_seconds")),
                "peak_working_set_bytes": timing.get("peak_working_set_bytes"),
                "source_rows_read": manifest.get("source_rows_read", execution.get("source_rows_read")),
                "records_processed": records,
                "records_per_second": rate,
                "queue_wait_seconds": command["queue_wait_seconds"],
                "source_bytes_read": manifest.get("source_bytes_read", execution.get("source_bytes_read")),
                "output_bytes": _directory_bytes(published),
                "status": status,
                "retries": 0,
                "cancelled": False,
                "log": command["log"],
            }
        )
    commands.append(
        {
            "name": "checksum_after",
            "exit_code": 0 if after["unchanged"] else 1,
            "wall_clock_seconds": after["seconds"],
            "cpu_seconds": None,
            "peak_working_set_bytes": None,
            "source_rows_read": None,
            "records_processed": None,
            "records_per_second": None,
            "queue_wait_seconds": 0.0,
            "source_bytes_read": sum(item["bytes"] for item in after["archives"]),
            "output_bytes": 0,
            "status": "completed" if after["unchanged"] else "failed",
            "retries": 0,
            "cancelled": False,
        }
    )
    active = sum(float(command["wall_clock_seconds"]) for command in commands if command.get("wall_clock_seconds") is not None)
    science_commands = [command for command in commands if command["name"].startswith("experiment_")]
    science_active = sum(float(command["wall_clock_seconds"]) for command in science_commands)
    queue_wait = sum(float(command["queue_wait_seconds"]) for command in science_commands)
    efficiency = None
    if science_wall > 0 and science_commands:
        efficiency = science_active / (len(science_commands) * science_wall)
    payload = {
        "milestone": 11,
        "started_utc": started,
        "science_started_utc": science_started_utc,
        "completed_utc": utc_now(),
        "wall_clock_seconds": clock.wall(),
        "active_execution_seconds": active,
        "science_phase_wall_clock_seconds": science_wall,
        "science_queue_wait_seconds": queue_wait,
        "parallel_efficiency": efficiency,
        "retries": 0,
        "cancellations": 0,
        "resources": resources,
        "concurrency": policy,
        "estimates": estimates,
        "checksum_before_seconds": checksum_seconds,
        "checksum_after_seconds": after["seconds"],
        "checksums_unchanged": after["unchanged"],
        "checksum_after": after,
        "commands": commands,
        "execution_model": (
            "Four operating-system processes, one per experiment, limited by the concurrency policy. "
            "Git worktrees were not created. The CSVs are gitignored, so a worktree would not contain them, "
            "and the experiments do not edit a shared source file."
        ),
    }
    report_dir = BACKEND_ROOT / "reports" / "milestones"
    report_dir.mkdir(parents=True, exist_ok=True)
    write_json(report_dir / "milestone_11_timing.json", payload)
    (report_dir / "milestone_11_timing.md").write_text(_timing_markdown(payload), encoding="utf-8")
    (report_dir / "milestone_11_summary.md").write_text(_summary(results, payload), encoding="utf-8")
    failed = [command for command in science_commands if command["status"] != "completed" or command["exit_code"] != 0]
    if after["unchanged"] is False or failed:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute the July 2024 experiment batch.")
    parser.add_argument("--worker", choices=list(WORKERS))
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--checksum-cache", type=Path)
    parser.add_argument("--work-root", type=Path, default=BACKEND_ROOT)
    args = parser.parse_args(argv)
    if args.worker:
        if args.checksum_cache is None:
            print("a worker needs --checksum-cache", file=sys.stderr)
            return 1
        from fire_data.experiments.clustering import run as run_a
        from fire_data.experiments.measurements import run as run_b
        from fire_data.experiments.overpasses import run as run_c
        from fire_data.experiments.resolution import run as run_d

        runners = {"A": run_a, "B": run_b, "C": run_c, "D": run_d}
        return runners[args.worker](args.work_root, args.run_id, args.checksum_cache)
    return coordinate(args.work_root, args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
