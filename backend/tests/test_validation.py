from pathlib import Path

from fire_data.contract import COLUMNS, SOURCES, SourceContract
from fire_data.fields import is_valid_acq_date, is_valid_acq_time
from fire_data.validate import validate_all, validate_row, validate_source

MODIS = SOURCES[0]
SNPP = SOURCES[3]


def observed_row(**overrides: str) -> list[str]:
    values = {
        "latitude": "19.9768",
        "longitude": "41.4337",
        "brightness": "302.8",
        "scan": "1.8",
        "track": "1.3",
        "acq_date": "2024-07-07",
        "acq_time": "0000",
        "satellite": "Aqua",
        "instrument": "MODIS",
        "confidence": "44",
        "version": "61.03",
        "bright_t31": "292.8",
        "frp": "7.2",
        "daynight": "N",
        "type": "0",
    }
    values.update(overrides)
    return [values[column] for column in COLUMNS]


def test_extracted_archives_pass_validation():
    report = validate_all()

    assert report.passed, [(source.source_id, source.issues[:3]) for source in report.sources if not source.passed]
    assert {source.source_id: source.row_count for source in report.sources} == {
        "modis": 20410,
        "viirs_noaa20": 82372,
        "viirs_noaa21": 87637,
        "viirs_snpp": 86840,
    }


def test_missing_archive_is_reported():
    missing = SourceContract(
        source_id="modis",
        relative_path=Path("modis") / "not-extracted.csv",
        satellites=MODIS.satellites,
        instrument=MODIS.instrument,
        version=MODIS.version,
        confidence=MODIS.confidence,
    )

    result = validate_source(missing)

    assert not result.passed
    assert result.issues[0].message.startswith("Missing archive:")


def test_header_must_match_the_extracted_columns(tmp_path: Path):
    archive = tmp_path / "bad-header.csv"
    archive.write_text("latitude,longitude\n1,2\n", encoding="utf-8")

    result = validate_source(MODIS, archive)

    assert not result.passed
    assert result.issues[0].line_number == 1


def test_row_rules_reject_values_outside_the_observed_contract():
    latitude = validate_row(MODIS, 2, observed_row(latitude="95"))
    confidence = validate_row(MODIS, 2, observed_row(confidence="n"))
    viirs_instrument = validate_row(
        SNPP,
        2,
        observed_row(satellite="SNPP", instrument="VIIRS", confidence="n", version="2"),
    )
    short_row = validate_row(MODIS, 2, observed_row()[:-1])

    assert [issue.column for issue in latitude] == ["latitude"]
    assert [issue.column for issue in confidence] == ["confidence"]
    assert [issue.column for issue in viirs_instrument] == ["instrument"]
    assert short_row[0].column is None
    assert "15 columns" in short_row[0].message


def test_time_and_date_parsers():
    assert is_valid_acq_time("0000")
    assert is_valid_acq_time("2359")
    assert not is_valid_acq_time("2400")
    assert not is_valid_acq_time("007")
    assert is_valid_acq_date("2024-07-07")
    assert not is_valid_acq_date("2024-02-31")
    assert not is_valid_acq_date("07/07/2024")
