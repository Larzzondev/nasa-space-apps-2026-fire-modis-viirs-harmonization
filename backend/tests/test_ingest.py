import json
import zipfile
from pathlib import Path

import pytest

from fire_data.contract import COLUMNS, RAW_DIR
from fire_data.ingest import (
    IngestError,
    build_manifest,
    identify_sensor,
    main,
    period_dates,
)

HEADER = ",".join(COLUMNS)


def row(acq_date: str, satellite: str) -> str:
    values = {
        "latitude": "10.0",
        "longitude": "20.0",
        "brightness": "300.0",
        "scan": "0.4",
        "track": "0.4",
        "acq_date": acq_date,
        "acq_time": "0123",
        "satellite": satellite,
        "instrument": "VIIRS",
        "confidence": "n",
        "version": "2",
        "bright_t31": "290.0",
        "frp": "1.5",
        "daynight": "N",
        "type": "0",
    }
    if satellite in {"Terra", "Aqua"}:
        values["instrument"] = "MODIS"
        values["confidence"] = "80"
        values["version"] = "61.03"
    return ",".join(values[column] for column in COLUMNS)


def write_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def july_csv(satellite: str, dates: list[str] | None = None) -> str:
    chosen = dates if dates is not None else period_dates()
    lines = [HEADER, *(row(day, satellite) for day in chosen)]
    return "\n".join(lines) + "\n"


def place_four(incoming: Path, snpp_dates: list[str] | None = None) -> None:
    write_zip(incoming / "DL_FIRE_M-C61_1.zip", {"fire_archive_M-C61_1.csv": july_csv("Terra") + row("2024-07-02", "Aqua") + "\n"})
    write_zip(incoming / "DL_FIRE_SV-C2_2.zip", {"fire_nrt_SV-C2_2.csv": july_csv("SNPP", snpp_dates)})
    write_zip(incoming / "DL_FIRE_J1V-C2_3.zip", {"fire_archive_J1V-C2_3.csv": july_csv("N20")})
    write_zip(incoming / "DL_FIRE_J2V-C2_4.zip", {"fire_archive_J2V-C2_4.csv": july_csv("N21")})


def test_product_code_selects_one_sensor() -> None:
    assert identify_sensor("DL_FIRE_M-C61_850118.zip") == "modis"
    assert identify_sensor("DL_FIRE_SV-C2_850121.zip") == "viirs_snpp"
    assert identify_sensor("DL_FIRE_J1V-C2_850119.zip") == "viirs_noaa20"
    assert identify_sensor("DL_FIRE_J2V-C2_850120.zip") == "viirs_noaa21"


def test_ambiguous_filename_is_rejected() -> None:
    with pytest.raises(IngestError, match="more than one product code"):
        identify_sensor("DL_FIRE_M-C61_SV-C2.zip")


def test_unknown_filename_is_rejected() -> None:
    with pytest.raises(IngestError, match="known FIRMS product code"):
        identify_sensor("fires.zip")


def test_duplicate_archives_are_not_extracted(tmp_path: Path) -> None:
    incoming = tmp_path / "incoming"
    destination = tmp_path / "destination"
    incoming.mkdir()
    write_zip(incoming / "DL_FIRE_M-C61_1.zip", {"a.csv": july_csv("Terra")})
    write_zip(incoming / "DL_FIRE_M-C61_2.zip", {"b.csv": july_csv("Aqua")})
    manifest = build_manifest(incoming, destination, dry_run=False)
    assert manifest["passed"] is False
    assert "modis" in manifest["missing_sensors"]
    assert len(manifest["rejected_archives"]) == 2
    assert list(destination.rglob("*.csv")) == []


