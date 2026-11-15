# July 2024 S-NPP coverage investigation

This note checks the local Suomi-NPP FIRMS CSV against NASA sources retrieved on 2026-11-15. A date with no local row is not a measurement of zero fire activity. NOAA-20 and NOAA-21 granule counts are context for the CMR query. They do not establish S-NPP availability.

The independent product queried in CMR is `VNP14IMG`, titled VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002. That is the Level-2 swath named in the LP DAAC alerts. It is not the FIRMS fire-location table. Daily searches for `VNP14IMGTML` and `VNP14IMGML` returned no granules, including on 7 July, when the local CSV has rows. The FIRMS API was not called because no map key was configured, and the July ZIP was not downloaded again.

## Sources

- Suomi NPP VIIRS Data Product Geolocation Anomaly - July 2024: https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-viirs-data-product-geolocation-anomaly-july-2024
  Data gaps will exist from 21:42:00 UTC on July 9, 2024, through 17:42:00 UTC on July 16, 2024, due to unrecoverable geolocation errors and invalid timestamps. Normal production resumed starting with July 16, 2024, after GPS recovery at 17:42:00 UTC. The anomaly start in the earlier notice is 21:46:00 UTC on July 9, 2024. The referenced datasets include VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
- Suomi NPP VIIRS Data Product Anomaly - July 2024: https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-viirs-data-product-anomaly-july-2024
  The mission experienced an outage from 05:28:00 UTC to 18:22:00 UTC on July 24, 2024. All VIIRS processing was on hold, and data for the outage period were described as not recoverable until further notice. The retrieved page body does not add a later recovery narrative. The referenced datasets include VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002. The page does not name July 25–29.
- FIRMS download readme: https://firms.modaps.eosdis.nasa.gov/download/Readme.txt
  DL_FIRE_M-C61 is MODIS Collection 6.1. fire_archive_M-C61 is described as standard-quality MCD14ML. fire_archive_SV-C2 is described as standard-quality VNP14IMGTML. fire_nrt_J1V-C2 is VJ114IMGDL and fire_nrt_J2V-C2 is VJ214IMGDL. The readme says standard-quality data are not yet available from FIRMS for NOAA-20 and NOAA-21. It does not define fire_archive_J1V-C2 or fire_archive_J2V-C2. A version field is described as distinguishing MODIS from VIIRS, not as an NRT-versus-standard flag. A request with no fire points is delivered as a header-only CSV.
- CMR granule search: `https://cmr.earthdata.nasa.gov/search/granules.json?short_name=VNP14IMG`.

The FIRMS CSV, the Level-2 swath, and CMR metadata are classified separately. A missing CMR granule is not treated as a FIRMS outage. `confirmed_source_unavailable` is used only when an LP DAAC sentence covers the whole UTC interval. That sentence is not extended past its stated end. `confirmed_zero_detections` and `archive_delivery_gap` were not assigned.

## Affected intervals

Times are UTC. `end_utc` is the exclusive end used for the boundary test, except where the stated alert end is included by the window definition in code.

