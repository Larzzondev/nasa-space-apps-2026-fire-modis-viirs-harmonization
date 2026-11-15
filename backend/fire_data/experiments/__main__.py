"""Validate an experiment configuration or prepare its run directory.

Preparation does not read the July CSVs and does not execute the analysis.
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

    args = parser.parse_args(argv)
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