def test_missing_archive_is_reported(tmp_path: Path) -> None:
    incoming = tmp_path / "incoming"
    destination = tmp_path / "destination"
    incoming.mkdir()
    write_zip(incoming / "DL_FIRE_M-C61_1.zip", {"a.csv": july_csv("Terra")})
    manifest = build_manifest(incoming, destination, dry_run=True)
    assert manifest["missing_sensors"] == ["viirs_snpp", "viirs_noaa20", "viirs_noaa21"]
    assert list(destination.rglob("*.csv")) == []


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    incoming = tmp_path / "incoming"
    destination = tmp_path / "destination"
    incoming.mkdir()
    outside = tmp_path / "outside.csv"
    write_zip(
        incoming / "DL_FIRE_M-C61_1.zip",
        {"../outside.csv": "escaped", "fire.csv": july_csv("Terra")},
    )
    manifest = build_manifest(incoming, destination, dry_run=False)
    modis = next(item for item in manifest["sensors"] if item["sensor"] == "modis")
    assert modis["validation_status"] == "failed"
    assert "escapes" in modis["issues"][0]
    assert not outside.exists()
    assert list(destination.rglob("*.csv")) == []


def test_existing_extract_is_not_overwritten(tmp_path: Path) -> None:
    incoming = tmp_path / "incoming"
    destination = tmp_path / "destination"
    incoming.mkdir()
    place_four(incoming)
    kept = destination / "modis" / "fire_archive_M-C61_1.csv"
    kept.parent.mkdir(parents=True)
    kept.write_text("original", encoding="utf-8")
    manifest = build_manifest(incoming, destination, dry_run=False)
    modis = next(item for item in manifest["sensors"] if item["sensor"] == "modis")
    assert modis["validation_status"] == "failed"
    assert kept.read_text(encoding="utf-8") == "original"
    assert manifest["passed"] is False


def test_dry_run_does_not_extract_or_write_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    incoming = tmp_path / "incoming"
    destination = tmp_path / "destination"
    incoming.mkdir()
    place_four(incoming)
    assert main(["--incoming", str(incoming), "--destination", str(destination), "--manifest", str(tmp_path / "out.json"), "--dry-run"]) == 0
    assert list(destination.rglob("*.csv")) == []
    assert not (tmp_path / "out.json").exists()
    assert "dry-run: passed=True" in capsys.readouterr().out


def test_manifest_records_checksums_and_absent_dates(tmp_path: Path) -> None:
    incoming = tmp_path / "incoming"
    destination = tmp_path / "destination"
    manifest_path = tmp_path / "manifest.json"
    incoming.mkdir()
    present = [day for day in period_dates() if day != "2024-07-03"]
    place_four(incoming, snpp_dates=present)
    assert main(["--incoming", str(incoming), "--destination", str(destination), "--manifest", str(manifest_path)]) == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snpp = next(item for item in manifest["sensors"] if item["sensor"] == "viirs_snpp")
    assert snpp["validation_status"] == "passed"
    assert snpp["record_count"] == 30
    assert snpp["dates_absent"] == ["2024-07-03"]
    assert "2024-07-03" not in snpp["dates_present"]
    assert snpp["zip_sha256"]
    assert snpp["csv_sha256"]
    assert snpp["zip_bytes"] > 0
    assert snpp["csv_bytes"] > 0
    assert snpp["processing_stream"] is None
    assert "not a count of zero" in snpp["absent_date_policy"]
    extracted = destination / "viirs_snpp" / "fire_nrt_SV-C2_2.csv"
    assert extracted.is_file()
    assert manifest["harmonization_coefficients_calculated"] is False


def test_column_mismatch_fails(tmp_path: Path) -> None:
    incoming = tmp_path / "incoming"
    destination = tmp_path / "destination"
    incoming.mkdir()
    write_zip(incoming / "DL_FIRE_M-C61_1.zip", {"a.csv": "latitude,longitude\n1,2\n"})
    manifest = build_manifest(incoming, destination, dry_run=False)
    modis = next(item for item in manifest["sensors"] if item["sensor"] == "modis")
    assert modis["validation_status"] == "failed"
    assert "15-column" in modis["issues"][0]


def test_destination_cannot_be_the_july7_sample() -> None:
    incoming = RAW_DIR.parent / "incoming" / "2024-07"
    with pytest.raises(IngestError, match="July 7 sample"):
        build_manifest(incoming, RAW_DIR / "modis", dry_run=True)
