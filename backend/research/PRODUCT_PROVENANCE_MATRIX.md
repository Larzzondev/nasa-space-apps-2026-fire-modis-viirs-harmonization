# Product provenance matrix

Retrieved 2026-11-15T14:48:01Z through 2026-11-15T14:48:50Z. Byte counts and SHA-256 values for those responses are in `backend/reports/milestones/milestone_12_timing.json`.

A row is confirmed when the cited NASA document states it. A July filename or a version cell is local text. It is not a processing level. `same_fire` is `not_assessed`. No coefficient is calculated.

The July 2024 files are:

| Local CSV | Bytes measured 2026-11-15 | Stored satellite | Stored instrument | Stored version |
| --- | ---: | --- | --- | --- |
| `modis/fire_archive_M-C61_850319.csv` | 54,196,122 | Terra, Aqua | MODIS | 61.03 |
| `viirs_snpp/fire_archive_SV-C2_850322.csv` | 132,818,598 | SNPP | SNPP | 2 |
| `viirs_noaa20/fire_archive_J1V-C2_850320.csv` | 235,770,840 | N20 | VIIRS | 2 |
| `viirs_noaa21/fire_archive_J2V-C2_850321.csv` | 225,148,614 | N21 | VIIRS | 2 |

Those four files sum to 647,934,174 bytes. That is the byte count already recorded for the July experiment batch. The files were not rewritten for this count.

## MODIS Terra

| Item | Status | Statement | Source |
| --- | --- | --- | --- |
| Official Level-2 identifier | Confirmed | `MOD14`, version `061`, title MODIS/Terra Thermal Anomalies/Fire 5-Min L2 Swath 1km V061. Processing level 2. DOI `10.5067/MODIS/MOD14.061`. | CMR and Earthdata `lpcloud-mod14-061` |
| Collection | Confirmed | LAADS: MODIS Collection 6.1, ArchiveSet 61. Earthdata file-name example uses collection token `061`: `MOD14.A2025224.1755.061.2025224212147.hdf`. | LAADS MOD14 page; Earthdata MOD14 page |
| Platform and instrument | Confirmed | Terra, MODIS. | LAADS MOD14 page |
| Standard versus NRT, for the Level-2 swath | Confirmed as two CMR collections | Standard `MOD14` `061` begins 2000-02-24 and is ACTIVE with no end date in the retrieved record. A second CMR hit is `MOD14` version `6.1NRT`, beginning 2021-02-07, DOI `10.5067/MODIS/MOD14.NRT.061`. | CMR |
| FIRMS standard name | Confirmed as a readme definition | `fire_archive_M-C61` is standard-quality `MCD14ML`, University of Maryland, described as replacing NRT `MCD14DL`. The combined file holds Terra and Aqua. | FIRMS download readme |
| FIRMS NRT name | Confirmed as a readme definition | `fire_nrt_M-C61` is `MCD14DL`, LANCE/FIRMS. CMR titles `MCD14DL` version `6.1NRT` as FIRMS NRT and begins that record on 2019-12-15. | Readme; CMR |
| FIRMS layer coverage | Confirmed for the layer page | Terra temporal coverage on the MODIS attribute page: 1 November 2000 – present. The download page states Collection 6.1 coverage from 1 November 2000 and does not split Terra from Aqua on that line. | FIRMS MODIS attribute page; FIRMS download page |
| Why November 2000 | Confirmed | The user's guide says Terra MODIS began acquiring data in February 2000, calibration and crosstalk remained problematic until early November 2000, and the CMG and fire-location products are not distributed for the earlier period. Level-2 swath and Level-3 tiled products do exist before November 2000, with the quality limits in guide section 7.2.1. | MODIS C6/C6.1 user's guide, Version 1.0, May 2021, sections 7.2.1, 8.3.10, and 8.3.11 |
| Spatial resolution | Confirmed | Level-2 swath is the 1 km class. Earthdata describes an MYD14 swath of about 2,030 km along track and 2,300 km across track; the user's guide describes a Level-2 area of about 2,340 km along scan by 2,030 km along track. FIRMS says the algorithm produces 1 km fire pixels and that `scan` and `track` are the actual pixel size, which grows toward the edge of scan. | Earthdata MYD14 page; user's guide section 3.2; FIRMS MODIS attribute page |
| Quality flags in the science product | Confirmed | Fire-mask classes 0 through 9. Classes 7, 8, and 9 are low, nominal, and high confidence fire. Confidence `C` maps to low for `0% ≤ C < 30%`, nominal for `30% ≤ C < 80%`, and high for `80% ≤ C ≤ 100%`. A pixel-level QA image carries the algorithm tests. `MCD14ML` adds `type` 0–3 and day/night. | User's guide sections 5.1, 5.5, and 8.4.3 |
| Quality flags in the FIRMS CSV | Confirmed as a smaller set | The July header has `confidence`, `type`, and `daynight`. It has no fire-mask class and no algorithm-QA bits. FIRMS describes MODIS confidence as 0–100 and the three classes. The numeric class edges used above are the user's guide, not a FIRMS column. | July header; FIRMS MODIS attribute page |
| Local July processing level | Unresolved | The file is named `fire_archive_M-C61_850319.csv` and stores version `61.03`. The readme defines that filename pattern as standard `MCD14ML`. The attribute page's standard example is `6.1`, and its NRT example is `6.1NRT`. `61.03` matches neither example. The filename and the version cell are not used as the stream. | Readme; attribute page; local header |
| Known processing changes | Confirmed | Collection 6, available since 2015, changed water processing, false-alarm rejection, small-fire detection, sun-glint rejection, cloud masking, confidence, and the FRP method relative to the preceding collection. Collection 6.1 changed Level-1B calibration of bands 1 and 2. The guide says the fire algorithm and FRP retrieval were unchanged and that Collection 6 and 6.1 fire products may be intermixed, with a reported January 2020 global fire-pixel difference of 5 pixels (404,057 versus 404,052). LDOPE says Collection 6 forward processing of Terra and Aqua land products was discontinued on 15 February 2023. | User's guide sections 2.1 and 2.2; LDOPE C61 known-issue page |

