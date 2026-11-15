# Data readiness and matching methodology

This review asks whether the current files and the proximity matcher are ready for a multi-date calibration. It is not a temporal validation and it does not add a statistical model. Dates present: 2024-07-07. Temporal validation: not_performed. Calibration coefficients calculated: no.

## Provenance discrepancy

Standard quality data is not yet available from FIRMS for NOAA-20 and NOAA-21. The readme names only the NRT short names VJ114IMGDL and VJ214IMGDL for those satellites.

The API availability page lists VIIRS_NOAA20_SP and VIIRS_NOAA21_SP.

The local CSVs contain neither the readme short names nor the API sensor codes.

Resolution: unresolved. The disagreement is between two FIRMS pages. It does not identify the processing stream of the local files.

The FIRMS VIIRS attribute page also describes a version-suffix convention for URT, RT, NRT, and standard processing. The local VIIRS version string is `2`, and the local MODIS version string is `61.03`. Those strings are not the page's examples (`2.0URT`, `2.0RT`, `1.0NRT`, `1.0`). The suffix convention was not applied. A filename beginning with `fire_archive` or `fire_nrt` was not applied either.

Two further document mismatches are recorded and left unresolved. The VIIRS page says the Suomi NPP satellite code is `N`, while the local S-NPP file stores `SNPP`. The page says the hot-spot type attribute is only available for VNP14IMGT standard-quality data, while every local archive, including NOAA-20 and NOAA-21, has a `type` column. Neither mismatch identifies the processing stream.

### Documents retrieved

- The FIRMS download readme defines fire_nrt_M-C61 as MCD14DL and fire_archive_M-C61 as standard-quality MCD14ML. It defines fire_nrt_SV-C2 as VNP14IMGTDL and fire_archive_SV-C2 as standard-quality VNP14IMGTML. It defines fire_nrt_J1V-C2 as VJ114IMGDL and fire_nrt_J2V-C2 as VJ214IMGDL. It does not define a standard-product filename or short name for NOAA-20 or NOAA-21. It states that standard quality data is not yet available from FIRMS for NOAA-20 and NOAA-21. The characters after the product code are described as the download request id. Supplied coordinates are described as WGS84. The Collection / Version field is described as the way to distinguish MODIS from VIIRS, not as an NRT-versus-standard flag. Source: https://firms.modaps.eosdis.nasa.gov/download/Readme.txt (retrieved 2026-11-14).
- The FIRMS API data-availability page lists MODIS_NRT, MODIS_SP, VIIRS_SNPP_NRT, VIIRS_SNPP_SP, VIIRS_NOAA20_NRT, VIIRS_NOAA20_SP, VIIRS_NOAA21_NRT, and VIIRS_NOAA21_SP. These are catalog sensor codes. They are not columns in the local CSV files. Source: https://firms.modaps.eosdis.nasa.gov/api/data_availability/ (retrieved 2026-11-14).
- The FIRMS VIIRS attribute page says the version value identifies the collection and, by suffix, the processing source: URT, RT, and NRT suffixes are those streams, and a collection value with no suffix is the page's example of standard processing (examples include 2.0URT, 2.0RT, 1.0NRT, and 1.0). It names Bright_ti4 / Brightness as I-4 and Bright_ti5 / Brightness_2 as I-5. It says high-confidence pixels are associated with day or nighttime saturated pixels. It says the satellite code for Suomi NPP is N. It says the inferred hot-spot type attribute is only available for VNP14IMGT standard-quality data. It describes NOAA-21 as about 50 minutes ahead of NOAA-20, with S-NPP between them. Source: https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html (retrieved 2026-11-14).
- The LAADS page for VJ114IMG titles it VIIRS/JPSS1 Active Fires 6-Min L2 Swath 375m, platform JPSS1 (NOAA-20), instrument VIIRS, processing level Level-2, collection NPP and JPSS1 VIIRS data 2.0. The page describes a swath product. It does not say that a FIRMS CSV named fire_archive_J1V-C2 is that swath file. Source: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ114IMG (retrieved 2026-11-14).

## Provenance matrix

Verified values were read from the local files. Unverified values are document statements that do not identify these files. Missing values have no field in the files and were not filled from the filename or the version column.

### modis

