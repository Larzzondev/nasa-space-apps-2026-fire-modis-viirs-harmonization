"""Evidence record for the July 2024 S-NPP coverage investigation.

The counts and timestamps below were read from the local CSV and from public
NASA responses during this investigation. They are not inferred fire counts.
"""

from __future__ import annotations

import json
from pathlib import Path

from fire_data.contract import BACKEND_ROOT
from fire_data.coverage_verify import (
    classify_firms_csv,
    classify_l2_swath,
    parse_utc,
    stated_l2_alert,
)

RETRIEVED = "2026-11-15T04:20:00Z"
REPORTS = BACKEND_ROOT / "reports"

GEOLOCATION_ALERT = {
    "title": "Suomi NPP VIIRS Data Product Geolocation Anomaly - July 2024",
    "url": "https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-viirs-data-product-geolocation-anomaly-july-2024",
    "publisher": "LP DAAC, NASA Earthdata",
    "retrieved_at": RETRIEVED,
    "issued": "2024-07-09",
    "resolved_header": "2024-07-16",
    "published": "2024-07-19",
    "last_updated": "2026-02-03",
    "statement": (
        "Data gaps will exist from 21:42:00 UTC on July 9, 2024, through 17:42:00 UTC on July 16, 2024, "
        "due to unrecoverable geolocation errors and invalid timestamps. Normal production resumed starting "
        "with July 16, 2024, after GPS recovery at 17:42:00 UTC. The anomaly start in the earlier notice is "
        "21:46:00 UTC on July 9, 2024. The referenced datasets include VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002."
    ),
}
JULY24_ALERT = {
    "title": "Suomi NPP VIIRS Data Product Anomaly - July 2024",
    "url": "https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-viirs-data-product-anomaly-july-2024",
    "publisher": "LP DAAC, NASA Earthdata",
    "retrieved_at": RETRIEVED,
    "issued": "2024-07-24",
    "resolved_header": "2024-08-05",
    "published": "2024-07-25",
    "last_updated": "2026-02-03",
    "statement": (
        "The mission experienced an outage from 05:28:00 UTC to 18:22:00 UTC on July 24, 2024. "
        "All VIIRS processing was on hold, and data for the outage period were described as not recoverable "
        "until further notice. The retrieved page body does not add a later recovery narrative. "
        "The referenced datasets include VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002. "
        "The page does not name July 25–29."
    ),
}
FIRMS_README = {
    "url": "https://firms.modaps.eosdis.nasa.gov/download/Readme.txt",
    "retrieved_at": RETRIEVED,
    "statement": (
        "DL_FIRE_M-C61 is MODIS Collection 6.1. fire_archive_M-C61 is described as standard-quality MCD14ML. "
        "fire_archive_SV-C2 is described as standard-quality VNP14IMGTML. fire_nrt_J1V-C2 is VJ114IMGDL and "
        "fire_nrt_J2V-C2 is VJ214IMGDL. The readme says standard-quality data are not yet available from FIRMS "
        "for NOAA-20 and NOAA-21. It does not define fire_archive_J1V-C2 or fire_archive_J2V-C2. "
        "A version field is described as distinguishing MODIS from VIIRS, not as an NRT-versus-standard flag. "
        "A request with no fire points is delivered as a header-only CSV."
    ),
}

