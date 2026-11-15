"""Check the extracted archives against the contract read from those files."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from pathlib import Path

from fire_data.contract import COLUMNS, NUMERIC_COLUMNS, SOURCES, SourceContract
from fire_data.fields import (
    is_valid_acq_date,
    is_valid_acq_time,
    is_valid_daynight,
    is_valid_fire_type,
    is_valid_modis_confidence,
    is_valid_viirs_confidence,
    parse_float,
)
from fire_data.readers import read_archive

ISSUE_LIMIT = 25


@dataclass(frozen=True)
class ValidationIssue:
    source_id: str
    line_number: int | None
    column: str | None
    message: str


@dataclass(frozen=True)
class SourceValidation:
    source_id: str
    relative_path: str
    row_count: int
    issue_count: int
    issues: tuple[ValidationIssue, ...]

    @property
    def passed(self) -> bool:
        return self.issue_count == 0


@dataclass(frozen=True)
class ValidationReport:
    sources: tuple[SourceValidation, ...]

    @property
    def passed(self) -> bool:
        return all(source.passed for source in self.sources)


def validate_all() -> ValidationReport:
    return ValidationReport(tuple(validate_source(source) for source in SOURCES))


def validate_source(source: SourceContract, path: Path | None = None) -> SourceValidation:
    archive = source.path if path is None else path
    label = source.relative_path.as_posix() if path is None else archive.name
    if not archive.is_file():
        issue = ValidationIssue(source.source_id, None, None, f"Missing archive: {label}")
        return SourceValidation(source.source_id, label, 0, 1, (issue,))

    try:
        with read_archive(archive) as (header, rows):
            return _validate_rows(source, label, header, rows)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        issue = ValidationIssue(source.source_id, None, None, str(exc))
        return SourceValidation(source.source_id, source.relative_path.as_posix(), 0, 1, (issue,))


def _validate_rows(
    source: SourceContract,
    label: str,
    header: list[str],
    rows: Iterator[tuple[int, list[str]]],
) -> SourceValidation:
    if tuple(header) != COLUMNS:
        issue = ValidationIssue(
            source.source_id,
            1,
            None,
            f"Header {header} does not match the extracted column list",
        )
        return SourceValidation(source.source_id, label, 0, 1, (issue,))

    issues: list[ValidationIssue] = []
    issue_count = 0
    row_count = 0
    for line_number, row in rows:
        row_count += 1
        for issue in validate_row(source, line_number, row):
            issue_count += 1
            if len(issues) < ISSUE_LIMIT:
                issues.append(issue)

    if row_count == 0:
        issue_count += 1
        issues.append(ValidationIssue(source.source_id, None, None, "Archive has no data rows"))

    return SourceValidation(
        source.source_id,
        label,
        row_count,
        issue_count,
        tuple(issues),
    )


def validate_row(
    source: SourceContract,
    line_number: int,
    row: list[str],
) -> tuple[ValidationIssue, ...]:
    if len(row) != len(COLUMNS):
        return (
            ValidationIssue(
                source.source_id,
                line_number,
                None,
                f"Expected {len(COLUMNS)} columns, found {len(row)}",
            ),
        )

    issues: list[ValidationIssue] = []
    values = dict(zip(COLUMNS, row))

    for name in COLUMNS:
        if values[name] == "":
            issues.append(ValidationIssue(source.source_id, line_number, name, "Value is empty"))

    if values["latitude"] != "":
        latitude = parse_float(values["latitude"])
        if latitude is None or not -90 <= latitude <= 90:
            issues.append(
                ValidationIssue(
                    source.source_id,
                    line_number,
                    "latitude",
                    "Latitude must be a number from -90 through 90",
                )
            )
    if values["longitude"] != "":
        longitude = parse_float(values["longitude"])
        if longitude is None or not -180 <= longitude <= 180:
            issues.append(
                ValidationIssue(
                    source.source_id,
                    line_number,
                    "longitude",
                    "Longitude must be a number from -180 through 180",
                )
            )

    for name in NUMERIC_COLUMNS:
        if name in {"latitude", "longitude"} or values[name] == "":
            continue
        if parse_float(values[name]) is None:
            issues.append(
                ValidationIssue(source.source_id, line_number, name, "Value must be a finite number")
            )

    if values["acq_date"] and not is_valid_acq_date(values["acq_date"]):
        issues.append(
            ValidationIssue(source.source_id, line_number, "acq_date", "Date must be YYYY-MM-DD")
        )
    if values["acq_time"] and not is_valid_acq_time(values["acq_time"]):
        issues.append(
            ValidationIssue(
                source.source_id,
                line_number,
                "acq_time",
                "Time must be a four-digit HHMM value",
            )
        )
    if values["satellite"] and values["satellite"] not in source.satellites:
        allowed = ", ".join(sorted(source.satellites))
        issues.append(
            ValidationIssue(
                source.source_id,
                line_number,
                "satellite",
                f"Satellite must be one of: {allowed}",
            )
        )
    if values["instrument"] and values["instrument"] != source.instrument:
        issues.append(
            ValidationIssue(
                source.source_id,
                line_number,
                "instrument",
                f"Instrument must be {source.instrument}",
            )
        )
    if values["confidence"]:
        valid_confidence = (
            is_valid_modis_confidence(values["confidence"])
            if source.confidence == "modis_0_100"
            else is_valid_viirs_confidence(values["confidence"])
        )
        if not valid_confidence:
            expected = "an integer from 0 through 100" if source.confidence == "modis_0_100" else "l, n, or h"
            issues.append(
                ValidationIssue(
                    source.source_id,
                    line_number,
                    "confidence",
                    f"Confidence must be {expected}",
                )
            )
    if values["version"] and values["version"] != source.version:
        issues.append(
            ValidationIssue(
                source.source_id,
                line_number,
                "version",
                f"Version must be {source.version}",
            )
        )
    if values["daynight"] and not is_valid_daynight(values["daynight"]):
        issues.append(ValidationIssue(source.source_id, line_number, "daynight", "Daynight must be D or N"))
    if values["type"] and not is_valid_fire_type(values["type"]):
        issues.append(
            ValidationIssue(source.source_id, line_number, "type", "Type must be 0, 1, 2, or 3")
        )
    return tuple(issues)