| Field | Status | Value | Evidence |
| --- | --- | --- | --- |
| `sha256` | verified | 45b23bd13722f989f974943b35e07c74ee1164d2399717e17c9a35f707c19352 | SHA-256 of the local file bytes. |
| `byte_size` | verified | 1635095 | Size in bytes of the local file. |
| `filename` | verified | fire_archive_M-C61_850118.csv | The filename is recorded as text. It is not interpreted as a processing stream. |
| `columns` | verified | latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type | Header row of the CSV. |
| `row_count` | verified | 20410 | Data rows read from the CSV. |
| `acquisition_dates` | verified | 2024-07-07 (20,410) | Distinct acq_date values and their row counts. |
| `satellite_values` | verified | Aqua (13,366), Terra (7,044) | Distinct satellite values stored in the file. |
| `instrument_values` | verified | MODIS (20,410) | Distinct instrument values stored in the file. |
| `version_values` | verified | 61.03 (20,410) | Distinct version strings stored in the file. The strings are not mapped to a processing stream. |
| `processing_level_column_present` | verified | no | Searched the header for processing_level, product_level, processing_stream, and product_short_name. |
| `saturation_or_quality_flag_present` | verified | no | Searched the header for a saturation, QA, or quality column. |
| `product_short_name` | missing | — | The CSV has no product-short-name field. The download readme and the API catalog name several candidate products. Choosing one would require the filename prefix or an assumption about the version string, and this review does not do that. |
| `processing_stream` | missing | — | No processing-stream attribute is stored. Filename prefixes and version values were not used to assign NRT, RT, URT, or standard processing. |
| `provider_checksum` | missing | — | No provider checksum or original zip readme is stored beside the CSV. |
| `area_of_interest` | missing | — | The CSV does not record the requested geographic scope. |
| `production_timestamp` | missing | — | The CSV does not record when the product was generated. |
| `projection_stated_in_file` | missing | — | The CSV does not state a projection. The download readme describes FIRMS coordinates as WGS84 in general. |
| `readme_filename_mapping` | unverified | — | The download readme maps fire_nrt and fire_archive names to product short names. Applying that map to this file would use the filename as evidence of processing level. |
| `api_sensor_code` | unverified | — | The API catalog lists NRT and SP sensor codes. None of those codes is a value in this CSV. |
| `version_suffix_rule` | unverified | — | The FIRMS VIIRS attribute page says a version without a URT, RT, or NRT suffix denotes standard processing in its examples. The stored VIIRS value is 2 and the stored MODIS value is 61.03. Those strings are not the page's examples, and this review does not apply the suffix rule. |

### viirs_noaa20

| Field | Status | Value | Evidence |
| --- | --- | --- | --- |
| `sha256` | verified | b2febdffbf7ad9dcaf7066ed913b8e0028eebff94bb79a9dd4e2e346dd4f9907 | SHA-256 of the local file bytes. |
| `byte_size` | verified | 6691837 | Size in bytes of the local file. |
| `filename` | verified | fire_archive_J1V-C2_850119.csv | The filename is recorded as text. It is not interpreted as a processing stream. |
| `columns` | verified | latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type | Header row of the CSV. |
| `row_count` | verified | 82372 | Data rows read from the CSV. |
| `acquisition_dates` | verified | 2024-07-07 (82,372) | Distinct acq_date values and their row counts. |
| `satellite_values` | verified | N20 (82,372) | Distinct satellite values stored in the file. |
| `instrument_values` | verified | VIIRS (82,372) | Distinct instrument values stored in the file. |
| `version_values` | verified | 2 (82,372) | Distinct version strings stored in the file. The strings are not mapped to a processing stream. |
| `processing_level_column_present` | verified | no | Searched the header for processing_level, product_level, processing_stream, and product_short_name. |
| `saturation_or_quality_flag_present` | verified | no | Searched the header for a saturation, QA, or quality column. |
| `product_short_name` | missing | — | The CSV has no product-short-name field. The download readme and the API catalog name several candidate products. Choosing one would require the filename prefix or an assumption about the version string, and this review does not do that. |
| `processing_stream` | missing | — | No processing-stream attribute is stored. Filename prefixes and version values were not used to assign NRT, RT, URT, or standard processing. |
| `provider_checksum` | missing | — | No provider checksum or original zip readme is stored beside the CSV. |
| `area_of_interest` | missing | — | The CSV does not record the requested geographic scope. |
| `production_timestamp` | missing | — | The CSV does not record when the product was generated. |
| `projection_stated_in_file` | missing | — | The CSV does not state a projection. The download readme describes FIRMS coordinates as WGS84 in general. |
| `readme_filename_mapping` | unverified | — | The download readme maps fire_nrt and fire_archive names to product short names. Applying that map to this file would use the filename as evidence of processing level. |
| `api_sensor_code` | unverified | — | The API catalog lists NRT and SP sensor codes. None of those codes is a value in this CSV. |
| `version_suffix_rule` | unverified | — | The FIRMS VIIRS attribute page says a version without a URT, RT, or NRT suffix denotes standard processing in its examples. The stored VIIRS value is 2 and the stored MODIS value is 61.03. Those strings are not the page's examples, and this review does not apply the suffix rule. |

