"""Validate an experiment configuration, prepare a run directory, or execute one.

Preparation does not read the July CSVs. Execution is a separate command.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fire_data.experiments.prepare import ExperimentConfigError, default_work_root, prepare_run
from fire_data.experiments.validate import SchemaError, load_schema, validate_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or prepare a July 2024 experiment run.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a configuration file against the schema")
    validate_parser.add_argument("config", type=Path)

    prepare_parser = subparsers.add_parser("prepare", help="Create an isolated run directory without reading source rows")
    prepare_parser.add_argument("config", type=Path)
    prepare_parser.add_argument("--run-id", required=True)
    prepare_parser.add_argument("--work-root", type=Path, default=default_work_root())

    execute_parser = subparsers.add_parser("execute", help="Execute one experiment or the resource-bounded batch")
    execute_parser.add_argument("--worker", choices=["A", "B", "C", "D"])
    execute_parser.add_argument("--run-id", default="m11")
    execute_parser.add_argument("--checksum-cache", type=Path)
    execute_parser.add_argument("--work-root", type=Path, default=default_work_root())

    args = parser.parse_args(argv)
    if args.command == "execute":
        from fire_data.experiments.execute import main as execute_main

        forwarded = ["--run-id", args.run_id, "--work-root", str(args.work_root)]
        if args.worker:
            forwarded.extend(["--worker", args.worker])
        if args.checksum_cache:
            forwarded.extend(["--checksum-cache", str(args.checksum_cache)])
        return execute_main(forwarded)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        schema = load_schema()
        if args.command == "validate":
            errors = validate_config(config, schema)
            if errors:
                raise SchemaError(errors)
            print(f"valid {args.config}")
            return 0
        destination = prepare_run(config, args.work_root, args.run_id, schema=schema)
    except (OSError, json.JSONDecodeError, SchemaError, ExperimentConfigError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