Terra launched 18 December 1999, according to the same user's guide. Launch is not the start of the fire-location record.

## MODIS Aqua

| Item | Status | Statement | Source |
| --- | --- | --- | --- |
| Official Level-2 identifier | Confirmed | `MYD14`, version `061`, Level 2. DOI `10.5067/MODIS/MYD14.061`. CMR temporal extent begins 2002-07-04. A second hit is `MYD14` `6.1NRT`, beginning 2021-02-07, DOI `10.5067/MODIS/MYD14.NRT.061`. | CMR; Earthdata `lpcloud-myd14-061` |
| FIRMS layer coverage | Confirmed, and one day off the Level-2 date | Attribute page: Aqua 3 July 2002 – present. CMR and Earthdata: 2002-07-04. The later date is the one both the Level-2 catalog and a cautious FIRMS intersection share. | FIRMS MODIS attribute page; CMR |
| Combined table | Confirmed | `MCD14ML` and the FIRMS `M-C61` file contain Terra and Aqua together. The user's guide satellite codes are `T` and `A`. The July file stores `Terra` and `Aqua`. | User's guide Table 10; FIRMS attribute page; local file |
| Outage | Confirmed | Aqua formatter-multiplexer failure on 16 August 2020. Regular science telemetry was lost for about two weeks, through the guide's stated window of 16 August–2 September 2020. Direct Broadcast coverage during that window was limited. | User's guide section 7.2.4 |
| Local July processing level | Unresolved | Aqua rows sit in the same `fire_archive_M-C61` file as Terra. The stream is the file's stream, which is unresolved for the reason in the Terra row. | Local file; readme |

Aqua launched 4 May 2002, according to the user's guide. The fire products start later, on the dates above.

The attribute page says Terra passes north to south across the equator in the morning and Aqua passes south to north in the afternoon. LDOPE `HC_MOD_26008` says both orbits have since drifted. Afternoon and morning labels are the design description, not a 2024–2026 overpass measurement.

## VIIRS S-NPP

