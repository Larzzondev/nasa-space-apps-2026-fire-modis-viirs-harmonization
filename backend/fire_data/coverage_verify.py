"""Classify S-NPP coverage without turning a missing date into zero fires.

The FIRMS CSV, the Level-2 swath, and CMR granule metadata are different
records. A version string is never a processing stream. A CMR hit count of
zero is not a FIRMS outage and is not zero fire detections.
"""

from __future__ import annotations

from datetime import datetime, timezone

CLASSIFICATIONS = (
    "confirmed_data_available",
    "confirmed_zero_detections",
    "confirmed_source_unavailable",
    "archive_delivery_gap",
    "unknown",
)

# LP DAAC stated these windows. The end is included. An interval that continues
# past the end is not covered, so the statement is not extended.
GEOLOCATION_START = datetime(2024, 7, 9, 21, 42, tzinfo=timezone.utc)
GEOLOCATION_END = datetime(2024, 7, 16, 17, 42, tzinfo=timezone.utc)
JULY24_OUTAGE_START = datetime(2024, 7, 24, 5, 28, tzinfo=timezone.utc)
JULY24_OUTAGE_END = datetime(2024, 7, 24, 18, 22, tzinfo=timezone.utc)


def processing_stream_from_version(_version: str) -> None:
    """The stored version text is not a processing level."""

    return None


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{value} has no timezone")
    return parsed.astimezone(timezone.utc)


def stated_l2_alert(start: datetime, end: datetime) -> str | None:
    """Return an alert id only when the whole interval sits inside a stated window."""

    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("interval bounds must be timezone-aware")
    if end <= start:
        raise ValueError("interval end must be after its start")
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    if start >= GEOLOCATION_START and end <= GEOLOCATION_END:
        return "geolocation"
    if start >= JULY24_OUTAGE_START and end <= JULY24_OUTAGE_END:
        return "july24"
    return None


def classify_firms_csv(*, local_rows: int) -> str:
    """Classify the local FIRMS CSV only.

    Rows in the file are direct evidence that this archive contains detections.
    Zero rows do not establish a FIRMS outage or zero fire detections.
    """

    if local_rows < 0:
        raise ValueError("local_rows cannot be negative")
    if local_rows > 0:
        return "confirmed_data_available"
    return "unknown"


def classify_l2_swath(*, cmr_granules: int | None, alert_id: str | None) -> str:
    """Classify the Level-2 swath named by an alert, not the FIRMS CSV.

    Granule metadata can show that catalog records exist. It does not verify
    fire pixels. A hit count of zero, without an explicit alert, stays unknown.
    """

    if cmr_granules is not None and cmr_granules < 0:
        raise ValueError("cmr_granules cannot be negative")
    if alert_id is not None:
        return "confirmed_source_unavailable"
    if cmr_granules is not None and cmr_granules > 0:
        return "confirmed_data_available"
    return "unknown"