### viirs_noaa21

| Field | Status | Value | Evidence |
| --- | --- | --- | --- |
| `sha256` | verified | 5be3094edf2dc4461b9eadc82c97657b730550aaa92000d88fc2b1fbe4b46917 | SHA-256 of the local file bytes. |
| `byte_size` | verified | 7113989 | Size in bytes of the local file. |
| `filename` | verified | fire_archive_J2V-C2_850120.csv | The filename is recorded as text. It is not interpreted as a processing stream. |
| `columns` | verified | latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type | Header row of the CSV. |
| `row_count` | verified | 87637 | Data rows read from the CSV. |
| `acquisition_dates` | verified | 2024-07-07 (87,637) | Distinct acq_date values and their row counts. |
| `satellite_values` | verified | N21 (87,637) | Distinct satellite values stored in the file. |
| `instrument_values` | verified | VIIRS (87,637) | Distinct instrument values stored in the file. |
| `version_values` | verified | 2 (87,637) | Distinct version strings stored in the file. The strings are not mapped to a processing stream. |
| `processing_level_column_present` | verified | no | Searched the header for processing_level, product_level, processing_stream, and product_short_name. |
| `saturation_or_quality_flag_present` | verified | no | Searched the header for a saturation, QA, or quality column. |
| `product_short_name` | missing | — | The CSV has no product-short-name field. The download readme and the API catalog name several candidate products. Choosing one would require the filename prefix or an assumption about the version string, and this review does not do that. |
| `processing_stream` | missing | — | No processing-stream attribute is stored. Filename prefixes and version values were not used to assign NRT, RT, URT, or standard processing. |
| `provider_checksum` | missing | — | No provider checksum or original zip readme is stored beside the CSV. |
| `area_of_interest` | missing | — | The CSV does not record the requested geographic scope. |
| `production_timestamp` | missing | — | The CSV does not record when the product was generated. |
| `projection_stated_in_file` | missing | — | The CSV does not state a projection. The download readme describes FIRMS coordinates as WGS84 in general. |
| `readme_filename_mapping` | unverified | — | The download readme maps fire_nrt and fire_archive names to product short names. Applying that map to this file would use the filename as evidence of processing level. |
| `api_sensor_code` | unverified | — | The API catalog lists NRT and SP sensor codes. None of those codes is a value in this CSV. |
| `version_suffix_rule` | unverified | — | The FIRMS VIIRS attribute page says a version without a URT, RT, or NRT suffix denotes standard processing in its examples. The stored VIIRS value is 2 and the stored MODIS value is 61.03. Those strings are not the page's examples, and this review does not apply the suffix rule. |

### viirs_snpp

