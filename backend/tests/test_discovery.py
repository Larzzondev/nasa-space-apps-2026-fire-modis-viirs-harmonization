import json

from fire_data.contract import COLUMNS, SOURCE_BY_ID
from fire_data.discover import discover_all, shared_column_names
from fire_data.__main__ import main

EXPECTED_ROWS = {
    "modis": 20410,
    "viirs_noaa20": 82372,
    "viirs_noaa21": 87637,
    "viirs_snpp": 86840,
}


def test_discovery_records_the_extracted_archives():
    report = discover_all()

    assert [source.source_id for source in report.sources] == list(EXPECTED_ROWS)
    assert shared_column_names(report) == COLUMNS
    for source in report.sources:
        contract = SOURCE_BY_ID[source.source_id]
        assert source.read_error is None
        assert source.row_count == EXPECTED_ROWS[source.source_id]
        assert source.columns == COLUMNS
        assert source.malformed_row_count == 0
        assert source.duplicate_row_count == 0
        assert source.invalid_acq_time_count == 0
        assert source.empty_counts == {column: 0 for column in COLUMNS}
        assert all(count == 0 for count in source.unparsable_numeric_counts.values())
        assert source.date_min == "2024-07-07"
        assert source.date_max == "2024-07-07"
        assert source.distinct_dates == 1
        assert set(source.categories["satellite"]) == set(contract.satellites)
        assert source.categories["instrument"] == (contract.instrument,)
        assert source.categories["version"] == (contract.version,)
        assert set(source.categories["daynight"]) == {"D", "N"}
        assert set(source.categories["type"]) == {"0", "1", "2", "3"}
        assert source.numeric_min["latitude"] is not None
        assert source.numeric_max["latitude"] is not None
        assert -90 <= source.numeric_min["latitude"] <= source.numeric_max["latitude"] <= 90
        assert source.numeric_min["longitude"] is not None
        assert source.numeric_max["longitude"] is not None
        assert -180 <= source.numeric_min["longitude"] <= source.numeric_max["longitude"] <= 180
        if contract.confidence == "modis_0_100":
            assert all(value.isdigit() and 0 <= int(value) <= 100 for value in source.categories["confidence"])
        else:
            assert set(source.categories["confidence"]) == {"h", "l", "n"}


def test_snpp_archive_keeps_instrument_value_from_the_file():
    snpp = next(source for source in discover_all().sources if source.source_id == "viirs_snpp")

    assert snpp.categories["instrument"] == ("SNPP",)
    assert snpp.categories["satellite"] == ("SNPP",)


def test_discover_command_writes_json(tmp_path):
    output = tmp_path / "discovery.json"

    assert main(["discover", "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [item["row_count"] for item in payload["sources"]] == list(EXPECTED_ROWS.values())
    assert payload["sources"][0]["columns"] == list(COLUMNS)