| Item | Status | Statement | Source |
| --- | --- | --- | --- |
| Official Level-2 identifier | Confirmed | `VNP14IMG`, version `002`, VIIRS/NPP Active Fires 6-Min L2 Swath 375m. Processing level 2. DOI `10.5067/VIIRS/VNP14IMG.002`. CMR temporal extent begins 2012-01-17. Platform Suomi-NPP. | CMR; Earthdata catalog |
| Sibling 750 m product | Confirmed as a different product | `VNP14` version `002`, 750 m, same start date in CMR, DOI `10.5067/VIIRS/VNP14.002`. The 375 m guide says it detects more fire pixels than `VNP14`, especially at night. | CMR; Collection 2 user's guide, June 2025 |
| Effective fire-record start | Confirmed as guidance | First active fires on 19 January 2012. The guide tells users to adopt 20 January 2012 because the first hours were still cooling calibration sources. FIRMS download and attribute pages both start S-NPP 375 m coverage on 20 January 2012. | Collection 2 guide section 4; FIRMS download page; FIRMS VIIRS attribute page |
| End of new data | Confirmed, with a catalog field that still says Present | Earthdata product text: delivery of Suomi NPP VIIRS science data products ceased on 2 November 2026 (2026/306). FIRMS transition note: new FIRMS active-fire data from Suomi NPP cease at 13:00 UTC on 2 November 2026. The download page ends the coverage line on 2 November 2026. The Earthdata temporal-extent widget still says `2012-01-17 to Present`. | Earthdata VNP14IMG page; Earthdata FIRMS transition note; FIRMS download page |
| FIRMS standard and NRT names | Confirmed as readme definitions | `fire_archive_SV-C2` is standard `VNP14IMGTML`. `fire_nrt_SV-C2` is NRT `VNP14IMGTDL`. API codes `VIIRS_SNPP_SP` and `VIIRS_SNPP_NRT` are listed. CMR returned zero hits for `VNP14IMGTML`, `VNP14IMGTDL`, and `VNP14IMGML`. | Readme; area API page; CMR |
| Spatial resolution | Confirmed | 375 m at nadir. Swath about 3,060 km. 6,400 samples. `scan` and `track` store the actual pixel size. Imagery resolution of 250 m on the FIRMS layer page is the imagery layer, not the fire pixel. | Collection 2 guide sections 3.1 and 4; FIRMS VIIRS attribute page; Earthdata VNP14IMG page |
| Quality flags | Confirmed for Level 2; reduced in FIRMS | Level-2 fire mask classes 0–9. Low confidence is class 7, nominal class 8, high class 9. High confidence is associated with saturated pixels, including the nominal I4 saturation temperature 367 K. Algorithm QA is a 32-bit field; bit 22 marks residual bow-tie, which matters if FRP is summed. FIRMS confidence is `l`, `n`, or `h`. The July CSV does not carry the QA bits, the view angle, or a saturation flag. | Collection 2 guide Tables 1–3 and the saturation FAQ; FIRMS VIIRS attribute page |
| Type field | Confirmed, with a bug history | Guide: `type` 0 presumed vegetation fire, 1 active volcano, 2 other static land source, 3 offshore. Versions 1 and 2 of the monthly location product set `type` inconsistently. The bug was corrected in May 2025 and the files were reprocessed to version 3 (`VV` = `03`). | Collection 2 guide sections 3.2 and 6.1 |
| Local July file | Unresolved stream | `fire_archive_SV-C2_850322.csv`, version `2`, satellite `SNPP`, instrument `SNPP`. The attribute page's satellite code for Suomi NPP is `N`, and its version examples are not the bare string `2`. The readme defines the filename pattern as standard. The pattern is not applied. | Local header; attribute page; readme |
| July 2024 gaps | Confirmed as already investigated | LP DAAC geolocation gap 21:42 UTC on 9 July 2024 through 17:42 UTC on 16 July 2024, and the 24 July 2024 outage from 05:28 UTC to 18:22 UTC, for the named VIIRS products including the 375 m Level-2 fire product. Later July dates without an LP DAAC sentence remain unknown. Those intervals are not re-derived here. | `backend/reports/coverage_investigation_2024_07.md`, sources retrieved 2026-11-15T04:20:00Z |

## VIIRS NOAA-20 (JPSS-1)