| Field | Status | Value | Evidence |
| --- | --- | --- | --- |
| `sha256` | verified | f6ceca9e5b8677febd42826fe3df5e84701da4b60bb9a7156f4440f3bebfd4a9 | SHA-256 of the local file bytes. |
| `byte_size` | verified | 7050277 | Size in bytes of the local file. |
| `filename` | verified | fire_archive_SV-C2_850121.csv | The filename is recorded as text. It is not interpreted as a processing stream. |
| `columns` | verified | latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type | Header row of the CSV. |
| `row_count` | verified | 86840 | Data rows read from the CSV. |
| `acquisition_dates` | verified | 2024-07-07 (86,840) | Distinct acq_date values and their row counts. |
| `satellite_values` | verified | SNPP (86,840) | Distinct satellite values stored in the file. |
| `instrument_values` | verified | SNPP (86,840) | Distinct instrument values stored in the file. |
| `version_values` | verified | 2 (86,840) | Distinct version strings stored in the file. The strings are not mapped to a processing stream. |
| `processing_level_column_present` | verified | no | Searched the header for processing_level, product_level, processing_stream, and product_short_name. |
| `saturation_or_quality_flag_present` | verified | no | Searched the header for a saturation, QA, or quality column. |
| `product_short_name` | missing | — | The CSV has no product-short-name field. The download readme and the API catalog name several candidate products. Choosing one would require the filename prefix or an assumption about the version string, and this review does not do that. |
| `processing_stream` | missing | — | No processing-stream attribute is stored. Filename prefixes and version values were not used to assign NRT, RT, URT, or standard processing. |
| `provider_checksum` | missing | — | No provider checksum or original zip readme is stored beside the CSV. |
| `area_of_interest` | missing | — | The CSV does not record the requested geographic scope. |
| `production_timestamp` | missing | — | The CSV does not record when the product was generated. |
| `projection_stated_in_file` | missing | — | The CSV does not state a projection. The download readme describes FIRMS coordinates as WGS84 in general. |
| `readme_filename_mapping` | unverified | — | The download readme maps fire_nrt and fire_archive names to product short names. Applying that map to this file would use the filename as evidence of processing level. |
| `api_sensor_code` | unverified | — | The API catalog lists NRT and SP sensor codes. None of those codes is a value in this CSV. |
| `version_suffix_rule` | unverified | — | The FIRMS VIIRS attribute page says a version without a URT, RT, or NRT suffix denotes standard processing in its examples. The stored VIIRS value is 2 and the stored MODIS value is 61.03. Those strings are not the page's examples, and this review does not apply the suffix rule. |

## Exact product and processing stream

The product short name and the processing stream are missing for every local archive. Candidate names from the download readme and sensor codes from the API catalog remain unverified against these CSVs.

## Matching methodology

Reviewed implementation: `fire_data.temporal.proximity_counts`.

- Distance: ECEF chord on a sphere of radius 6371008.8 m, the same definition as the temporal proximity count.
- Time: Absolute difference of UTC minutes, with the calendar date included in the minute count.
- Satellite pairs: Each unordered pair of satellites is visited once. A self-pair is omitted.
- Detection pairs: Each pair of detections inside the radius and the time window is counted once. The reverse ordered pair is not stored. A detection may join many pairs.
- Nearest-neighbor ties: The smallest distance is kept. If distances tie, the smaller absolute time difference is kept.
- Duplicates: Repeated CSV rows are counted and retained. They are not collapsed before matching.
- Same fire: `not_assessed`.
- Unique fires: Pair counts and detection counts are not converted into a unique-fire total.

Duplicate accounting on the current files: 277,259 data rows, 0 exact duplicate rows, 0 extra rows with the same satellite, latitude text, longitude text, date, and time. Rows removed before matching: 0. An exact duplicate is a repeated data line within the local archives. A location-time duplicate is another row with the same satellite, latitude text, longitude text, acq_date, and acq_time. Both kinds stay in the matcher as separate detections. Duplicate pairs across satellites are not collapsed, and the reverse of a pair is not stored.

Nearest-neighbor distance is directional and is limited to the largest radius in the configuration set. A detection whose nearest partner lies outside a tighter radius is counted as without a neighbor for that tighter configuration. Raw pair count can exceed either unique-detection count because one detection can pair with many partners. `detections_with_at_least_one_neighbor` is the sum of the unique source rows and the unique target rows that participate. That sum is a count of archived rows. It is not a count of fires, and it is not added across satellite pairs.

Full quantile distributions for pair distance, absolute time difference, and both nearest-neighbor directions are in `data_readiness.json`. The table below is the per-configuration summary.

