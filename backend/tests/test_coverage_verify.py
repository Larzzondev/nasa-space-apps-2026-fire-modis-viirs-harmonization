from datetime import datetime, timezone

import pytest

from fire_data.coverage_verify import (
    classify_firms_csv,
    classify_l2_swath,
    parse_utc,
    processing_stream_from_version,
    stated_l2_alert,
)


def test_empty_local_rows_are_not_zero_detections() -> None:
    assert classify_firms_csv(local_rows=0) == "unknown"
    assert classify_firms_csv(local_rows=0) != "confirmed_zero_detections"


def test_cmr_absence_does_not_make_firms_or_l2_unavailable() -> None:
    assert classify_firms_csv(local_rows=0) == "unknown"
    assert classify_l2_swath(cmr_granules=0, alert_id=None) == "unknown"


def test_explicit_alert_marks_only_the_l2_swath() -> None:
    assert classify_l2_swath(cmr_granules=79, alert_id="geolocation") == "confirmed_source_unavailable"
    assert classify_firms_csv(local_rows=0) == "unknown"


def test_catalogued_granules_are_not_verified_fire_pixels() -> None:
    assert classify_l2_swath(cmr_granules=63, alert_id=None) == "confirmed_data_available"


def test_local_rows_are_direct_firms_evidence() -> None:
    assert classify_firms_csv(local_rows=15643) == "confirmed_data_available"


def test_july24_outage_is_not_extended() -> None:
    inside = stated_l2_alert(
        parse_utc("2024-07-24T05:28:00Z"),
        parse_utc("2024-07-24T18:22:00Z"),
    )
    after = stated_l2_alert(
        parse_utc("2024-07-24T18:22:00Z"),
        parse_utc("2024-07-25T00:00:00Z"),
    )
    widened = stated_l2_alert(
        parse_utc("2024-07-24T05:28:00Z"),
        parse_utc("2024-07-25T00:00:00Z"),
    )
    assert inside == "july24"
    assert after is None
    assert widened is None


def test_geolocation_window_keeps_its_stated_end() -> None:
    before_recovery = stated_l2_alert(
        parse_utc("2024-07-16T00:00:00Z"),
        parse_utc("2024-07-16T17:42:00Z"),
    )
    after_recovery = stated_l2_alert(
        parse_utc("2024-07-16T17:42:00Z"),
        parse_utc("2024-07-17T00:00:00Z"),
    )
    july25 = stated_l2_alert(
        parse_utc("2024-07-25T00:00:00Z"),
        parse_utc("2024-07-26T00:00:00Z"),
    )
    assert before_recovery == "geolocation"
    assert after_recovery is None
    assert july25 is None


def test_version_text_does_not_assign_a_processing_stream() -> None:
    assert processing_stream_from_version("2") is None
    assert processing_stream_from_version("61.03") is None
    assert processing_stream_from_version("2.0NRT") is None


def test_negative_counts_are_rejected() -> None:
    with pytest.raises(ValueError):
        classify_firms_csv(local_rows=-1)
    with pytest.raises(ValueError):
        stated_l2_alert(
            datetime(2024, 7, 24, 18, 22, tzinfo=timezone.utc),
            datetime(2024, 7, 24, 18, 22, tzinfo=timezone.utc),
        )


def test_investigation_record_keeps_unknown_intervals_unknown() -> None:
    from fire_data.coverage_investigation import build_investigation

    report = build_investigation()
    by_key = {(item["date"], item["interval"]): item for item in report["intervals"]}
    assert by_key[("2024-07-11", "full UTC date")]["l2_classification"] == "confirmed_source_unavailable"
    assert by_key[("2024-07-11", "full UTC date")]["firms_classification"] == "unknown"
    assert by_key[("2024-07-16", "17:42–23:59 UTC")]["firms_classification"] == "confirmed_data_available"
    assert by_key[("2024-07-16", "17:42–23:59 UTC")]["l2_classification"] == "confirmed_data_available"
    for day in ("2024-07-25", "2024-07-26", "2024-07-27", "2024-07-28"):
        item = by_key[(day, "full UTC date")]
        assert item["firms_classification"] == "unknown"
        assert item["l2_classification"] == "unknown"
        assert item["local_rows"] == 0
    after_outage = by_key[("2024-07-24", "18:22–23:59 UTC")]
    assert after_outage["l2_classification"] == "unknown"
    assert after_outage["alert_id_applied"] is None
    before_resume = by_key[("2024-07-29", "00:00–15:24 UTC")]
    assert before_resume["firms_classification"] == "unknown"
    assert before_resume["l2_classification"] == "unknown"
    classes = {
        value
        for item in report["intervals"]
        for value in (item["firms_classification"], item["l2_classification"])
    }
    assert "confirmed_zero_detections" not in classes
    assert "archive_delivery_gap" not in classes
    assert report["local_archive"]["processing_stream_in_file"] is None