| Date | UTC interval | FIRMS rows | VNP14IMG granules | FIRMS class | L2 class |
| --- | --- | ---: | ---: | --- | --- |
| 2024-07-10 | 2024-07-10T00:00:00Z to 2024-07-11T00:00:00Z | 0 | 79 | `unknown` | `confirmed_source_unavailable` |
| 2024-07-11 | 2024-07-11T00:00:00Z to 2024-07-12T00:00:00Z | 0 | 0 | `unknown` | `confirmed_source_unavailable` |
| 2024-07-12 | 2024-07-12T00:00:00Z to 2024-07-13T00:00:00Z | 0 | 0 | `unknown` | `confirmed_source_unavailable` |
| 2024-07-13 | 2024-07-13T00:00:00Z to 2024-07-14T00:00:00Z | 0 | 0 | `unknown` | `confirmed_source_unavailable` |
| 2024-07-14 | 2024-07-14T00:00:00Z to 2024-07-15T00:00:00Z | 0 | 0 | `unknown` | `confirmed_source_unavailable` |
| 2024-07-15 | 2024-07-15T00:00:00Z to 2024-07-16T00:00:00Z | 0 | 0 | `unknown` | `confirmed_source_unavailable` |
| 2024-07-16 | 2024-07-16T00:00:00Z to 2024-07-16T17:42:00Z | 0 | 0 | `unknown` | `confirmed_source_unavailable` |
| 2024-07-16 | 2024-07-16T17:42:00Z to 2024-07-17T00:00:00Z | 15643 | 63 | `confirmed_data_available` | `confirmed_data_available` |
| 2024-07-24 | 2024-07-24T00:00:00Z to 2024-07-24T05:28:00Z | 14621 | 55 | `confirmed_data_available` | `confirmed_data_available` |
| 2024-07-24 | 2024-07-24T05:28:00Z to 2024-07-24T18:22:00Z | 0 | 0 | `unknown` | `confirmed_source_unavailable` |
| 2024-07-24 | 2024-07-24T18:22:00Z to 2024-07-25T00:00:00Z | 0 | 0 | `unknown` | `unknown` |
| 2024-07-25 | 2024-07-25T00:00:00Z to 2024-07-26T00:00:00Z | 0 | 0 | `unknown` | `unknown` |
| 2024-07-26 | 2024-07-26T00:00:00Z to 2024-07-27T00:00:00Z | 0 | 0 | `unknown` | `unknown` |
| 2024-07-27 | 2024-07-27T00:00:00Z to 2024-07-28T00:00:00Z | 0 | 0 | `unknown` | `unknown` |
| 2024-07-28 | 2024-07-28T00:00:00Z to 2024-07-29T00:00:00Z | 0 | 0 | `unknown` | `unknown` |
| 2024-07-29 | 2024-07-29T00:00:00Z to 2024-07-29T15:24:00Z | 0 | 0 | `unknown` | `unknown` |
| 2024-07-29 | 2024-07-29T15:24:00Z to 2024-07-30T00:00:00Z | 17802 | 86 | `confirmed_data_available` | `confirmed_data_available` |

## What each interval proves

### 2024-07-10 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: explicit_alert.
The date falls inside the LP DAAC geolocation gap. CMR still lists 79 VNP14IMG granules, ending at 07:42 UTC. Those files were not opened. The local FIRMS CSV has no row for the date. The granule count is not a fire count.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- Direct: LP DAAC alert 'geolocation' places this entire UTC interval inside a stated VIIRS gap and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- The alert does not name the FIRMS CSV as its own product.
- Cataloged VNP14IMG granules inside this window were not opened, so their fire pixels are unknown.

### 2024-07-11 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: explicit_alert.
No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- Direct: LP DAAC alert 'geolocation' places this entire UTC interval inside a stated VIIRS gap and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- The alert does not name the FIRMS CSV as its own product.

### 2024-07-12 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: explicit_alert.
No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- Direct: LP DAAC alert 'geolocation' places this entire UTC interval inside a stated VIIRS gap and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- The alert does not name the FIRMS CSV as its own product.

### 2024-07-13 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: explicit_alert.
No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- Direct: LP DAAC alert 'geolocation' places this entire UTC interval inside a stated VIIRS gap and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- The alert does not name the FIRMS CSV as its own product.

### 2024-07-14 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: explicit_alert.
No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- Direct: LP DAAC alert 'geolocation' places this entire UTC interval inside a stated VIIRS gap and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- The alert does not name the FIRMS CSV as its own product.

### 2024-07-15 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: explicit_alert.
No VNP14IMG granule was returned, and the date is inside the stated geolocation gap.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- Direct: LP DAAC alert 'geolocation' places this entire UTC interval inside a stated VIIRS gap and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- The alert does not name the FIRMS CSV as its own product.

