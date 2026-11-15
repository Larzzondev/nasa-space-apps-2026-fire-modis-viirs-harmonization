"""Field parsers for values observed in the extracted archives."""

from __future__ import annotations

import math
from datetime import datetime

from fire_data.contract import DAYNIGHT_VALUES, FIRE_TYPE_VALUES, VIIRS_CONFIDENCE_VALUES


def parse_float(value: str) -> float | None:
    try:
        number = float(value)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def is_valid_acq_date(value: str) -> bool:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%d") == value


def is_valid_acq_time(value: str) -> bool:
    if len(value) != 4 or not value.isdigit():
        return False
    hour = int(value[:2])
    minute = int(value[2:])
    return 0 <= hour <= 23 and 0 <= minute <= 59


def is_valid_daynight(value: str) -> bool:
    return value in DAYNIGHT_VALUES


def is_valid_fire_type(value: str) -> bool:
    return value in FIRE_TYPE_VALUES


def is_valid_modis_confidence(value: str) -> bool:
    if not value.isdigit():
        return False
    confidence = int(value)
    return 0 <= confidence <= 100


def is_valid_viirs_confidence(value: str) -> bool:
    return value in VIIRS_CONFIDENCE_VALUES