INTERVALS = (
    {
        "date": "2024-07-10",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 79,
        "cmr_first": "2024-07-09T23:54:00Z",
        "cmr_last": "2024-07-10T07:42:00Z",
        "alert_says_unavailable": True,
        "alert_id": "geolocation",
        "confidence": "high",
        "note": (
            "The date falls inside the LP DAAC geolocation gap. CMR still lists 79 VNP14IMG granules, "
            "ending at 07:42 UTC. Those files were not opened. The local FIRMS CSV has no row for the date. "
            "The granule count is not a fire count."
        ),
    },
    {
        "date": "2024-07-11",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": True,
        "alert_id": "geolocation",
        "confidence": "high",
        "note": "No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.",
    },
    {
        "date": "2024-07-12",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": True,
        "alert_id": "geolocation",
        "confidence": "high",
        "note": "No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.",
    },
    {
        "date": "2024-07-13",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": True,
        "alert_id": "geolocation",
        "confidence": "high",
        "note": "No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.",
    },
    {
        "date": "2024-07-14",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": True,
        "alert_id": "geolocation",
        "confidence": "high",
        "note": "No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.",
    },
    {
        "date": "2024-07-15",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": True,
        "alert_id": "geolocation",
        "confidence": "high",
        "note": "No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.",
    },
    {
        "date": "2024-07-16",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "00:00–17:42 UTC",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": True,
        "alert_id": "geolocation",
        "confidence": "high",
        "note": "The stated gap runs through 17:42 UTC. The returned July 16 granules begin at 17:42 UTC.",
    },
    {
        "date": "2024-07-16",
        "local_rows": 15643,
        "local_time_min": "1742",
        "local_time_max": "2316",
        "interval": "17:42–23:59 UTC",
        "cmr_granules": 63,
        "cmr_first": "2024-07-16T17:42:00Z",
        "cmr_last": "2024-07-16T23:54:00Z",
        "alert_says_unavailable": False,
        "alert_id": "geolocation",
        "confidence": "high",
        "note": (
            "The local minimum acquisition time is 1742, the same minute as the first returned granule "
            "and the stated GPS recovery. An example granule is VNP14IMG.A2024198.1742.002."
        ),
    },
    {
        "date": "2024-07-24",
        "local_rows": 14621,
        "local_time_min": "0000",
        "local_time_max": "0523",
        "interval": "00:00–05:23 UTC",
        "cmr_granules": 55,
        "cmr_first": "2024-07-23T23:54:00Z",
        "cmr_last": "2024-07-24T05:18:00Z",
        "alert_says_unavailable": False,
        "alert_id": "july24",
        "confidence": "high",
        "note": "Every local July 24 time is at or before 0523, before the stated 05:28 outage start. The granule query returned 55 files, none later than 05:18 UTC.",
    },
    {
        "date": "2024-07-24",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "05:28–18:22 UTC",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": True,
        "alert_id": "july24",
        "confidence": "high",
        "note": "This is the outage window named by LP DAAC. No returned granule falls inside it.",
    },
    {
        "date": "2024-07-24",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "18:22–23:59 UTC",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": False,
        "alert_id": None,
        "confidence": "high",
        "note": "No VNP14IMG granule was returned after 05:18 UTC. The July 24 alert does not name the hours after 18:22. The cause is unresolved.",
    },
    {
        "date": "2024-07-25",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": False,
        "alert_id": None,
        "confidence": "high",
        "note": "CMR returned no VNP14IMG granule. No retrieved NASA alert names this date. The cause is unresolved.",
    },
    {
        "date": "2024-07-26",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": False,
        "alert_id": None,
        "confidence": "high",
        "note": "CMR returned no VNP14IMG granule. No retrieved NASA alert names this date. The cause is unresolved.",
    },
    {
        "date": "2024-07-27",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": False,
        "alert_id": None,
        "confidence": "high",
        "note": "CMR returned no VNP14IMG granule. No retrieved NASA alert names this date. The cause is unresolved.",
    },
    {
        "date": "2024-07-28",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "full UTC date",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": False,
        "alert_id": None,
        "confidence": "high",
        "note": "CMR returned no VNP14IMG granule. No retrieved NASA alert names this date. The cause is unresolved.",
    },
    {
        "date": "2024-07-29",
        "local_rows": 0,
        "local_time_min": None,
        "local_time_max": None,
        "interval": "00:00–15:24 UTC",
        "cmr_granules": 0,
        "cmr_first": None,
        "cmr_last": None,
        "alert_says_unavailable": False,
        "alert_id": None,
        "confidence": "high",
        "note": "The first returned VNP14IMG granule starts at 15:24 UTC. No retrieved NASA alert names this resume time. The cause is unresolved.",
    },
    {
        "date": "2024-07-29",
        "local_rows": 17802,
        "local_time_min": "1527",
        "local_time_max": "2357",
        "interval": "15:24–23:59 UTC",
        "cmr_granules": 86,
        "cmr_first": "2024-07-29T15:24:00Z",
        "cmr_last": "2024-07-29T23:54:00Z",
        "alert_says_unavailable": False,
        "alert_id": None,
        "confidence": "high",
        "note": "Local rows begin at 1527, three minutes after the first returned granule. The granule count is not a fire count.",
    },
)