| Item | Status | Statement | Source |
| --- | --- | --- | --- |
| Official Level-2 identifier | Confirmed | `VJ114IMG`, version `002`, VIIRS/JPSS1 Active Fires 6-Min L2 Swath 375m. Level 2. Platform NOAA-20. DOI `10.5067/VIIRS/VJ114IMG.002`. CMR temporal extent begins 2018-01-01 and has no end date in the retrieved record. | CMR; Earthdata `lpcloud-vj114img-002`; LAADS |
| 750 m sibling | Confirmed as a different product | `VJ114` version `002`, 750 m, DOI `10.5067/VIIRS/VJ114.002`, CMR start 2018-01-01. | CMR |
| FIRMS NRT name | Confirmed | `fire_nrt_J1V-C2` is `VJ114IMGDL`, LANCE/FIRMS. API code `VIIRS_NOAA20_NRT`. The area API links the NOAA-20 attribute table at a URL whose path contains `vj114imgtdlnrt`. | Download readme; area API page |
| FIRMS standard name | Unresolved | The readme does not define `fire_archive_J1V-C2` and says standard-quality data are not yet available from FIRMS for NOAA-20. The API lists `VIIRS_NOAA20_SP`. The Collection 2 guide defines monthly `VJ114IMGML`. CMR has no hit for that short name. | Readme; API pages; user's guide; CMR |
| FIRMS coverage lines disagree | Confirmed disagreement | Download page: 1 April 2018 – present. Attribute page: 1 January 2020 – present. Level-2 catalog: 2018-01-01. These are three statements. | Download page; attribute page; CMR |
| Orbit note | Confirmed as a FIRMS description | NOAA-21's orbit is about 50 minutes ahead of NOAA-20, with S-NPP between them. Nominal S-NPP equator crossing is given as 1:30 pm and 1:30 am. | FIRMS VIIRS attribute page |
| Local July file | Unresolved | `fire_archive_J1V-C2_850320.csv`, satellite `N20`, instrument `VIIRS`, version `2`. `N20` matches the attribute page. The version and the filename do not assign the stream. | Local header; attribute page; readme |

## VIIRS NOAA-21 (JPSS-2)

| Item | Status | Statement | Source |
| --- | --- | --- | --- |
| Official Level-2 identifier | Confirmed | `VJ214IMG`, version `002`, VIIRS/JPSS2 Active Fires 6-Min L2 Swath 375m. Level 2. Platform on the Earthdata page: NOAA-21. LAADS platform cell: `JPSS2(NOAA21)`. DOI `10.5067/VIIRS/VJ214IMG.002`. CMR temporal extent begins 2023-02-10. Spatial resolution 375 m. | CMR; Earthdata; LAADS |
| Catalog wording to keep distinct | Confirmed | Earthdata says the long name should read "VIIRS/JPSS2 Thermal Anomalies/Fire 6-Min L2 Swath 375m V002" and that the current title wording should be rectified in a future version. LAADS collection cell reads `NPP and JPSS1 VIIRS data 2.0 (ArchiveSet 5200)` while the platform cell reads JPSS-2 / NOAA-21. The platform cell is the satellite identity used here. | Earthdata VJ214IMG page; LAADS VJ214IMG page |
| 750 m sibling | Confirmed as a different product | `VJ214` version `002`, 750 m, DOI `10.5067/VIIRS/VJ214.002`, CMR start 2023-02-10. | CMR |
| FIRMS NRT name | Confirmed | `fire_nrt_J2V-C2` is `VJ214IMGDL`. API code `VIIRS_NOAA21_NRT`. | Download readme; area API page |
| FIRMS standard name | Unresolved | Same readme sentence as NOAA-20: standard-quality data are not yet available from FIRMS. `fire_archive_J2V-C2` is not defined there. The API lists `VIIRS_NOAA21_SP`. The guide names `VJ214IMGML`. CMR returned zero hits for that name. | Readme; API pages; user's guide; CMR |
| FIRMS coverage lines disagree | Confirmed disagreement | Download page: 1 March 2023 – present. Attribute page: 17 January 2024 – present. Level-2 catalog: 2023-02-10. | Download page; attribute page; CMR |
| Local July file | Unresolved | `fire_archive_J2V-C2_850321.csv`, satellite `N21`, instrument `VIIRS`, version `2`. `N21` matches the attribute page. The stream is unresolved. | Local header; attribute page; readme |

