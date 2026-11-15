"""Ingest four FIRMS ZIP archives for 1–31 July 2024.

The product code in the ZIP name selects the sensor. The filename is not used
as a processing level. A date with no stored row is absent from the file; it
is not recorded as zero detections. The July 7 sample directories are never
written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path, PurePosixPath

from fire_data.contract import BACKEND_ROOT, COLUMNS, RAW_DIR

INCOMING_DIR = BACKEND_ROOT / "data" / "incoming" / "2024-07"
DESTINATION_DIR = BACKEND_ROOT / "data" / "raw" / "monthly_2024_07"
DEFAULT_MANIFEST = BACKEND_ROOT / "reports" / "ingestion_2024_07.json"
PERIOD_START = date(2024, 7, 1)
PERIOD_END = date(2024, 7, 31)
PRODUCT_CODES: tuple[tuple[str, str], ...] = (
    ("M-C61", "modis"),
    ("SV-C2", "viirs_snpp"),
    ("J1V-C2", "viirs_noaa20"),
    ("J2V-C2", "viirs_noaa21"),
)
SENSOR_ORDER = ("modis", "viirs_snpp", "viirs_noaa20", "viirs_noaa21")
EXPECTED_SATELLITES = {
    "modis": frozenset({"Terra", "Aqua"}),
    "viirs_snpp": frozenset({"SNPP"}),
    "viirs_noaa20": frozenset({"N20"}),
    "viirs_noaa21": frozenset({"N21"}),
}
SAMPLE_DIRECTORIES = (
    RAW_DIR / "modis",
    RAW_DIR / "viirs_snpp",
    RAW_DIR / "viirs_noaa20",
    RAW_DIR / "viirs_noaa21",
)
ABSENT_DATE_POLICY = (
    "A date with no stored row is absent from the archive. "
    "It is not a count of zero fire detections."
)


class IngestError(ValueError):
    """The archive cannot be accepted."""


def period_dates() -> list[str]:
    count = (PERIOD_END - PERIOD_START).days + 1
    return [(PERIOD_START + timedelta(days=offset)).isoformat() for offset in range(count)]


def identify_sensor(filename: str) -> str:
    """Return the sensor id when the ZIP name contains exactly one product code."""

    stem = Path(filename).name
    found = []
    for code, sensor in PRODUCT_CODES:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])", stem, flags=re.IGNORECASE):
            found.append((code, sensor))
    if len(found) == 1:
        return found[0][1]
    if len(found) > 1:
        codes = ", ".join(code for code, _sensor in found)
        raise IngestError(f"{stem} matches more than one product code ({codes})")
    raise IngestError(f"{stem} does not contain a known FIRMS product code")


def discover_archives(incoming: Path) -> dict[str, object]:
    archives = sorted(path for path in incoming.glob("*.zip") if path.is_file())
    assigned: dict[str, Path] = {}
    grouped: dict[str, list[Path]] = {sensor: [] for sensor in SENSOR_ORDER}
    rejected: list[dict[str, str]] = []
    for path in archives:
        try:
            sensor = identify_sensor(path.name)
        except IngestError as error:
            rejected.append({"filename": path.name, "reason": str(error)})
            continue
        grouped[sensor].append(path)
    for sensor, paths in grouped.items():
        if len(paths) == 1:
            assigned[sensor] = paths[0]
        elif len(paths) > 1:
            names = ", ".join(path.name for path in paths)
            for path in paths:
                rejected.append(
                    {
                        "filename": path.name,
                        "reason": f"Duplicate {sensor} archives ({names}). None of them was selected.",
                    }
                )
    missing = [sensor for sensor in SENSOR_ORDER if sensor not in assigned]
    return {"assigned": assigned, "missing_sensors": missing, "rejected": rejected}


def assert_destination_allowed(destination: Path) -> None:
    resolved = destination.resolve()
    for sample in SAMPLE_DIRECTORIES:
        sample_resolved = sample.resolve()
        if resolved == sample_resolved or _is_relative_to(resolved, sample_resolved):
            raise IngestError(f"{destination} is inside a July 7 sample directory")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _member_parts(filename: str) -> tuple[str, ...]:
    normalized = filename.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise IngestError(f"ZIP member escapes the archive: {filename}")
    parts = tuple(part for part in PurePosixPath(normalized).parts if part not in {"", "."})
    if any(part == ".." for part in parts):
        raise IngestError(f"ZIP member escapes the archive: {filename}")
    return parts


def inspect_zip(path: Path) -> tuple[str, bytes, list[str]]:
    """Return the single CSV member name, its bytes, and non-CSV member names."""

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as error:
        raise IngestError(f"{path.name} is not a readable ZIP archive") from error
    csv_members: list[tuple[str, bytes]] = []
    skipped: list[str] = []
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            parts = _member_parts(info.filename)
            if not parts:
                continue
            if parts[-1].lower().endswith(".csv"):
                csv_members.append((parts[-1], archive.read(info)))
            else:
                skipped.append(info.filename)
    if len(csv_members) != 1:
        raise IngestError(f"{path.name} contains {len(csv_members)} CSV members; expected one")
    name, payload = csv_members[0]
    return name, payload, skipped


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_csv(payload: bytes, sensor: str) -> dict[str, object]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise IngestError("CSV is not UTF-8") from error
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as error:
        raise IngestError("CSV has no header row") from error
    if tuple(header) != COLUMNS:
        raise IngestError("CSV header does not match the observed 15-column contract")
    date_index = COLUMNS.index("acq_date")
    satellite_index = COLUMNS.index("satellite")
    counts: Counter[str] = Counter()
    satellites: Counter[str] = Counter()
    invalid_dates: Counter[str] = Counter()
    record_count = 0
    allowed = EXPECTED_SATELLITES[sensor]
    unexpected: set[str] = set()
    for row in reader:
        if not row or all(not cell.strip() for cell in row):
            continue
        record_count += 1
        if len(row) != len(COLUMNS):
            raise IngestError(f"CSV row {record_count + 1} does not have 15 columns")
        raw_date = row[date_index]
        try:
            parsed = date.fromisoformat(raw_date)
        except ValueError:
            invalid_dates[raw_date] += 1
            continue
        if parsed.isoformat() != raw_date:
            invalid_dates[raw_date] += 1
            continue
        counts[raw_date] += 1
        satellite = row[satellite_index]
        satellites[satellite] += 1
        if satellite not in allowed:
            unexpected.add(satellite)
    if invalid_dates:
        shown = ", ".join(sorted(invalid_dates))
        raise IngestError(f"CSV contains acquisition dates that are not YYYY-MM-DD: {shown}")
    if unexpected:
        shown = ", ".join(sorted(unexpected))
        raise IngestError(f"CSV satellite values are not expected for {sensor}: {shown}")
    expected = set(period_dates())
    present = {day: counts[day] for day in sorted(counts) if day in expected}
    outside = {day: counts[day] for day in sorted(counts) if day not in expected}
    absent = [day for day in period_dates() if day not in counts]
    if outside:
        shown = ", ".join(outside)
        raise IngestError(f"CSV contains acquisition dates outside July 2024: {shown}")
    return {
        "record_count": record_count,
        "dates_present": present,
        "dates_absent": absent,
        "date_min": min(present) if present else None,
        "date_max": max(present) if present else None,
        "satellites_observed": dict(sorted(satellites.items())),
        "coverage_status": "complete" if not absent else "incomplete",
    }


def _target_path(destination: Path, sensor: str, csv_name: str) -> Path:
    target = (destination / sensor / Path(csv_name).name).resolve()
    root = destination.resolve()
    if not _is_relative_to(target, root):
        raise IngestError(f"Refusing to write outside {destination}")
    return target


def _empty_sensor(sensor: str, **extra: object) -> dict[str, object]:
    return {
        "sensor": sensor,
        "validation_status": "failed",
        "processing_stream": None,
        "processing_stream_note": "Not assigned. The ZIP name and the version field are not a processing level.",
        "absent_date_policy": ABSENT_DATE_POLICY,
        **extra,
    }


def ingest_one(path: Path, sensor: str, destination: Path, *, dry_run: bool) -> dict[str, object]:
    record = _empty_sensor(
        sensor,
        zip_filename=path.name,
        zip_bytes=path.stat().st_size,
        zip_sha256=_sha256_file(path),
        extracted=False,
    )
    try:
        csv_name, payload, skipped = inspect_zip(path)
        checked = validate_csv(payload, sensor)
        target = _target_path(destination, sensor, csv_name)
        record.update(checked)
        record.update(
            {
                "csv_filename": csv_name,
                "csv_bytes": len(payload),
                "csv_sha256": _sha256(payload),
                "skipped_members": skipped,
                "destination": target.as_posix(),
                "validation_status": "passed",
                "issues": [],
            }
        )
    except IngestError as error:
        record["issues"] = [str(error)]
        return record
    if target.exists():
        record["validation_status"] = "failed"
        record["extracted"] = False
        record["issues"] = [f"{target.name} already exists and was not overwritten"]
        return record
    if dry_run:
        return record
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    written = _sha256_file(target)
    if written != record["csv_sha256"]:
        record["validation_status"] = "failed"
        record["issues"] = ["Extracted CSV checksum does not match the ZIP member"]
        return record
    record["extracted"] = True
    return record


def build_manifest(incoming: Path, destination: Path, *, dry_run: bool) -> dict[str, object]:
    assert_destination_allowed(destination)
    if not incoming.is_dir():
        raise IngestError(f"Incoming directory does not exist: {incoming}")
    found = discover_archives(incoming)
    sensors = []
    for sensor in SENSOR_ORDER:
        path = found["assigned"].get(sensor)
        if path is None:
            sensors.append(
                _empty_sensor(
                    sensor,
                    issues=[f"No ZIP archive for {sensor} in {incoming}"],
                )
            )
            continue
        sensors.append(ingest_one(path, sensor, destination, dry_run=dry_run))
    failures = [item for item in sensors if item["validation_status"] != "passed"]
    return {
        "period": {"start": PERIOD_START.isoformat(), "end": PERIOD_END.isoformat()},
        "dry_run": dry_run,
        "incoming_dir": incoming.as_posix(),
        "destination_dir": destination.as_posix(),
        "missing_sensors": found["missing_sensors"],
        "rejected_archives": found["rejected"],
        "sensors": sensors,
        "harmonization_coefficients_calculated": False,
        "passed": not failures and not found["rejected"] and not found["missing_sensors"],
    }


def write_manifest(manifest: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _print_summary(manifest: dict[str, object]) -> None:
    mode = "dry-run" if manifest["dry_run"] else "ingest"
    print(f"{mode}: passed={manifest['passed']}")
    missing = manifest["missing_sensors"]
    if missing:
        print("missing archives: " + ", ".join(missing))
    for item in manifest["rejected_archives"]:
        print(f"rejected {item['filename']}: {item['reason']}")
    for sensor in manifest["sensors"]:
        status = sensor["validation_status"]
        absent = sensor.get("dates_absent")
        absent_count = len(absent) if isinstance(absent, list) else "n/a"
        print(
            f"{sensor['sensor']}: {status} records={sensor.get('record_count', 'n/a')} "
            f"dates_absent={absent_count}"
        )
        for issue in sensor.get("issues", []):
            print(f"  {issue}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest the four July 2024 FIRMS ZIP archives.")
    parser.add_argument("--incoming", type=Path, default=INCOMING_DIR)
    parser.add_argument("--destination", type=Path, default=DESTINATION_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dry-run", action="store_true", help="Validate the ZIPs and do not extract them")
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(args.incoming, args.destination, dry_run=args.dry_run)
    except IngestError as error:
        print(f"error: {error}")
        return 1
    _print_summary(manifest)
    if not args.dry_run:
        write_manifest(manifest, args.manifest)
        print(f"Wrote {args.manifest}")
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