INTERVAL_BOUNDS = {
    ("2024-07-10", "full UTC date"): ("2024-07-10T00:00:00Z", "2024-07-11T00:00:00Z"),
    ("2024-07-11", "full UTC date"): ("2024-07-11T00:00:00Z", "2024-07-12T00:00:00Z"),
    ("2024-07-12", "full UTC date"): ("2024-07-12T00:00:00Z", "2024-07-13T00:00:00Z"),
    ("2024-07-13", "full UTC date"): ("2024-07-13T00:00:00Z", "2024-07-14T00:00:00Z"),
    ("2024-07-14", "full UTC date"): ("2024-07-14T00:00:00Z", "2024-07-15T00:00:00Z"),
    ("2024-07-15", "full UTC date"): ("2024-07-15T00:00:00Z", "2024-07-16T00:00:00Z"),
    ("2024-07-16", "00:00–17:42 UTC"): ("2024-07-16T00:00:00Z", "2024-07-16T17:42:00Z"),
    ("2024-07-16", "17:42–23:59 UTC"): ("2024-07-16T17:42:00Z", "2024-07-17T00:00:00Z"),
    ("2024-07-24", "00:00–05:23 UTC"): ("2024-07-24T00:00:00Z", "2024-07-24T05:28:00Z"),
    ("2024-07-24", "05:28–18:22 UTC"): ("2024-07-24T05:28:00Z", "2024-07-24T18:22:00Z"),
    ("2024-07-24", "18:22–23:59 UTC"): ("2024-07-24T18:22:00Z", "2024-07-25T00:00:00Z"),
    ("2024-07-25", "full UTC date"): ("2024-07-25T00:00:00Z", "2024-07-26T00:00:00Z"),
    ("2024-07-26", "full UTC date"): ("2024-07-26T00:00:00Z", "2024-07-27T00:00:00Z"),
    ("2024-07-27", "full UTC date"): ("2024-07-27T00:00:00Z", "2024-07-28T00:00:00Z"),
    ("2024-07-28", "full UTC date"): ("2024-07-28T00:00:00Z", "2024-07-29T00:00:00Z"),
    ("2024-07-29", "00:00–15:24 UTC"): ("2024-07-29T00:00:00Z", "2024-07-29T15:24:00Z"),
    ("2024-07-29", "15:24–23:59 UTC"): ("2024-07-29T15:24:00Z", "2024-07-30T00:00:00Z"),
}


