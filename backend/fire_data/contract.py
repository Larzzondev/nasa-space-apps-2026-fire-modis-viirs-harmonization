"""Observed contract for the four local FIRMS archive extracts.

The column list and product rules below were read from the CSV files in
``data/raw``. They are not a generic NASA schema. In particular, the VIIRS
archives in this extract use the column names ``brightness`` and
``bright_t31``, and the S-NPP file stores ``instrument`` as ``SNPP``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = BACKEND_ROOT / "data" / "raw"

COLUMNS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_t31",
    "frp",
    "daynight",
    "type",
)

NUMERIC_COLUMNS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "bright_t31",
    "frp",
)

CATEGORY_COLUMNS: tuple[str, ...] = (
    "satellite",
    "instrument",
    "confidence",
    "version",
    "daynight",
    "type",
)

DAYNIGHT_VALUES = frozenset({"D", "N"})
FIRE_TYPE_VALUES = frozenset({"0", "1", "2", "3"})
VIIRS_CONFIDENCE_VALUES = frozenset({"l", "n", "h"})


@dataclass(frozen=True)
class SourceContract:
    source_id: str
    relative_path: Path
    satellites: frozenset[str]
    instrument: str
    version: str
    confidence: str

    @property
    def path(self) -> Path:
        return RAW_DIR / self.relative_path


SOURCES: tuple[SourceContract, ...] = (
    SourceContract(
        source_id="modis",
        relative_path=Path("modis") / "fire_archive_M-C61_850118.csv",
        satellites=frozenset({"Aqua", "Terra"}),
        instrument="MODIS",
        version="61.03",
        confidence="modis_0_100",
    ),
    SourceContract(
        source_id="viirs_noaa20",
        relative_path=Path("viirs_noaa20") / "fire_archive_J1V-C2_850119.csv",
        satellites=frozenset({"N20"}),
        instrument="VIIRS",
        version="2",
        confidence="viirs_lnh",
    ),
    SourceContract(
        source_id="viirs_noaa21",
        relative_path=Path("viirs_noaa21") / "fire_archive_J2V-C2_850120.csv",
        satellites=frozenset({"N21"}),
        instrument="VIIRS",
        version="2",
        confidence="viirs_lnh",
    ),
    SourceContract(
        source_id="viirs_snpp",
        relative_path=Path("viirs_snpp") / "fire_archive_SV-C2_850121.csv",
        satellites=frozenset({"SNPP"}),
        instrument="SNPP",
        version="2",
        confidence="viirs_lnh",
    ),
)

SOURCE_BY_ID = {source.source_id: source for source in SOURCES}
