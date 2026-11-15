"""Guards for the milestone 12 historical-data documents.

The tests read the strategy files. They do not download NASA archives, do not
open the July CSVs, and do not fit a coefficient.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
DOCS = {
    "strategy": RESEARCH / "HISTORICAL_DATA_STRATEGY.md",
    "matrix": RESEARCH / "PRODUCT_PROVENANCE_MATRIX.md",
    "timeline": RESEARCH / "TEMPORAL_OVERLAP_TIMELINE.md",
    "acquisition": RESEARCH / "ACQUISITION_PLAN.md",
    "sampling": RESEARCH / "VALIDATION_SAMPLING_STRATEGY.md",
}


def _text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in DOCS.values())


def test_strategy_documents_exist():
    missing = [str(path) for path in DOCS.values() if not path.is_file()]
    assert missing == []


def test_documents_cite_the_retrieval_day_and_leave_same_fire_open():
    body = _text()
    assert "2026-11-15" in body
    assert "not_assessed" in body
    assert "unresolved" in body


def test_noaa_products_stay_distinct_and_the_firms_disagreement_is_quoted():
    body = _text()
    for token in ("MOD14", "MYD14", "VNP14IMG", "VJ114IMG", "VJ214IMG"):
        assert token in body
    assert "not yet available" in body
    assert "VIIRS_NOAA20_SP" in body
    assert "VIIRS_NOAA21_SP" in body
    assert "VJ114IMG" in body and "VJ214IMG" in body


def test_july_2024_is_locked_out_of_the_three_splits():
    sampling = DOCS["sampling"].read_text(encoding="utf-8")
    assert "2024-07" not in sampling.split("### Calibration period")[1].split("### Training")[0]
    assert "July 2024 is not in the training period" in sampling
    assert "2025-01-15" in sampling
    assert "2026-09-15" in sampling
    assert "2024-02-15" in sampling


def test_no_coefficient_and_no_embedded_map_key():
    body = _text()
    assert "No coefficient is calculated" in body or "No harmonization coefficient is calculated" in body
    assert "MAP_KEY=" not in body
    assert "xgboost" not in body.lower() or "not trained" in body.lower() or "is not trained" in body.lower()