## Archive naming

| Archive | Pattern | What the pattern encodes |
| --- | --- | --- |
| FIRMS zip | `DL_FIRE_M-C61_<id>.zip`, `DL_FIRE_SV-C2_<id>.zip`, `DL_FIRE_J1V-C2_<id>.zip`, `DL_FIRE_J2V-C2_<id>.zip` | Product code plus download request id. `C61` means MODIS Collection 6.1. `C2` means VIIRS Collection 2. The readme says a CSV request also contains `Readme.txt`. |
| FIRMS CSV | `fire_nrt_<code>_<id>.csv` or `fire_archive_<code>_<id>.csv` | The readme defines `fire_nrt_*` for all four codes and `fire_archive_*` for `M-C61` and `SV-C2` only. |
| MODIS Level 2 | `MOD14.AYYYYDDD.HHMM.061.YYYYDDDHHMMSS.hdf` and the Aqua `MYD14` equivalent | Short name, acquisition day and time, collection, production time. |
| VIIRS Level 2 | `Vxx14IMG.AYYYYDDD.HHMM.002.yyyydddhhmmss.nc` | `xx` is `NP`, `J1`, or `J2`. Collection token `002`. |
| VIIRS monthly location, guide | `Vxx14IMGML.YYYYMM.02.03.csv` | Platform, year-month, collection 02, product version 03. |
| MODIS monthly location, guide | `MCD14ML.YYYYMM.CCC.VV.txt` | Collection and within-collection version. The guide's then-current `VV` is `03`. Fixed-width text, not the FIRMS comma-separated header. |

Coordinates in the FIRMS delivery are WGS84 geographic, according to the download readme. A request that finds no fire points is delivered as a header-only CSV or an empty DBF. That is an empty detection file, not a failed download.

## Version field

The download readme says that if NRT and standard files are combined, the Collection / Version field is how to distinguish the source. The VIIRS attribute page says a suffix `URT`, `RT`, or `NRT` marks those streams and that a collection value with no suffix is the standard example. The MODIS attribute page gives `6.1URT`, `6.1RT`, `6.1NRT`, and `6.1`.

The July values `61.03` and `2` are not those examples. They are recorded. They are not mapped.

## Milestone 13 area API check

The keyed run was retrieved 2026-11-15T15:41:39Z through 2026-11-15T15:41:56Z. The log is `backend/reports/firms_api_provenance_2024_07_07.json`. Timing is `backend/reports/milestones/milestone_13_timing.json`. An earlier pass the same day, at 15:23Z, stopped before any authenticated URL because the key was not configured.

`VIIRS_NOAA20_SP` availability returned HTTP 200. The body names that source from 2018-04-01 through 2026-07-31. `VIIRS_NOAA21_SP` availability returned HTTP 200 and names that source from 2023-03-01 through 2026-07-31. 2024-07-07 falls inside both windows. The area requests used each file's observed detection extent, day range 1, and CSV. Both area responses were HTTP 200, with zero retries. NOAA-20 returned 82,372 rows. NOAA-21 returned 87,637 rows. Every API `acq_date` was 2024-07-07. Every API `version` cell was `2`. Satellites were `N20` and `N21`.

Shared column names match on all 82,372 NOAA-20 rows and all 87,637 NOAA-21 rows. No shared-field identity was missing, added, or changed. The archive headers contain `brightness` and `bright_t31`. The API headers contain `bright_ti4` and `bright_ti5`. Milestone 13 did not alias those names and did not compare their values. Product equivalence stays `not_assessed`. The local archive streams stay `unresolved`: the query label is Standard Processing, and the response version text is still `2`, which is not one of the attribute-page suffix examples. `same_fire` stays `not_assessed`. No coefficient was calculated. The thermal comparison is the next section.

The area page still links the NOAA-20 attribute table to `https://www.earthdata.nasa.gov/learn/find-data/near-real-time/firms/vj114imgtdlnrt` and the NOAA-21 attribute table to `https://www.earthdata.nasa.gov/learn/find-data/near-real-time/firms/vj214imgtdlnrt`. Those NRT paths are not the stream of the local CSVs.