| Pair | Radius (m) | Max Δt (min) | Raw pairs | Unique source | Unique target | Detections with a neighbor | Source NN p50 (m) | Pair distance p50 (m) | Pair Δt p50 (min) | Same fire |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Terra–Aqua | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–Aqua | 375 | 30 | 9 | 9 | 9 | 18 | 310.5 | 310.5 | 13.0 | not_assessed |
| Terra–Aqua | 375 | 180 | 161 | 158 | 156 | 314 | 263.2 | 264.4 | 107.0 | not_assessed |
| Terra–Aqua | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–Aqua | 1,000 | 30 | 68 | 46 | 54 | 100 | 545.1 | 669.8 | 12.0 | not_assessed |
| Terra–Aqua | 1,000 | 180 | 970 | 640 | 661 | 1,301 | 552.6 | 652.3 | 107.0 | not_assessed |
| Terra–Aqua | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–Aqua | 5,000 | 30 | 402 | 96 | 120 | 216 | 1,028.6 | 2,223.4 | 10.0 | not_assessed |
| Terra–Aqua | 5,000 | 180 | 6,258 | 1,031 | 1,220 | 2,251 | 792.5 | 2,337.3 | 107.0 | not_assessed |
| Terra–NOAA-20 | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–NOAA-20 | 375 | 30 | 214 | 139 | 199 | 338 | 238.1 | 267.1 | 6.0 | not_assessed |
| Terra–NOAA-20 | 375 | 180 | 3,158 | 1,573 | 3,079 | 4,652 | 201.0 | 262.3 | 164.0 | not_assessed |
| Terra–NOAA-20 | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–NOAA-20 | 1,000 | 30 | 1,032 | 296 | 665 | 961 | 409.9 | 628.0 | 6.0 | not_assessed |
| Terra–NOAA-20 | 1,000 | 180 | 15,874 | 2,578 | 9,962 | 12,540 | 303.3 | 631.1 | 164.0 | not_assessed |
| Terra–NOAA-20 | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–NOAA-20 | 5,000 | 30 | 5,402 | 336 | 1,013 | 1,349 | 466.0 | 2,214.4 | 6.0 | not_assessed |
| Terra–NOAA-20 | 5,000 | 180 | 85,634 | 2,897 | 16,139 | 19,036 | 345.3 | 2,376.7 | 165.0 | not_assessed |
| Terra–NOAA-21 | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–NOAA-21 | 375 | 30 | 511 | 354 | 496 | 850 | 233.6 | 259.0 | 18.0 | not_assessed |
| Terra–NOAA-21 | 375 | 180 | 3,006 | 1,578 | 2,938 | 4,516 | 206.7 | 259.0 | 118.0 | not_assessed |
| Terra–NOAA-21 | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–NOAA-21 | 1,000 | 30 | 2,498 | 724 | 1,565 | 2,289 | 392.2 | 628.8 | 18.0 | not_assessed |
| Terra–NOAA-21 | 1,000 | 180 | 16,210 | 2,603 | 10,158 | 12,761 | 304.1 | 643.5 | 118.0 | not_assessed |
| Terra–NOAA-21 | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–NOAA-21 | 5,000 | 30 | 11,549 | 840 | 2,360 | 3,200 | 445.1 | 2,113.5 | 18.0 | not_assessed |
| Terra–NOAA-21 | 5,000 | 180 | 96,100 | 2,935 | 16,968 | 19,903 | 346.9 | 2,464.5 | 128.0 | not_assessed |
| Terra–S-NPP | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–S-NPP | 375 | 30 | 54 | 37 | 51 | 88 | 249.6 | 274.4 | 30.0 | not_assessed |
| Terra–S-NPP | 375 | 180 | 3,133 | 1,537 | 3,053 | 4,590 | 203.9 | 260.4 | 141.0 | not_assessed |
| Terra–S-NPP | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–S-NPP | 1,000 | 30 | 310 | 101 | 187 | 288 | 469.7 | 659.5 | 30.0 | not_assessed |
| Terra–S-NPP | 1,000 | 180 | 16,422 | 2,499 | 10,238 | 12,737 | 295.8 | 637.8 | 141.0 | not_assessed |
| Terra–S-NPP | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Terra–S-NPP | 5,000 | 30 | 1,693 | 137 | 292 | 429 | 558.8 | 2,310.8 | 30.0 | not_assessed |
| Terra–S-NPP | 5,000 | 180 | 93,237 | 2,786 | 16,740 | 19,526 | 333.6 | 2,430.9 | 143.0 | not_assessed |
| Aqua–NOAA-20 | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–NOAA-20 | 375 | 30 | 4,655 | 3,170 | 4,628 | 7,798 | 220.4 | 258.6 | 27.0 | not_assessed |
| Aqua–NOAA-20 | 375 | 180 | 7,501 | 4,323 | 7,313 | 11,636 | 212.7 | 259.4 | 27.0 | not_assessed |
| Aqua–NOAA-20 | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–NOAA-20 | 1,000 | 30 | 23,916 | 7,293 | 16,746 | 24,039 | 432.1 | 638.5 | 27.0 | not_assessed |
| Aqua–NOAA-20 | 1,000 | 180 | 39,752 | 9,267 | 26,288 | 35,555 | 403.1 | 646.6 | 27.0 | not_assessed |
| Aqua–NOAA-20 | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–NOAA-20 | 5,000 | 30 | 111,618 | 9,443 | 28,498 | 37,941 | 561.9 | 2,158.8 | 26.0 | not_assessed |
| Aqua–NOAA-20 | 5,000 | 180 | 200,689 | 11,715 | 43,802 | 55,517 | 522.0 | 2,223.8 | 27.0 | not_assessed |
| Aqua–NOAA-21 | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–NOAA-21 | 375 | 30 | 1,763 | 1,213 | 1,726 | 2,939 | 224.5 | 259.4 | 14.0 | not_assessed |
| Aqua–NOAA-21 | 375 | 180 | 6,588 | 3,613 | 6,407 | 10,020 | 211.2 | 259.7 | 65.0 | not_assessed |
| Aqua–NOAA-21 | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–NOAA-21 | 1,000 | 30 | 10,005 | 2,847 | 6,949 | 9,796 | 443.1 | 663.7 | 17.0 | not_assessed |
| Aqua–NOAA-21 | 1,000 | 180 | 37,393 | 7,815 | 24,812 | 32,627 | 405.5 | 660.3 | 64.0 | not_assessed |
| Aqua–NOAA-21 | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–NOAA-21 | 5,000 | 30 | 54,190 | 3,874 | 12,060 | 15,934 | 612.5 | 2,165.0 | 19.0 | not_assessed |
| Aqua–NOAA-21 | 5,000 | 180 | 220,512 | 10,719 | 44,180 | 54,899 | 583.0 | 2,357.4 | 62.0 | not_assessed |
| Aqua–S-NPP | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–S-NPP | 375 | 30 | 13 | 10 | 13 | 23 | 189.9 | 193.1 | 29.0 | not_assessed |
| Aqua–S-NPP | 375 | 180 | 7,031 | 3,833 | 6,820 | 10,653 | 209.6 | 260.8 | 51.0 | not_assessed |
| Aqua–S-NPP | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–S-NPP | 1,000 | 30 | 69 | 24 | 53 | 77 | 469.7 | 687.6 | 29.0 | not_assessed |
| Aqua–S-NPP | 1,000 | 180 | 39,149 | 8,338 | 26,106 | 34,444 | 413.1 | 654.3 | 51.0 | not_assessed |
| Aqua–S-NPP | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| Aqua–S-NPP | 5,000 | 30 | 303 | 32 | 113 | 145 | 622.1 | 1,507.5 | 29.0 | not_assessed |
| Aqua–S-NPP | 5,000 | 180 | 218,425 | 11,390 | 45,944 | 57,334 | 578.8 | 2,323.2 | 51.0 | not_assessed |
| NOAA-20–NOAA-21 | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–NOAA-21 | 375 | 30 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–NOAA-21 | 375 | 180 | 100,849 | 49,357 | 52,073 | 101,430 | 184.8 | 250.7 | 50.0 | not_assessed |
| NOAA-20–NOAA-21 | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–NOAA-21 | 1,000 | 30 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–NOAA-21 | 1,000 | 180 | 395,259 | 62,200 | 66,884 | 129,084 | 216.4 | 584.5 | 50.0 | not_assessed |
| NOAA-20–NOAA-21 | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–NOAA-21 | 5,000 | 30 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–NOAA-21 | 5,000 | 180 | 2,073,568 | 69,345 | 74,359 | 143,704 | 236.8 | 2,402.3 | 50.0 | not_assessed |
| NOAA-20–S-NPP | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–S-NPP | 375 | 30 | 77,181 | 48,320 | 48,275 | 96,595 | 197.6 | 248.0 | 25.0 | not_assessed |
| NOAA-20–S-NPP | 375 | 180 | 110,911 | 54,686 | 57,007 | 111,693 | 184.4 | 250.1 | 25.0 | not_assessed |
| NOAA-20–S-NPP | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–S-NPP | 1,000 | 30 | 275,306 | 60,860 | 59,844 | 120,704 | 229.2 | 560.2 | 25.0 | not_assessed |
| NOAA-20–S-NPP | 1,000 | 180 | 419,339 | 65,991 | 70,103 | 136,094 | 208.6 | 575.0 | 25.0 | not_assessed |
| NOAA-20–S-NPP | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-20–S-NPP | 5,000 | 30 | 1,275,182 | 67,478 | 65,817 | 133,295 | 248.4 | 2,295.0 | 25.0 | not_assessed |
| NOAA-20–S-NPP | 5,000 | 180 | 2,083,460 | 72,106 | 76,638 | 148,744 | 222.9 | 2,356.6 | 25.0 | not_assessed |
| NOAA-21–S-NPP | 375 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-21–S-NPP | 375 | 30 | 73,884 | 45,522 | 46,063 | 91,585 | 195.6 | 248.3 | 25.0 | not_assessed |
| NOAA-21–S-NPP | 375 | 180 | 113,992 | 55,809 | 56,034 | 111,843 | 184.5 | 251.2 | 25.0 | not_assessed |
| NOAA-21–S-NPP | 1,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-21–S-NPP | 1,000 | 30 | 275,918 | 56,235 | 59,107 | 115,342 | 223.7 | 571.5 | 25.0 | not_assessed |
| NOAA-21–S-NPP | 1,000 | 180 | 447,758 | 68,910 | 69,735 | 138,645 | 213.2 | 583.8 | 25.0 | not_assessed |
| NOAA-21–S-NPP | 5,000 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | not_assessed |
| NOAA-21–S-NPP | 5,000 | 30 | 1,379,296 | 61,395 | 65,630 | 127,025 | 238.7 | 2,384.1 | 25.0 | not_assessed |
| NOAA-21–S-NPP | 5,000 | 180 | 2,354,224 | 75,649 | 76,190 | 151,839 | 229.1 | 2,421.5 | 25.0 | not_assessed |