def _statements(item: dict, firms: str, l2: str, alert_id: str | None) -> dict[str, list[str]]:
    proves = []
    does_not_prove = [
        "No harmonization coefficient is implied.",
        "NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.",
    ]
    if firms == "confirmed_data_available":
        proves.append(
            f"Direct: fire_archive_SV-C2_850322.csv contains {item['local_rows']} rows in this UTC interval."
        )
        does_not_prove.append("Those rows were not matched one-to-one to unopened Level-2 fire pixels.")
    else:
        proves.append("Direct: the local FIRMS CSV has no row in this UTC interval.")
        does_not_prove.append(
            "Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable."
        )
    if l2 == "confirmed_source_unavailable":
        proves.append(
            f"Direct: LP DAAC alert '{alert_id}' places this entire UTC interval inside a stated VIIRS gap "
            "and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002."
        )
        does_not_prove.append("The alert does not name the FIRMS CSV as its own product.")
        if item["cmr_granules"]:
            does_not_prove.append(
                "Cataloged VNP14IMG granules inside this window were not opened, so their fire pixels are unknown."
            )
    elif l2 == "confirmed_data_available":
        proves.append(
            f"Direct: CMR returned {item['cmr_granules']} VNP14IMG granule-metadata records for this window."
        )
        does_not_prove.append("Granule metadata does not verify fire-pixel contents. The swath files were not opened.")
    else:
        proves.append("No retrieved LP DAAC sentence covers this UTC interval.")
        if item["cmr_granules"] == 0:
            proves.append("CMR returned no VNP14IMG granule for the queried window. That is a catalog observation.")
            does_not_prove.append(
                "A missing CMR granule does not establish FIRMS unavailability and is not, by itself, an authoritative outage declaration."
            )
        does_not_prove.append("The cause of this interval remains unknown.")
    return {"proves": proves, "does_not_prove": does_not_prove}