### 2024-07-16 00:00–17:42 UTC

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: explicit_alert.
The stated gap runs through 17:42 UTC. The returned July 16 granules begin at 17:42 UTC.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- Direct: LP DAAC alert 'geolocation' places this entire UTC interval inside a stated VIIRS gap and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- The alert does not name the FIRMS CSV as its own product.

### 2024-07-16 17:42–23:59 UTC

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: direct. L2 evidence strength: catalog_metadata.
The local minimum acquisition time is 1742, the same minute as the first returned granule and the stated GPS recovery. An example granule is VNP14IMG.A2024198.1742.002.
Proves:
- Direct: fire_archive_SV-C2_850322.csv contains 15643 rows in this UTC interval.
- Direct: CMR returned 63 VNP14IMG granule-metadata records for this window.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Those rows were not matched one-to-one to unopened Level-2 fire pixels.
- Granule metadata does not verify fire-pixel contents. The swath files were not opened.

### 2024-07-24 00:00–05:23 UTC

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: direct. L2 evidence strength: catalog_metadata.
Every local July 24 time is at or before 0523, before the stated 05:28 outage start. The granule query returned 55 files, none later than 05:18 UTC.
Proves:
- Direct: fire_archive_SV-C2_850322.csv contains 14621 rows in this UTC interval.
- Direct: CMR returned 55 VNP14IMG granule-metadata records for this window.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Those rows were not matched one-to-one to unopened Level-2 fire pixels.
- Granule metadata does not verify fire-pixel contents. The swath files were not opened.

### 2024-07-24 05:28–18:22 UTC

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: explicit_alert.
This is the outage window named by LP DAAC. No returned granule falls inside it.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- Direct: LP DAAC alert 'july24' places this entire UTC interval inside a stated VIIRS gap and lists VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- The alert does not name the FIRMS CSV as its own product.

### 2024-07-24 18:22–23:59 UTC

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: insufficient.
No VNP14IMG granule was returned after 05:18 UTC. The July 24 alert does not name the hours after 18:22. The cause is unresolved.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- No retrieved LP DAAC sentence covers this UTC interval.
- CMR returned no VNP14IMG granule for the queried window. That is a catalog observation.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- A missing CMR granule does not establish FIRMS unavailability and is not, by itself, an authoritative outage declaration.
- The cause of this interval remains unknown.

### 2024-07-25 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: insufficient.
CMR returned no VNP14IMG granule. No retrieved NASA alert names this date. The cause is unresolved.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- No retrieved LP DAAC sentence covers this UTC interval.
- CMR returned no VNP14IMG granule for the queried window. That is a catalog observation.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- A missing CMR granule does not establish FIRMS unavailability and is not, by itself, an authoritative outage declaration.
- The cause of this interval remains unknown.

### 2024-07-26 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: insufficient.
CMR returned no VNP14IMG granule. No retrieved NASA alert names this date. The cause is unresolved.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- No retrieved LP DAAC sentence covers this UTC interval.
- CMR returned no VNP14IMG granule for the queried window. That is a catalog observation.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- A missing CMR granule does not establish FIRMS unavailability and is not, by itself, an authoritative outage declaration.
- The cause of this interval remains unknown.

### 2024-07-27 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: insufficient.
CMR returned no VNP14IMG granule. No retrieved NASA alert names this date. The cause is unresolved.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- No retrieved LP DAAC sentence covers this UTC interval.
- CMR returned no VNP14IMG granule for the queried window. That is a catalog observation.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- A missing CMR granule does not establish FIRMS unavailability and is not, by itself, an authoritative outage declaration.
- The cause of this interval remains unknown.

### 2024-07-28 full UTC date

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: insufficient.
CMR returned no VNP14IMG granule. No retrieved NASA alert names this date. The cause is unresolved.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- No retrieved LP DAAC sentence covers this UTC interval.
- CMR returned no VNP14IMG granule for the queried window. That is a catalog observation.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- A missing CMR granule does not establish FIRMS unavailability and is not, by itself, an authoritative outage declaration.
- The cause of this interval remains unknown.

