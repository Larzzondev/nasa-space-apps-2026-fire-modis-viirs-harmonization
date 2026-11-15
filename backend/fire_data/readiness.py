"""Data-readiness review of the local FIRMS extracts and the proximity matcher.

The review records what can be verified from the files and from documents
retrieved for this pass. It does not assign a processing stream from a
filename or a version value, does not treat proximity pairs as fires, and
does not calculate a calibration coefficient.
"""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path

import numpy as np

from fire_data.contract import COLUMNS, SOURCES, SourceContract
from fire_data.eda_spatial import EARTH_RADIUS_M, lonlat_to_ecef
from fire_data.readers import read_archive
from fire_data.temporal import (
    DEFAULT_RADII_M,
    DEFAULT_WINDOWS_MIN,
    REPORTS_DIR,
    SATELLITE_ORDER,
    assert_output_allowed,
    scan_archives,
)

RETRIEVED = "2026-11-14"
QUANTILES = (0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)
VARIABLE_CLASSES = (
    "candidate_measurement",
    "observation_geometry",
    "quality_indicator",
    "matching_key",
    "stratification_variable",
    "excluded_until_further_evidence",
)

DOCUMENT_STATEMENTS: tuple[dict[str, str], ...] = (
    {
        "source_id": "firms_download_readme",
        "url": "https://firms.modaps.eosdis.nasa.gov/download/Readme.txt",
        "retrieved": RETRIEVED,
        "text": (
            "The FIRMS download readme defines fire_nrt_M-C61 as MCD14DL and fire_archive_M-C61 as "
            "standard-quality MCD14ML. It defines fire_nrt_SV-C2 as VNP14IMGTDL and fire_archive_SV-C2 as "
            "standard-quality VNP14IMGTML. It defines fire_nrt_J1V-C2 as VJ114IMGDL and fire_nrt_J2V-C2 as "
            "VJ214IMGDL. It does not define a standard-product filename or short name for NOAA-20 or NOAA-21. "
            "It states that standard quality data is not yet available from FIRMS for NOAA-20 and NOAA-21. "
            "The characters after the product code are described as the download request id. "
            "Supplied coordinates are described as WGS84. The Collection / Version field is described as the "
            "way to distinguish MODIS from VIIRS, not as an NRT-versus-standard flag."
        ),
    },
    {
        "source_id": "firms_api_availability",
        "url": "https://firms.modaps.eosdis.nasa.gov/api/data_availability/",
        "retrieved": RETRIEVED,
        "text": (
            "The FIRMS API data-availability page lists MODIS_NRT, MODIS_SP, VIIRS_SNPP_NRT, VIIRS_SNPP_SP, "
            "VIIRS_NOAA20_NRT, VIIRS_NOAA20_SP, VIIRS_NOAA21_NRT, and VIIRS_NOAA21_SP. "
            "These are catalog sensor codes. They are not columns in the local CSV files."
        ),
    },
    {
        "source_id": "firms_viirs_attributes",
        "url": "https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html",
        "retrieved": RETRIEVED,
        "text": (
            "The FIRMS VIIRS attribute page says the version value identifies the collection and, by suffix, "
            "the processing source: URT, RT, and NRT suffixes are those streams, and a collection value with "
            "no suffix is the page's example of standard processing (examples include 2.0URT, 2.0RT, 1.0NRT, and 1.0). "
            "It names Bright_ti4 / Brightness as I-4 and Bright_ti5 / Brightness_2 as I-5. "
            "It says high-confidence pixels are associated with day or nighttime saturated pixels. "
            "It says the satellite code for Suomi NPP is N. "
            "It says the inferred hot-spot type attribute is only available for VNP14IMGT standard-quality data. "
            "It describes NOAA-21 as about 50 minutes ahead of NOAA-20, with S-NPP between them."
        ),
    },
    {
        "source_id": "laads_vj114img",
        "url": "https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ114IMG",
        "retrieved": RETRIEVED,
        "text": (
            "The LAADS page for VJ114IMG titles it VIIRS/JPSS1 Active Fires 6-Min L2 Swath 375m, "
            "platform JPSS1 (NOAA-20), instrument VIIRS, processing level Level-2, collection "
            "NPP and JPSS1 VIIRS data 2.0. The page describes a swath product. It does not say that a "
            "FIRMS CSV named fire_archive_J1V-C2 is that swath file."
        ),
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _field(
    source_id: str,
    field: str,
    *,
    status: str,
    value: object,
    evidence: str,
) -> dict[str, object]:
    if status not in {"verified", "unverified", "missing"}:
        raise ValueError(f"Unknown provenance status: {status}")
    return {
        "source_id": source_id,
        "field": field,
        "status": status,
        "value": value,
        "evidence": evidence,
    }


def provenance_rows(archive: dict[str, object]) -> list[dict[str, object]]:
    """Build one archive's provenance matrix without using filename or version as a stream.

    ``archive`` must already contain measurements from the file. The filename and
    the version counts are stored as verified strings. They are not converted
    into a processing level.
    """

    source_id = str(archive["source_id"])
    columns = list(archive["columns"])
    level_names = {"processing_level", "product_level", "processing_stream", "product_short_name"}
    has_level = any(str(column).strip().lower() in level_names for column in columns)
    has_saturation = any("saturat" in str(column).lower() or str(column).lower() in {"qa", "quality"} for column in columns)
    rows = [
        _field(source_id, "sha256", status="verified", value=archive.get("sha256"), evidence="SHA-256 of the local file bytes."),
        _field(source_id, "byte_size", status="verified", value=archive.get("byte_size"), evidence="Size in bytes of the local file."),
        _field(
            source_id,
            "filename",
            status="verified",
            value=archive.get("filename"),
            evidence="The filename is recorded as text. It is not interpreted as a processing stream.",
        ),
        _field(source_id, "columns", status="verified", value=columns, evidence="Header row of the CSV."),
        _field(source_id, "row_count", status="verified", value=archive.get("row_count"), evidence="Data rows read from the CSV."),
        _field(source_id, "acquisition_dates", status="verified", value=archive.get("dates"), evidence="Distinct acq_date values and their row counts."),
        _field(source_id, "satellite_values", status="verified", value=archive.get("satellites"), evidence="Distinct satellite values stored in the file."),
        _field(source_id, "instrument_values", status="verified", value=archive.get("instruments"), evidence="Distinct instrument values stored in the file."),
        _field(
            source_id,
            "version_values",
            status="verified",
            value=archive.get("versions"),
            evidence="Distinct version strings stored in the file. The strings are not mapped to a processing stream.",
        ),
        _field(
            source_id,
            "processing_level_column_present",
            status="verified",
            value=has_level,
            evidence="Searched the header for processing_level, product_level, processing_stream, and product_short_name.",
        ),
        _field(
            source_id,
            "saturation_or_quality_flag_present",
            status="verified",
            value=has_saturation,
            evidence="Searched the header for a saturation, QA, or quality column.",
        ),
        _field(
            source_id,
            "product_short_name",
            status="missing",
            value=None,
            evidence=(
                "The CSV has no product-short-name field. The download readme and the API catalog name "
                "several candidate products. Choosing one would require the filename prefix or an assumption "
                "about the version string, and this review does not do that."
            ),
        ),
        _field(
            source_id,
            "processing_stream",
            status="missing",
            value=None,
            evidence=(
                "No processing-stream attribute is stored. Filename prefixes and version values were not used "
                "to assign NRT, RT, URT, or standard processing."
            ),
        ),
        _field(
            source_id,
            "provider_checksum",
            status="missing",
            value=None,
            evidence="No provider checksum or original zip readme is stored beside the CSV.",
        ),
        _field(
            source_id,
            "area_of_interest",
            status="missing",
            value=None,
            evidence="The CSV does not record the requested geographic scope.",
        ),
        _field(
            source_id,
            "production_timestamp",
            status="missing",
            value=None,
            evidence="The CSV does not record when the product was generated.",
        ),
        _field(
            source_id,
            "projection_stated_in_file",
            status="missing",
            value=None,
            evidence="The CSV does not state a projection. The download readme describes FIRMS coordinates as WGS84 in general.",
        ),
        _field(
            source_id,
            "readme_filename_mapping",
            status="unverified",
            value=None,
            evidence=(
                "The download readme maps fire_nrt and fire_archive names to product short names. "
                "Applying that map to this file would use the filename as evidence of processing level."
            ),
        ),
        _field(
            source_id,
            "api_sensor_code",
            status="unverified",
            value=None,
            evidence="The API catalog lists NRT and SP sensor codes. None of those codes is a value in this CSV.",
        ),
        _field(
            source_id,
            "version_suffix_rule",
            status="unverified",
            value=None,
            evidence=(
                "The FIRMS VIIRS attribute page says a version without a URT, RT, or NRT suffix denotes standard "
                "processing in its examples. The stored VIIRS value is 2 and the stored MODIS value is 61.03. "
                "Those strings are not the page's examples, and this review does not apply the suffix rule."
            ),
        ),
    ]
    return rows


def count_duplicates(
    sources: tuple[SourceContract, ...] = SOURCES,
    paths: dict[str, Path] | None = None,
) -> dict[str, object]:
    """Count repeated CSV lines and repeated satellite/location/time keys.

    Repeats are retained. They are separate stored rows in the matcher.
    """

    index = {name: position for position, name in enumerate(COLUMNS)}
    exact_seen: set[tuple[str, str]] = set()
    key_seen: set[tuple[str, str, str, str, str]] = set()
    exact_duplicates = 0
    key_duplicates = 0
    rows = 0
    per_source: list[dict[str, object]] = []
    for source in sources:
        path = paths[source.source_id] if paths and source.source_id in paths else source.path
        source_exact = 0
        source_key = 0
        source_rows = 0
        with read_archive(path) as (header, data_rows):
            if tuple(header) != COLUMNS:
                raise ValueError(f"{path.name} header does not match the observed 15-column contract")
            for _line_number, row in data_rows:
                if len(row) != len(COLUMNS):
                    continue
                source_rows += 1
                rows += 1
                exact_key = (source.source_id, tuple(row))
                if exact_key in exact_seen:
                    exact_duplicates += 1
                    source_exact += 1
                else:
                    exact_seen.add(exact_key)
                location_key = (
                    row[index["satellite"]],
                    row[index["latitude"]],
                    row[index["longitude"]],
                    row[index["acq_date"]],
                    row[index["acq_time"]],
                )
                if location_key in key_seen:
                    key_duplicates += 1
                    source_key += 1
                else:
                    key_seen.add(location_key)
        per_source.append(
            {
                "source_id": source.source_id,
                "row_count": source_rows,
                "exact_duplicate_rows": source_exact,
                "location_time_duplicate_rows": source_key,
            }
        )
    return {
        "row_count": rows,
        "exact_duplicate_rows": exact_duplicates,
        "location_time_duplicate_rows": key_duplicates,
        "duplicates_removed_before_matching": 0,
        "sources": per_source,
        "handling": (
            "An exact duplicate is a repeated data line within the local archives. "
            "A location-time duplicate is another row with the same satellite, latitude text, "
            "longitude text, acq_date, and acq_time. Both kinds stay in the matcher as separate detections. "
            "Duplicate pairs across satellites are not collapsed, and the reverse of a pair is not stored."
        ),
    }


def _distribution(values: np.ndarray) -> dict[str, object]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {
            "count": 0,
            "minimum": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None,
            "p99": None,
            "maximum": None,
        }
    quantiles = np.quantile(finite, QUANTILES, method="linear")
    keys = ("minimum", "p25", "p50", "p75", "p90", "p99", "maximum")
    return {"count": int(finite.size), **{key: float(quantiles[index]) for index, key in enumerate(keys)}}


def matching_audit(
    satellite: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    epoch_min: np.ndarray,
    radii_m: tuple[float, ...] = DEFAULT_RADII_M,
    windows_min: tuple[int, ...] = DEFAULT_WINDOWS_MIN,
) -> list[dict[str, object]]:
    """Audit unordered cross-satellite proximity with the same sphere as the temporal pass.

    Each physical pair of detections is stored once. Nearest-neighbor summaries are
    still directional, because A's nearest B detection need not be B's nearest A.
    ``same_fire`` stays ``not_assessed``. Pair counts are not fire counts.
    """

    from scipy.spatial import cKDTree

    names = [name for name in SATELLITE_ORDER if satellite.size and np.any(satellite == name)]
    names.extend(sorted(set(satellite.tolist()) - set(names)))
    grouped = {}
    for name in names:
        chosen = satellite == name
        grouped[name] = {
            "latitude": latitude[chosen],
            "longitude": longitude[chosen],
            "epoch_min": epoch_min[chosen],
        }
    ecef = {
        name: lonlat_to_ecef(values["latitude"], values["longitude"])
        for name, values in grouped.items()
        if values["latitude"].size
    }
    radii = tuple(sorted(float(radius) for radius in radii_m))
    windows = tuple(sorted(int(window) for window in windows_min))
    max_radius = radii[-1] if radii else 0.0
    max_window = windows[-1] if windows else 0
    from itertools import combinations

    rows: list[dict[str, object]] = []
    for name_a, name_b in combinations(names, 2):
        points_a = ecef.get(name_a)
        points_b = ecef.get(name_b)
        epoch_a = grouped[name_a]["epoch_min"]
        epoch_b = grouped[name_b]["epoch_min"]
        count_a = int(epoch_a.size)
        count_b = int(epoch_b.size)
        nn_distance_a = {window: np.full(count_a, np.inf) for window in windows}
        nn_delta_a = {window: np.full(count_a, np.nan) for window in windows}
        nn_distance_b = {window: np.full(count_b, np.inf) for window in windows}
        nn_delta_b = {window: np.full(count_b, np.nan) for window in windows}
        distance_chunks: list[np.ndarray] = []
        delta_chunks: list[np.ndarray] = []
        if (
            points_a is not None
            and points_b is not None
            and count_a
            and count_b
            and max_radius > 0
        ):
            neighbors = cKDTree(points_b).query_ball_point(points_a, r=max_radius, workers=1)
            for index_a, indices in enumerate(neighbors):
                if not indices:
                    continue
                idx = np.asarray(indices, dtype=np.int64)
                diff = points_b[idx] - points_a[index_a]
                distance = np.sqrt(np.einsum("ij,ij->i", diff, diff))
                delta = np.abs(epoch_b[idx] - np.int64(epoch_a[index_a])).astype(np.float64)
                keep = (distance <= max_radius) & (delta <= max_window)
                if np.any(keep):
                    distance_chunks.append(distance[keep])
                    delta_chunks.append(delta[keep])
                for window in windows:
                    eligible = np.flatnonzero(delta <= window)
                    if eligible.size == 0:
                        continue
                    order = eligible[np.lexsort((delta[eligible], distance[eligible]))]
                    best = int(order[0])
                    if distance[best] < nn_distance_a[window][index_a]:
                        nn_distance_a[window][index_a] = distance[best]
                        nn_delta_a[window][index_a] = delta[best]
                    better = distance[eligible] < nn_distance_b[window][idx[eligible]]
                    chosen = eligible[better]
                    nn_distance_b[window][idx[chosen]] = distance[chosen]
                    nn_delta_b[window][idx[chosen]] = delta[chosen]
                    tied = (~better) & (distance[eligible] == nn_distance_b[window][idx[eligible]]) & (
                        delta[eligible] < nn_delta_b[window][idx[eligible]]
                    )
                    tied_idx = eligible[tied]
                    nn_delta_b[window][idx[tied_idx]] = delta[tied_idx]
        pair_distance = np.concatenate(distance_chunks) if distance_chunks else np.empty(0, dtype=np.float64)
        pair_delta = np.concatenate(delta_chunks) if delta_chunks else np.empty(0, dtype=np.float64)
        for radius in radii:
            for window in windows:
                selected = (pair_distance <= radius) & (pair_delta <= window) if pair_distance.size else np.empty(0, dtype=bool)
                source_nn = nn_distance_a[window]
                target_nn = nn_distance_b[window]
                source_hit = source_nn <= radius
                target_hit = target_nn <= radius
                source_with = int(source_hit.sum())
                target_with = int(target_hit.sum())
                rows.append(
                    {
                        "satellite_a": name_a,
                        "satellite_b": name_b,
                        "radius_m": radius,
                        "max_delta_minutes": window,
                        "raw_pair_count": int(selected.sum()) if selected.size else 0,
                        "unique_source_detections": source_with,
                        "unique_target_detections": target_with,
                        "detections_with_at_least_one_neighbor": source_with + target_with,
                        "source_detections": count_a,
                        "target_detections": count_b,
                        "pair_distance_m": _distribution(pair_distance[selected] if selected.size else pair_distance),
                        "abs_delta_minutes": _distribution(pair_delta[selected] if selected.size else pair_delta),
                        "nearest_neighbor_source_to_target_m": _distribution(source_nn[source_hit]),
                        "nearest_neighbor_target_to_source_m": _distribution(target_nn[target_hit]),
                        "nearest_neighbor_source_to_target_minutes": _distribution(nn_delta_a[window][source_hit]),
                        "nearest_neighbor_target_to_source_minutes": _distribution(nn_delta_b[window][target_hit]),
                        "source_without_neighbor": count_a - source_with,
                        "target_without_neighbor": count_b - target_with,
                        "reverse_pairs_stored": 0,
                        "pair_orientation": "unordered_satellite_pair",
                        "same_fire": "not_assessed",
                        "interpreted_as_unique_fires": False,
                    }
                )
    return rows


def classify_variables() -> list[dict[str, str]]:
    """Classify stored fields for a later calibration. No coefficient is attached."""

    return [
        {
            "variable": "frp",
            "classification": "candidate_measurement",
            "rationale": (
                "FRP is stored in MW on every satellite in this extract. It is the measurement a later "
                "calibration would compare. The retrieval is sensor-specific, the processing stream is "
                "unresolved, and only one date is present, so no coefficient is calculated."
            ),
        },
        {
            "variable": "scan",
            "classification": "observation_geometry",
            "rationale": "Scan is the stored along-scan pixel size in km. It describes the observation, not the fire intensity.",
        },
        {
            "variable": "track",
            "classification": "observation_geometry",
            "rationale": "Track is the stored along-track pixel size in km. It describes the observation, not the fire intensity.",
        },
        {
            "variable": "daynight",
            "classification": "stratification_variable",
            "rationale": (
                "Daynight is the stored D or N flag. It can separate strata. The file does not record whether "
                "the flag came from solar zenith angle or from orbit direction, so the flag is used only as stored."
            ),
        },
        {
            "variable": "brightness",
            "classification": "excluded_until_further_evidence",
            "rationale": (
                "VIIRS files store an exact brightness of 367 K with no Level-1 saturation flag, so those rows "
                "cannot be marked confirmed saturated. MODIS brightness is a different stored temperature and "
                "reaches above 367 K. The two columns are not one measurement."
            ),
        },
        {
            "variable": "confidence",
            "classification": "excluded_until_further_evidence",
            "rationale": (
                "MODIS confidence is an integer from 0 through 100. VIIRS confidence is l, n, or h. "
                "The FIRMS VIIRS page describes h as associated with saturated pixels; these CSVs do not "
                "carry the saturation bit that would confirm that association row by row. The scales are not a "
                "shared quality weight."
            ),
        },
        {
            "variable": "satellite",
            "classification": "stratification_variable",
            "rationale": "Satellite identity defines the sensor stratum. Detections from different satellites are not added as independent fires.",
        },
        {
            "variable": "acquisition_time",
            "classification": "matching_key",
            "rationale": (
                "acq_date and acq_time locate the observation in UTC. They are keys for a proximity window. "
                "The clock time alone is not a fire attribute to rescale."
            ),
        },
        {
            "variable": "latitude_longitude",
            "classification": "matching_key",
            "rationale": (
                "Latitude and longitude are the stored pixel-center coordinates used to compute distance. "
                "They are match keys. The file does not state a projection; the download readme describes FIRMS "
                "coordinates as WGS84 in general."
            ),
        },
    ]


def acquisition_specification(dates_present: list[str]) -> dict[str, object]:
    """Specification for a future 30-date bundle. It does not list fabricated observations."""

    return {
        "target_date_count": 30,
        "dates_acquired_for_this_spec": [],
        "dates_present_in_current_archives": list(dates_present),
        "fabricated_dates": False,
        "purpose": (
            "Obtain 30 acquisition dates with comparable FIRMS active-fire tables for Terra, Aqua, "
            "S-NPP, NOAA-20, and NOAA-21. This specification describes the request. It does not create those files."
        ),
        "date_selection": {
            "rule": (
                "After one processing stream is named in a provider metadata field, choose 30 distinct UTC dates "
                "with a rule written into the manifest before download. The rule must spread dates across months "
                "rather than take 30 consecutive days, and it must be reproducible from a recorded seed or calendar formula. "
                "The specific 30 dates are chosen at acquisition time. They are not invented here."
            ),
            "completeness": (
                "A date enters the analysis set only when all five satellites have a file for that date from the "
                "same processing stream and the same recorded area of interest. A satellite with no detections "
                "is represented by a header-only CSV, not by an omitted file and not by imputed rows."
            ),
            "current_holdings": (
                "The current archives contain one acquisition date, 2024-07-07, and no processing-stream field. "
                "They do not satisfy the 30-date specification."
            ),
        },
        "product_identifiers": {
            "status": "required_in_the_provider_manifest",
            "assigned_to_current_files": False,
            "download_readme": {
                "MODIS_NRT": "MCD14DL",
                "MODIS_standard": "MCD14ML",
                "SNPP_NRT": "VNP14IMGTDL",
                "SNPP_standard": "VNP14IMGTML",
                "NOAA20_NRT": "VJ114IMGDL",
                "NOAA21_NRT": "VJ214IMGDL",
                "NOAA20_standard_in_download_readme": None,
                "NOAA21_standard_in_download_readme": None,
            },
            "api_sensor_codes": [
                "MODIS_NRT",
                "MODIS_SP",
                "VIIRS_SNPP_NRT",
                "VIIRS_SNPP_SP",
                "VIIRS_NOAA20_NRT",
                "VIIRS_NOAA20_SP",
                "VIIRS_NOAA21_NRT",
                "VIIRS_NOAA21_SP",
            ],
            "note": (
                "The download readme and the API catalog disagree on whether NOAA-20 and NOAA-21 standard "
                "products are available. The manifest for the 30-date bundle must name the short name and the "
                "stream in a metadata field. A filename prefix is not sufficient."
            ),
        },
        "processing_level_requirements": [
            "Every file carries an explicit processing-stream value in a metadata field supplied with the download.",
            "The 30 dates use one stream. NRT and standard files are not mixed.",
            "NOAA-20 and NOAA-21 are included only when that metadata field is present, because the download readme and the API catalog currently disagree.",
            "A version string of 2 or 61.03, and a filename beginning with fire_archive or fire_nrt, are stored and are not accepted as the stream.",
            "Level-2 swath granules such as the LAADS VJ114IMG product are a different file type. They are not substituted for the FIRMS table unless the manifest says so.",
        ],
        "required_metadata": [
            "product short name",
            "processing stream",
            "collection or version, stored separately from the processing stream",
            "satellite and instrument",
            "area of interest and date range requested",
            "projection",
            "production time",
            "variable definitions for brightness, the second thermal column, confidence, and type",
            "provider checksum",
            "source URL and retrieval time",
        ],
        "missing_data_handling": [
            "A failed download is recorded as a failure. It is not written as an empty scene.",
            "A successful request with no detections is a header-only CSV and is retained.",
            "A date missing any of the five satellites is excluded from the 30-date set.",
            "Detections, brightness values, and FRP values are not imputed.",
            "The existing 2024-07-07 files are not copied forward to fill the other 29 dates.",
        ],
        "file_naming_and_checksums": {
            "preserve_provider_filename": True,
            "do_not_rename_between_nrt_and_archive": True,
            "layout": "data/raw/<source_id>/<provider_filename>",
            "manifest": "data/manifest/firms_30day_manifest.csv",
            "manifest_columns": [
                "provider_filename",
                "sha256",
                "bytes",
                "product_short_name",
                "processing_stream",
                "satellite",
                "area_of_interest",
                "date_start",
                "date_end",
                "source_url",
                "retrieved_utc",
            ],
            "checksum_algorithm": "SHA-256",
            "checksum_rule": (
                "Compute SHA-256 on the downloaded bytes before any rewrite. Store lowercase hexadecimal. "
                "Recompute the digest before analysis and stop if it differs from the manifest."
            ),
        },
    }


def _attach_file_facts(
    sources: tuple[SourceContract, ...],
    paths: dict[str, Path] | None,
    archives: list[dict],
) -> list[dict]:
    by_id = {source.source_id: source for source in sources}
    enriched = []
    for archive in archives:
        source = by_id[str(archive["source_id"])]
        path = paths[source.source_id] if paths and source.source_id in paths else source.path
        enriched.append({**archive, "sha256": sha256_file(path), "byte_size": path.stat().st_size})
    return enriched


def build_readiness(
    sources: tuple[SourceContract, ...] = SOURCES,
    paths: dict[str, Path] | None = None,
    radii_m: tuple[float, ...] = DEFAULT_RADII_M,
    windows_min: tuple[int, ...] = DEFAULT_WINDOWS_MIN,
) -> dict[str, object]:
    scanned = scan_archives(sources, paths)
    archives = _attach_file_facts(sources, paths, list(scanned["archives"]))
    points = scanned["points"]
    matrix = [row for archive in archives for row in provenance_rows(archive)]
    streams = [row for row in matrix if row["field"] == "processing_stream"]
    return {
        "scope": {
            "label": "data-readiness and matching-methodology review",
            "temporal_validation": "not_performed",
            "dates_present": list(scanned["dates"]),
            "radii_m": list(radii_m),
            "windows_min": list(windows_min),
            "earth_radius_m": EARTH_RADIUS_M,
            "calibration_coefficients_calculated": False,
        },
        "discrepancy": {
            "subject": "NOAA-20 and NOAA-21 standard processing in FIRMS",
            "download_readme": (
                "Standard quality data is not yet available from FIRMS for NOAA-20 and NOAA-21. "
                "The readme names only the NRT short names VJ114IMGDL and VJ214IMGDL for those satellites."
            ),
            "api_catalog": "The API availability page lists VIIRS_NOAA20_SP and VIIRS_NOAA21_SP.",
            "local_files": "The local CSVs contain neither the readme short names nor the API sensor codes.",
            "resolution": "unresolved",
            "effect_on_current_archives": (
                "The disagreement is between two FIRMS pages. It does not identify the processing stream of the local files."
            ),
        },
        "archives": archives,
        "provenance_matrix": matrix,
        "processing_stream_status": {
            row["source_id"]: {"status": row["status"], "value": row["value"]} for row in streams
        },
        "document_statements": list(DOCUMENT_STATEMENTS),
        "duplicates": count_duplicates(sources, paths),
        "matching": matching_audit(
            points["satellite"],
            points["latitude"],
            points["longitude"],
            points["epoch_min"],
            radii_m,
            windows_min,
        ),
        "matching_method": {
            "implementation_reviewed": "fire_data.temporal.proximity_counts",
            "distance": (
                f"ECEF chord on a sphere of radius {EARTH_RADIUS_M} m, the same definition as the temporal proximity count."
            ),
            "time": "Absolute difference of UTC minutes, with the calendar date included in the minute count.",
            "satellite_pairs": "Each unordered pair of satellites is visited once. A self-pair is omitted.",
            "detection_pairs": (
                "Each pair of detections inside the radius and the time window is counted once. "
                "The reverse ordered pair is not stored. A detection may join many pairs."
            ),
            "nearest_neighbor_tie": "The smallest distance is kept. If distances tie, the smaller absolute time difference is kept.",
            "duplicates": "Repeated CSV rows are counted and retained. They are not collapsed before matching.",
            "same_fire": "not_assessed",
            "unique_fires": "Pair counts and detection counts are not converted into a unique-fire total.",
        },
        "variables": classify_variables(),
        "acquisition_specification": acquisition_specification(list(scanned["dates"])),
    }


def main(argv: list[str] | None = None) -> int:
    from fire_data.readiness_report import write_readiness

    parser = argparse.ArgumentParser(description="Review provenance, matching, and data readiness.")
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args(argv)
    summary = build_readiness()
    written = write_readiness(summary, args.output_dir)
    missing = Counter(row["status"] for row in summary["provenance_matrix"])
    print(
        "processing_stream=missing "
        f"provenance_verified={missing['verified']} "
        f"provenance_unverified={missing['unverified']} "
        f"provenance_missing={missing['missing']} "
        f"matching_rows={len(summary['matching'])}"
    )
    print(f"Wrote {written[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
