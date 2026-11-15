"""Command line for archive discovery, validation, and one-day EDA."""

from __future__ import annotations

import argparse
from pathlib import Path

from fire_data.contract import BACKEND_ROOT
from fire_data.discover import discover_all, write_discovery
from fire_data.validate import validate_all

DEFAULT_REPORT = BACKEND_ROOT / "reports" / "discovery.json"
DEFAULT_EDA_DIR = BACKEND_ROOT / "reports"


def _thresholds(text: str) -> tuple[float, ...]:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        raise SystemExit("At least one overlap threshold is required")
    return tuple(float(part) for part in parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover, validate, or summarize the extracted FIRMS archives.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="Measure the four archives and write a JSON report")
    discover_parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)

    subparsers.add_parser("validate", help="Check the four archives against the observed contract")

    eda_parser = subparsers.add_parser("eda", help="Write the one-day exploratory summary, report, and figures")
    eda_parser.add_argument("--output-dir", type=Path, default=DEFAULT_EDA_DIR)
    eda_parser.add_argument("--thresholds-m", default="375,1000,5000")

    args = parser.parse_args(argv)
    if args.command == "discover":
        report = discover_all()
        write_discovery(report, args.output)
        for source in report.sources:
            status = "ERROR" if source.read_error else "OK"
            print(f"{source.source_id}: {status} rows={source.row_count} dates={source.date_min}..{source.date_max}")
            if source.read_error:
                print(f"  {source.read_error}")
        print(f"Wrote {args.output}")
        return 1 if any(source.read_error for source in report.sources) else 0

    if args.command == "validate":
        report = validate_all()
        for source in report.sources:
            status = "OK" if source.passed else "FAIL"
            print(f"{source.source_id}: {status} rows={source.row_count} issues={source.issue_count}")
            for issue in source.issues:
                location = "file" if issue.line_number is None else f"line {issue.line_number}"
                column = f" {issue.column}" if issue.column else ""
                print(f"  {location}{column}: {issue.message}")
        return 0 if report.passed else 1

    from fire_data.eda import run_eda

    summary = run_eda(args.output_dir, _thresholds(args.thresholds_m))
    print(f"detections={summary['scope']['detection_count']} dates={','.join(summary['scope']['dates'])}")
    print(f"Wrote {args.output_dir / 'eda_report.md'}")
    print(f"Wrote {args.output_dir / 'eda_summary.json'}")
    print(f"Wrote {args.output_dir / 'figures'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