### 2024-07-29 00:00–15:24 UTC

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: insufficient. L2 evidence strength: insufficient.
The first returned VNP14IMG granule starts at 15:24 UTC. No retrieved NASA alert names this resume time. The cause is unresolved.
Proves:
- Direct: the local FIRMS CSV has no row in this UTC interval.
- No retrieved LP DAAC sentence covers this UTC interval.
- CMR returned no VNP14IMG granule for the queried window. That is a catalog observation.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Zero delivered rows are not zero fire detections and do not establish that FIRMS was unavailable.
- A missing CMR granule does not establish FIRMS unavailability and is not, by itself, an authoritative outage declaration.
- The cause of this interval remains unknown.

### 2024-07-29 15:24–23:59 UTC

Evidence: local FIRMS CSV fire_archive_SV-C2_850322.csv; VNP14IMG, VIIRS/NPP Active Fires 6-Min L2 Swath 375m V002; CMR granule metadata for short_name VNP14IMG.
FIRMS evidence strength: direct. L2 evidence strength: catalog_metadata.
Local rows begin at 1527, three minutes after the first returned granule. The granule count is not a fire count.
Proves:
- Direct: fire_archive_SV-C2_850322.csv contains 17802 rows in this UTC interval.
- Direct: CMR returned 86 VNP14IMG granule-metadata records for this window.
Does not prove:
- No harmonization coefficient is implied.
- NOAA-20 and NOAA-21 granule counts are not evidence about S-NPP.
- Those rows were not matched one-to-one to unopened Level-2 fire pixels.
- Granule metadata does not verify fire-pixel contents. The swath files were not opened.


## Bounding local time

On 2024-07-09 the local CSV has 103164 rows and a last acquisition time of 2141. The local CSV stops at 2141, one minute before the 21:42 UTC gap start in the July 19 LP DAAC update. CMR still lists granules later that night. Those later granules were not opened and are not counted as fire detections.

## Provenance

The CSV columns do not contain a product short name or a processing stream. The stored version text was not used as one. The FIRMS download readme documents filename conventions. Those conventions are external statements, not fields in the file.

- modis_c61: Collection 6.1; fire_archive_M-C61 is standard-quality MCD14ML. Stored version `61.03`. In-file processing stream: unresolved_in_file.
- viirs_snpp_c2: fire_archive_SV-C2 is standard-quality VNP14IMGTML, replacing NRT VNP14IMGTDL. Stored version `2`. In-file processing stream: unresolved_in_file.
- viirs_noaa20_c2: Only fire_nrt_J1V-C2 is defined, as VJ114IMGDL. Standard quality is stated as not yet available. Stored version `2`. In-file processing stream: unresolved.
- viirs_noaa21_c2: Only fire_nrt_J2V-C2 is defined, as VJ214IMGDL. Standard quality is stated as not yet available. Stored version `2`. In-file processing stream: unresolved.

## Unresolved

- The local CSV has no product-short-name or processing-stream field.
- The FIRMS area API was not queried because no key was available, so this exact ZIP was not compared with a second FIRMS download.
- VNP14IMGTML was not found as daily CMR granules, so the FIRMS fire-location table was not directly re-read from NASA CMR.
- Residual VNP14IMG granules on July 9–10 were not opened. Their fire-pixel contents and quality flags are unknown.
- No retrieved NASA alert names July 25–29. CMR granule absence on those dates is observed; the operational cause is not.
- The July 24 alert header says the outage was resolved on August 5, 2024, but the retrieved body does not say the missing data were restored.
- NOAA-20 and NOAA-21 processing level remains unresolved. The filename uses fire_archive while the download readme says standard data are not yet available for those sensors.

## What this investigation did not do

- No date was classified as confirmed_zero_detections.
- Missing dates were not filled with zero.
- No harmonization coefficient was calculated.
- Raw CSV and ZIP files were not modified.