## Thermal fields on 7 July 2024

The field comparison is `backend/reports/viirs_thermal_field_mapping_2024_07_07.json`. Area responses were retrieved 2026-11-15T16:00:00Z through 2026-11-15T16:00:23Z. The user's guide text layer was read at 2026-11-15T16:06:44Z from the same PDF bytes, SHA-256 `fb957afb6e465cb312fb8229a2b6e424c489344bb09e76a7baee80a248d1ccb7`. No second area request was sent for that reading.

The FIRMS VIIRS attribute page, retrieved 2026-11-15T16:06:41Z, says `Bright_ti4 / Brightness (in web services)` is the VIIRS I-4 channel brightness temperature of the fire pixel in Kelvin, and `Bright_ti5 / Brightness_2 (in web services)` is the I-5 channel brightness temperature of the fire pixel in Kelvin. The same page gives the I-4 interval as 3.55-3.93 µm and calls I-4 mid-infrared. It does not contain `bright_t31`, and it does not state a scale factor. The Earthdata active-fire attribute page states the same Kelvin sentences and the same web-service aliases. On that combined page, `bright_t31` occurs with the MODIS channel 31 sentence. It is not named beside I-5.

The FIRMS MODIS attribute page says `bright_t31` is the channel 31 brightness temperature in Kelvin. That sentence is a MODIS definition. It is not applied to the VIIRS files.

The Collection 2 user's guide, Version 1.2, June 2025, names Level-2 `FP_T4` and `FP_T5` as fire-pixel I4 and I5 brightness temperature in kelvin, and the monthly location fields `T4` and `T5` as the same quantities in K. It calls I5 long-wave infrared and gives 367 K as the nominal I4 saturation temperature. It does not name `brightness`, `bright_t31`, `bright_ti4`, or `bright_ti5`, and it does not mention a scale factor. The Earthdata variable tables for `VJ114IMG` and `VJ214IMG` list `FP_T4` and `FP_T5` in Kelvin, float32, with fill, scale factor, and offset all `N/A`. Those rows describe the Level-2 swath. They are not a scale for the FIRMS CSV.

The archive columns were left as `brightness` and `bright_t31`. The API columns were left as `bright_ti4` and `bright_ti5`. Rows were paired on the shared non-thermal fields. Both platforms aligned on every row: 82,372 NOAA-20 rows and 87,637 NOAA-21 rows. `brightness` equals `bright_ti4` on every paired row, including the raw text. `bright_t31` equals `bright_ti5` on every paired row, including the raw text. The maximum absolute difference, mean absolute difference, mean signed difference, and the type-7 quantiles are 0. No value was missing or invalid. No constant offset was present, and no coefficient was calculated. The crossed pairs are not a mapping. NOAA-20 has 0 crossed equalities. NOAA-21 has 1 crossed equality in each direction out of 87,637 numeric pairs.

`brightness` is the documented web-service alias of the I-4 Kelvin measurement. `bright_t31` is not the documented VIIRS alias of the I-5 measurement; that alias is `Brightness_2`. Because one archive name remains unnamed on the VIIRS attribute page, both platforms are classified `same_observations_field_equivalence_unresolved`. The `VIIRS_NOAA20_SP` and `VIIRS_NOAA21_SP` labels are not used as the processing stream. Each stream stays `unresolved`. Product equivalence stays `not_assessed`. `same_fire` stays `not_assessed`.

The day-file checksums after the comparison matched the checksums before it. The monthly NOAA checksums matched `ingestion_2024_07.json`. The files were not rewritten.

The day files were read and hashed and not written. Their checksums after the run matched the checksums before it. The monthly NOAA checksums matched `ingestion_2024_07.json`. The observed extents are stored-point ranges, not the original order area.

## Sources

The source list and retrieval window are the same as in `HISTORICAL_DATA_STRATEGY.md`. The July coverage investigation cited for the S-NPP gaps was retrieved earlier the same day, at 2026-11-15T04:20:00Z, and is not re-fetched here.