## Calibration readiness

Each variable has one class. No coefficient is calculated.

| Variable | Class | Why |
| --- | --- | --- |
| `frp` | Candidate measurement | FRP is stored in MW on every satellite in this extract. It is the measurement a later calibration would compare. The retrieval is sensor-specific, the processing stream is unresolved, and only one date is present, so no coefficient is calculated. |
| `scan` | Observation geometry | Scan is the stored along-scan pixel size in km. It describes the observation, not the fire intensity. |
| `track` | Observation geometry | Track is the stored along-track pixel size in km. It describes the observation, not the fire intensity. |
| `daynight` | Stratification variable | Daynight is the stored D or N flag. It can separate strata. The file does not record whether the flag came from solar zenith angle or from orbit direction, so the flag is used only as stored. |
| `brightness` | Excluded until further evidence | VIIRS files store an exact brightness of 367 K with no Level-1 saturation flag, so those rows cannot be marked confirmed saturated. MODIS brightness is a different stored temperature and reaches above 367 K. The two columns are not one measurement. |
| `confidence` | Excluded until further evidence | MODIS confidence is an integer from 0 through 100. VIIRS confidence is l, n, or h. The FIRMS VIIRS page describes h as associated with saturated pixels; these CSVs do not carry the saturation bit that would confirm that association row by row. The scales are not a shared quality weight. |
| `satellite` | Stratification variable | Satellite identity defines the sensor stratum. Detections from different satellites are not added as independent fires. |
| `acquisition_time` | Matching key | acq_date and acq_time locate the observation in UTC. They are keys for a proximity window. The clock time alone is not a fire attribute to rescale. |
| `latitude_longitude` | Matching key | Latitude and longitude are the stored pixel-center coordinates used to compute distance. They are match keys. The file does not state a projection; the download readme describes FIRMS coordinates as WGS84 in general. |

