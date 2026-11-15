"""Run the one-day exploratory summary.

Each archive is loaded once. Derived satellite groups and spatial trees are
temporary working sets. The raw CSV files are opened for reading only.
"""

from __future__ import annotations

from pathlib import Path

from fire_data.contract import BACKEND_ROOT, RAW_DIR
from fire_data.eda_summary import DEFAULT_THRESHOLDS_M, build_summary
from fire_data.eda_table import load_all, read_source_rows

REPORTS_DIR = BACKEND_ROOT / "reports"


def _refuse_raw_output(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    raw = RAW_DIR.resolve()
    if resolved == raw or raw in resolved.parents:
        raise ValueError("Refusing to write EDA products into the raw archive directory")


def _lookup(table, line_numbers: set[int]) -> dict[int, dict[str, str]]:
    return read_source_rows(Path(table.archive_path), line_numbers)


def run_eda(
    output_dir: Path | None = None,
    thresholds_m: tuple[float, ...] = DEFAULT_THRESHOLDS_M,
) -> dict:
    output = REPORTS_DIR if output_dir is None else Path(output_dir)
    _refuse_raw_output(output)
    tables = load_all()
    summary = build_summary(tables, thresholds_m, row_lookup=_lookup)
    figures_dir = output / "figures"
    from fire_data.eda_figures import write_figures

    summary["figures"] = write_figures(tables, summary, figures_dir)
    import matplotlib
    import numpy
    import scipy

    summary["software"] = {
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "matplotlib": matplotlib.__version__,
    }
    from fire_data.eda_report import write_report, write_summary

    output.mkdir(parents=True, exist_ok=True)
    write_summary(summary, output / "eda_summary.json")
    write_report(summary, output / "eda_report.md")
    return summary
