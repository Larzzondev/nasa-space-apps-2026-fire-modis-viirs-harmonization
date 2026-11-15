"""Load each FIRMS archive once into compact arrays.

Python lists exist only while an archive is being read. The returned table keeps
one numeric array per column. Terra and Aqua are later index selections of the
MODIS arrays, not another copy of the CSV.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fire_data.contract import COLUMNS, SOURCES, SourceContract
from fire_data.fields import is_valid_acq_time, parse_float
from fire_data.readers import read_archive

_NUMERIC = ("latitude", "longitude", "brightness", "scan", "track", "bright_t31", "frp")


@dataclass
class DetectionTable:
    source_id: str
    archive: str
    archive_path: str
    confidence_kind: str
    line_number: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    brightness: np.ndarray
    scan: np.ndarray
    track: np.ndarray
    bright_t31: np.ndarray
    frp: np.ndarray
    acq_hhmm: np.ndarray
    hour_utc: np.ndarray
    satellite: np.ndarray
    confidence: np.ndarray
    daynight: np.ndarray
    dates: tuple[str, ...]

    def __len__(self) -> int:
        return int(self.frp.size)


def load_source(source: SourceContract, path: Path | None = None) -> DetectionTable:
    archive = source.path if path is None else path
    if not archive.is_file():
        raise FileNotFoundError(f"Missing archive: {archive}")

    index = {name: position for position, name in enumerate(COLUMNS)}
    numeric = {name: [] for name in _NUMERIC}
    line_numbers: list[int] = []
    hhmm: list[int] = []
    satellite: list[str] = []
    confidence: list[str] = []
    daynight: list[str] = []
    dates: set[str] = set()

    with read_archive(archive) as (header, rows):
        if tuple(header) != COLUMNS:
            raise ValueError(f"{archive.name} header does not match the observed contract")
        for line_number, row in rows:
            if len(row) != len(COLUMNS):
                raise ValueError(f"{archive.name} line {line_number} does not have {len(COLUMNS)} fields")
            for name in _NUMERIC:
                value = parse_float(row[index[name]])
                if value is None:
                    raise ValueError(f"{archive.name} line {line_number} has a non-finite {name}")
                numeric[name].append(value)
            acq_time = row[index["acq_time"]]
            if not is_valid_acq_time(acq_time):
                raise ValueError(f"{archive.name} line {line_number} has an invalid acq_time")
            line_numbers.append(line_number)
            hhmm.append(int(acq_time))
            satellite.append(row[index["satellite"]])
            confidence.append(row[index["confidence"]])
            daynight.append(row[index["daynight"]])
            dates.add(row[index["acq_date"]])

    if not line_numbers:
        raise ValueError(f"{archive.name} has a header but no detections")

    acq_hhmm = np.asarray(hhmm, dtype=np.uint16)
    return DetectionTable(
        source_id=source.source_id,
        archive=source.relative_path.as_posix(),
        archive_path=str(archive),
        confidence_kind=source.confidence,
        line_number=np.asarray(line_numbers, dtype=np.int32),
        latitude=np.asarray(numeric["latitude"], dtype=np.float64),
        longitude=np.asarray(numeric["longitude"], dtype=np.float64),
        brightness=np.asarray(numeric["brightness"], dtype=np.float64),
        scan=np.asarray(numeric["scan"], dtype=np.float64),
        track=np.asarray(numeric["track"], dtype=np.float64),
        bright_t31=np.asarray(numeric["bright_t31"], dtype=np.float64),
        frp=np.asarray(numeric["frp"], dtype=np.float64),
        acq_hhmm=acq_hhmm,
        hour_utc=(acq_hhmm // 100).astype(np.int8),
        satellite=np.asarray(satellite, dtype="U8"),
        confidence=np.asarray(confidence, dtype="U8"),
        daynight=np.asarray(daynight, dtype="U1"),
        dates=tuple(sorted(dates)),
    )


def load_all(sources: tuple[SourceContract, ...] = SOURCES) -> list[DetectionTable]:
    return [load_source(source) for source in sources]


def read_source_rows(path: Path, line_numbers: set[int]) -> dict[int, dict[str, str]]:
    """Re-read only the requested CSV lines and keep their original text.

    This is a streaming second pass. It stores the flagged rows, not another
    copy of the archive.
    """

    if not line_numbers:
        return {}
    found: dict[int, dict[str, str]] = {}
    with read_archive(path) as (header, rows):
        if tuple(header) != COLUMNS:
            raise ValueError(f"{path.name} header does not match the observed contract")
        for line_number, row in rows:
            if line_number not in line_numbers:
                continue
            if len(row) != len(COLUMNS):
                raise ValueError(f"{path.name} line {line_number} does not have {len(COLUMNS)} fields")
            found[line_number] = {column: row[position] for position, column in enumerate(COLUMNS)}
            if len(found) == len(line_numbers):
                break
    missing = line_numbers - found.keys()
    if missing:
        sample = ", ".join(str(number) for number in sorted(missing)[:5])
        raise ValueError(f"{path.name} is missing source lines {sample}")
    return found