## Data acquisition specification

Obtain 30 acquisition dates with comparable FIRMS active-fire tables for Terra, Aqua, S-NPP, NOAA-20, and NOAA-21. This specification describes the request. It does not create those files.

Target date count: 30. Dates acquired for this specification: none. Dates already on disk: 2024-07-07. Fabricated dates: no.

After one processing stream is named in a provider metadata field, choose 30 distinct UTC dates with a rule written into the manifest before download. The rule must spread dates across months rather than take 30 consecutive days, and it must be reproducible from a recorded seed or calendar formula. The specific 30 dates are chosen at acquisition time. They are not invented here.

A date enters the analysis set only when all five satellites have a file for that date from the same processing stream and the same recorded area of interest. A satellite with no detections is represented by a header-only CSV, not by an omitted file and not by imputed rows.

The current archives contain one acquisition date, 2024-07-07, and no processing-stream field. They do not satisfy the 30-date specification.

### Product identifiers to require in the manifest

| Identifier role | Value in the download readme |
| --- | --- |
| `MODIS_NRT` | MCD14DL |
| `MODIS_standard` | MCD14ML |
| `SNPP_NRT` | VNP14IMGTDL |
| `SNPP_standard` | VNP14IMGTML |
| `NOAA20_NRT` | VJ114IMGDL |
| `NOAA21_NRT` | VJ214IMGDL |
| `NOAA20_standard_in_download_readme` | not stated |
| `NOAA21_standard_in_download_readme` | not stated |

