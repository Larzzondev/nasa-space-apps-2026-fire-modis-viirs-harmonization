"""Measure what the extracted FIRMS archives actually contain."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from fire_data.contract import (
    CATEGORY_COLUMNS,
    COLUMNS,
    NUMERIC_COLUMNS,
    SOURCES,
    SourceContract,
)
from fire_data.readers import read_archive
from fire_data.fields import is_valid_acq_time, parse_float


@dataclass(frozen=True)
class SourceDiscovery:
    source_id: str
    relative_path: str
    row_count: int
    columns: tuple[str, ...]
    empty_counts: dict[str, int]
    malformed_row_count: int
    duplicate_row_count: int
    numeric_min: dict[str, float | None]
    numeric_max: dict[str, float | None]
    unparsable_numeric_counts: dict[str, int]
    categories: dict[str, tuple[str, ...]]
    date_min: str | None
    date_max: str | None
    distinct_dates: int
    distinct_acq_times: int
    invalid_acq_time_count: int
    read_error: str | None = None

    def to_json(self) -> dict[str, object]:
        payload = asdict(self)
        payload["columns"] = list(self.columns)
        for name, values in self.categories.items():
            payload["categories"][name] = list(values)
        return payload


@dataclass(frozen=True)
class DiscoveryReport:
    sources: tuple[SourceDiscovery, ...]

    def to_json(self) -> dict[str, object]:
        return {"sources": [source.to_json() for source in self.sources]}


def discover_source(source: SourceContract) -> SourceDiscovery:
    if not source.path.is_file():
        return _empty_discovery(source, f"Missing archive: {source.relative_path.as_posix()}")

    try:
        with read_archive(source.path) as (header, rows):
            return _summarize(source, tuple(header), rows)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return _empty_discovery(source, str(exc))


def _summarize(
    source: SourceContract,
    columns: tuple[str, ...],
    rows: Iterator[tuple[int, list[str]]],
) -> SourceDiscovery:
    empty_counts = {name: 0 for name in columns}
    categories: dict[str, set[str]] = {name: set() for name in CATEGORY_COLUMNS if name in columns}
    numeric_min: dict[str, float | None] = {name: None for name in NUMERIC_COLUMNS}
    numeric_max: dict[str, float | None] = {name: None for name in NUMERIC_COLUMNS}
    unparsable = {name: 0 for name in NUMERIC_COLUMNS}
    dates: set[str] = set()
    acq_times: set[str] = set()
    invalid_times = 0
    malformed = 0
    seen: set[tuple[str, ...]] = set()
    duplicates = 0
    row_count = 0
    index = {name: position for position, name in enumerate(columns)}

    for _line_number, row in rows:
        row_count += 1
        if len(row) != len(columns):
            malformed += 1
            continue
        key = tuple(row)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
        for name, value in zip(columns, row):
            if value == "":
                empty_counts[name] += 1
            elif name in categories:
                categories[name].add(value)
        date_value = row[index["acq_date"]] if "acq_date" in index else ""
        if date_value:
            dates.add(date_value)
        if "acq_time" in index:
            time_value = row[index["acq_time"]]
            if time_value:
                acq_times.add(time_value)
                if not is_valid_acq_time(time_value):
                    invalid_times += 1
        for name in NUMERIC_COLUMNS:
            if name not in index:
                continue
            number = parse_float(row[index[name]])
            if number is None:
                if row[index[name]] != "":
                    unparsable[name] += 1
                continue
            current_min = numeric_min[name]
            current_max = numeric_max[name]
            numeric_min[name] = number if current_min is None else min(current_min, number)
            numeric_max[name] = number if current_max is None else max(current_max, number)

    ordered_dates = sorted(dates)
    return SourceDiscovery(
        source_id=source.source_id,
        relative_path=source.relative_path.as_posix(),
        row_count=row_count,
        columns=columns,
        empty_counts=empty_counts,
        malformed_row_count=malformed,
        duplicate_row_count=duplicates,
        numeric_min=numeric_min,
        numeric_max=numeric_max,
        unparsable_numeric_counts=unparsable,
        categories={name: tuple(sorted(values)) for name, values in categories.items()},
        date_min=ordered_dates[0] if ordered_dates else None,
        date_max=ordered_dates[-1] if ordered_dates else None,
        distinct_dates=len(ordered_dates),
        distinct_acq_times=len(acq_times),
        invalid_acq_time_count=invalid_times,
    )


def discover_all() -> DiscoveryReport:
    return DiscoveryReport(tuple(discover_source(source) for source in SOURCES))


def write_discovery(report: DiscoveryReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8")


def _empty_discovery(source: SourceContract, message: str) -> SourceDiscovery:
    return SourceDiscovery(
        source_id=source.source_id,
        relative_path=source.relative_path.as_posix(),
        row_count=0,
        columns=(),
        empty_counts={},
        malformed_row_count=0,
        duplicate_row_count=0,
        numeric_min={name: None for name in NUMERIC_COLUMNS},
        numeric_max={name: None for name in NUMERIC_COLUMNS},
        unparsable_numeric_counts={name: 0 for name in NUMERIC_COLUMNS},
        categories={},
        date_min=None,
        date_max=None,
        distinct_dates=0,
        distinct_acq_times=0,
        invalid_acq_time_count=0,
        read_error=message,
    )


def shared_column_names(report: DiscoveryReport) -> tuple[str, ...] | None:
    """Return the column list when every readable source has the same header."""

    readable = [source.columns for source in report.sources if source.read_error is None]
    if not readable or any(columns != readable[0] for columns in readable):
        return None
    if readable[0] != COLUMNS:
        return readable[0]
    return COLUMNS