def build_investigation() -> dict:
    dates = []
    for item in INTERVALS:
        start_text, end_text = INTERVAL_BOUNDS[(item["date"], item["interval"])]
        alert_id = stated_l2_alert(parse_utc(start_text), parse_utc(end_text))
        firms = classify_firms_csv(local_rows=item["local_rows"])
        l2 = classify_l2_swath(cmr_granules=item["cmr_granules"], alert_id=alert_id)
        dates.append(
            {
                **item,
                "start_utc": start_text,
                "end_utc": end_text,
                "timezone": "UTC",
                "alert_id_applied": alert_id,
                "firms_product": "local FIRMS CSV fire_archive_SV-C2_850322.csv",
                "l2_product": "VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002",
                "cmr_product": "CMR granule metadata for short_name VNP14IMG",
                "firms_classification": firms,
                "l2_classification": l2,
                "firms_evidence_strength": "direct" if firms == "confirmed_data_available" else "insufficient",
                "l2_evidence_strength": (
                    "explicit_alert" if alert_id else ("catalog_metadata" if l2 == "confirmed_data_available" else "insufficient")
                ),
                **_statements(item, firms, l2, alert_id),
            }
        )
    return {
        "retrieved_at": RETRIEVED,
        "question": (
            "Whether the July 2024 S-NPP gaps in the local FIRMS CSV can be checked against an independent NASA archive."
        ),
        "local_archive": {
            "zip": "DL_FIRE_SV-C2_850322.zip",
            "csv": "fire_archive_SV-C2_850322.csv",
            "rows": 1635020,
            "processing_stream_in_file": None,
            "version_in_file": "2",
            "version_used_as_processing_stream": False,
        },
        "independent_queries": {
            "firms_api": "not_called",
            "firms_api_reason": "No MAP_KEY or FIRMS_MAP_KEY was set. The exact FIRMS order was not downloaded again.",
            "cmr_short_name": "VNP14IMG",
            "cmr_dataset_id_observed": "VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002",
            "cmr_example_granule": "VNP14IMG.A2024198.1742.002.2024205173004",
            "firms_fire_location_short_names_in_cmr": {
                "VNP14IMGML": 0,
                "VNP14IMGTML": 0,
                "note": "Daily CMR searches returned no granules for these short names, including on 2024-07-07, when the local CSV has rows. CMR did not serve the FIRMS fire-location table.",
            },
            "full_day_vnp14img_granules_for_scale": {"2024-07-07": 241, "2024-07-17": 241, "2024-07-30": 241},
            "other_platforms_contextual_only": {
                "VJ114IMG": "241 granules on each queried gap date, including 2024-07-10, 2024-07-15, 2024-07-25, and 2024-07-28",
                "VJ214IMG": "241 granules on those same dates",
                "use": "Shows the CMR query returned a full day for NOAA-20 and NOAA-21. It is not evidence about S-NPP.",
            },
        },
        "sources": {
            "geolocation_alert": GEOLOCATION_ALERT,
            "july24_alert": JULY24_ALERT,
            "firms_readme": FIRMS_README,
            "cmr": "https://cmr.earthdata.nasa.gov/search/granules.json",
        },
        "intervals": dates,
        "bounding_observation": {
            "date": "2024-07-09",
            "local_rows": 103164,
            "local_time_max": "2141",
            "cmr_granules": 241,
            "cmr_last": "2024-07-09T23:54:00Z",
            "note": (
                "The local CSV stops at 2141, one minute before the 21:42 UTC gap start in the July 19 LP DAAC update. "
                "CMR still lists granules later that night. Those later granules were not opened and are not counted as fire detections."
            ),
        },
        "provenance": {
            "modis_c61": {
                "filename_token": "M-C61 / fire_archive_M-C61",
                "readme_statement": "Collection 6.1; fire_archive_M-C61 is standard-quality MCD14ML.",
                "stored_version": "61.03",
                "processing_stream_in_file": None,
                "processing_stream_status": "unresolved_in_file",
            },
            "viirs_snpp_c2": {
                "filename_token": "SV-C2 / fire_archive_SV-C2",
                "readme_statement": "fire_archive_SV-C2 is standard-quality VNP14IMGTML, replacing NRT VNP14IMGTDL.",
                "stored_version": "2",
                "processing_stream_in_file": None,
                "processing_stream_status": "unresolved_in_file",
                "independent_product_checked": "VNP14IMG Level-2 swath, not the FIRMS VNP14IMGTML table.",
            },
            "viirs_noaa20_c2": {
                "filename_token": "J1V-C2 / fire_archive_J1V-C2",
                "readme_statement": "Only fire_nrt_J1V-C2 is defined, as VJ114IMGDL. Standard quality is stated as not yet available.",
                "stored_version": "2",
                "processing_stream_in_file": None,
                "processing_stream_status": "unresolved",
            },
            "viirs_noaa21_c2": {
                "filename_token": "J2V-C2 / fire_archive_J2V-C2",
                "readme_statement": "Only fire_nrt_J2V-C2 is defined, as VJ214IMGDL. Standard quality is stated as not yet available.",
                "stored_version": "2",
                "processing_stream_in_file": None,
                "processing_stream_status": "unresolved",
            },
        },
        "not_done": [
            "No date was classified as confirmed_zero_detections.",
            "Missing dates were not filled with zero.",
            "No harmonization coefficient was calculated.",
            "Raw CSV and ZIP files were not modified.",
        ],
        "unresolved": [
            "The local CSV has no product-short-name or processing-stream field.",
            "The FIRMS area API was not queried because no key was available, so this exact ZIP was not compared with a second FIRMS download.",
            "VNP14IMGTML was not found as daily CMR granules, so the FIRMS fire-location table was not directly re-read from NASA CMR.",
            "Residual VNP14IMG granules on July 9–10 were not opened. Their fire-pixel contents and quality flags are unknown.",
            "No retrieved NASA alert names July 25–29. CMR granule absence on those dates is observed; the operational cause is not.",
            "The July 24 alert header says the outage was resolved on August 5, 2024, but the retrieved body does not say the missing data were restored.",
            "NOAA-20 and NOAA-21 processing level remains unresolved. The filename uses fire_archive while the download readme says standard data are not yet available for those sensors.",
        ],
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# July 2024 S-NPP coverage investigation",
        "",
        "This note checks the local Suomi-NPP FIRMS CSV against NASA sources retrieved on 2026-11-15. "
        "A date with no local row is not a measurement of zero fire activity. "
        "NOAA-20 and NOAA-21 granule counts are context for the CMR query. They do not establish S-NPP availability.",
        "",
        "The independent product queried in CMR is `VNP14IMG`, titled VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002. "
        "That is the Level-2 swath named in the LP DAAC alerts. It is not the FIRMS fire-location table. "
        "Daily searches for `VNP14IMGTML` and `VNP14IMGML` returned no granules, including on 7 July, when the local CSV has rows. "
        "The FIRMS API was not called because no map key was configured, and the July ZIP was not downloaded again.",
        "",
        "## Sources",
        "",
        f"- {report['sources']['geolocation_alert']['title']}: {report['sources']['geolocation_alert']['url']}",
        f"  {report['sources']['geolocation_alert']['statement']}",
        f"- {report['sources']['july24_alert']['title']}: {report['sources']['july24_alert']['url']}",
        f"  {report['sources']['july24_alert']['statement']}",
        f"- FIRMS download readme: {report['sources']['firms_readme']['url']}",
        f"  {report['sources']['firms_readme']['statement']}",
        "- CMR granule search: `https://cmr.earthdata.nasa.gov/search/granules.json?short_name=VNP14IMG`.",
        "",
        "The FIRMS CSV, the Level-2 swath, and CMR metadata are classified separately. "
        "A missing CMR granule is not treated as a FIRMS outage. "
        "`confirmed_source_unavailable` is used only when an LP DAAC sentence covers the whole UTC interval. "
        "That sentence is not extended past its stated end. "
        "`confirmed_zero_detections` and `archive_delivery_gap` were not assigned.",
        "",
        "## Affected intervals",
        "",
        "Times are UTC. `end_utc` is the exclusive end used for the boundary test, except where the stated alert end is included by the window definition in code.",
        "",
        "| Date | UTC interval | FIRMS rows | VNP14IMG granules | FIRMS class | L2 class |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for item in report["intervals"]:
        lines.append(
            f"| {item['date']} | {item['start_utc']} to {item['end_utc']} | {item['local_rows']} | "
            f"{item['cmr_granules']} | `{item['firms_classification']}` | `{item['l2_classification']}` |"
        )
    lines.extend(["", "## What each interval proves", ""])
    for item in report["intervals"]:
        lines.append(f"### {item['date']} {item['interval']}")
        lines.append("")
        lines.append(f"Evidence: {item['firms_product']}; {item['l2_product']}; {item['cmr_product']}.")
        lines.append(
            f"FIRMS evidence strength: {item['firms_evidence_strength']}. "
            f"L2 evidence strength: {item['l2_evidence_strength']}."
        )
        lines.append(item["note"])
        lines.append("Proves:")
        lines.extend(f"- {point}" for point in item["proves"])
        lines.append("Does not prove:")
        lines.extend(f"- {point}" for point in item["does_not_prove"])
        lines.append("")
    bound = report["bounding_observation"]
    lines.extend(
        [
            "",
            "## Bounding local time",
            "",
            f"On {bound['date']} the local CSV has {bound['local_rows']} rows and a last acquisition time of {bound['local_time_max']}. {bound['note']}",
            "",
            "## Provenance",
            "",
            "The CSV columns do not contain a product short name or a processing stream. The stored version text was not used as one. "
            "The FIRMS download readme documents filename conventions. Those conventions are external statements, not fields in the file.",
            "",
        ]
    )
    for key, item in report["provenance"].items():
        lines.append(
            f"- {key}: {item['readme_statement']} Stored version `{item['stored_version']}`. "
            f"In-file processing stream: {item['processing_stream_status']}."
        )
    lines.extend(["", "## Unresolved", ""])
    lines.extend(f"- {item}" for item in report["unresolved"])
    lines.extend(["", "## What this investigation did not do", ""])
    lines.extend(f"- {item}" for item in report["not_done"])
    lines.append("")
    return "\n".join(lines)


def write_investigation(output_dir: Path = REPORTS) -> dict:
    report = build_investigation()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "coverage_investigation_2024_07.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    (output_dir / "coverage_investigation_2024_07.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    return report