API sensor codes listed on the availability page: `MODIS_NRT`, `MODIS_SP`, `VIIRS_SNPP_NRT`, `VIIRS_SNPP_SP`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA20_SP`, `VIIRS_NOAA21_NRT`, `VIIRS_NOAA21_SP`.

The download readme and the API catalog disagree on whether NOAA-20 and NOAA-21 standard products are available. The manifest for the 30-date bundle must name the short name and the stream in a metadata field. A filename prefix is not sufficient.

### Processing-level requirements

- Every file carries an explicit processing-stream value in a metadata field supplied with the download.
- The 30 dates use one stream. NRT and standard files are not mixed.
- NOAA-20 and NOAA-21 are included only when that metadata field is present, because the download readme and the API catalog currently disagree.
- A version string of 2 or 61.03, and a filename beginning with fire_archive or fire_nrt, are stored and are not accepted as the stream.
- Level-2 swath granules such as the LAADS VJ114IMG product are a different file type. They are not substituted for the FIRMS table unless the manifest says so.

### Required metadata

- product short name
- processing stream
- collection or version, stored separately from the processing stream
- satellite and instrument
- area of interest and date range requested
- projection
- production time
- variable definitions for brightness, the second thermal column, confidence, and type
- provider checksum
- source URL and retrieval time

### Missing-data handling

- A failed download is recorded as a failure. It is not written as an empty scene.
- A successful request with no detections is a header-only CSV and is retained.
- A date missing any of the five satellites is excluded from the 30-date set.
- Detections, brightness values, and FRP values are not imputed.
- The existing 2024-07-07 files are not copied forward to fill the other 29 dates.

### File naming and checksums

Preserve the provider filename: True. Layout: `data/raw/<source_id>/<provider_filename>`. Manifest: `data/manifest/firms_30day_manifest.csv`. Checksum: SHA-256. Compute SHA-256 on the downloaded bytes before any rewrite. Store lowercase hexadecimal. Recompute the digest before analysis and stop if it differs from the manifest.

## Unresolved

- The processing stream and product short name of each local archive.
- Which FIRMS page is current for NOAA-20 and NOAA-21 standard products, and whether either page describes these downloads.
- Whether the stored VIIRS version `2` was intended to match the attribute page's unsuffixed standard example.
- Whether any proximity pair is the same physical fire.
- The 30 acquisition dates themselves, which are not chosen until a stream and an area of interest are recorded.

## Reproduction

From the backend directory:

```bash
.venv\Scripts\python -m fire_data.readiness
```

The command writes `reports/data_readiness.md` and `reports/data_readiness.json`. It leaves the exploratory report, the anomaly report, the temporal report, and `data/raw/` unchanged.
