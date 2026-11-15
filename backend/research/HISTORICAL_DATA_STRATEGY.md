# Historical dataset strategy

This note prepares a multi-year MODIS and VIIRS active-fire record that can later be harmonized. It does not harmonize anything. No coefficient is calculated. No model is trained. `same_fire` remains `not_assessed`. The July 2024 extracts stay where they are.

The strategy has one rule that outranks filename habit. A processing stream is assigned only when a provider metadata field, or a product document that defines that exact file, names the stream. A prefix `fire_archive` or `fire_nrt`, and a version string `2` or `61.03`, are stored as text. They do not assign near-real-time or standard processing.

Documents below were retrieved in one batch from 2026-11-15T14:48:01Z through 2026-11-15T14:48:50Z unless a source line gives a different time. The retrieval log, byte counts, and SHA-256 values are in `backend/reports/milestones/milestone_12_timing.json`.

## What this strategy is for

The July 2024 FIRMS tables are a locked descriptive month. They showed that Terra, Aqua, S-NPP, NOAA-20, and NOAA-21 do not share a pixel, a confidence scale, or a demonstrated processing stream. A historical extension has to add years without mixing those differences into one series.

The extension is a set of named product families, each with its own temporal window. A later harmonization may compare families. It may not treat a shared instrument name as proof that two products are the same measurement.

## Confirmed product families

These identities come from NASA catalog and product documents, not from the July filenames.

| Family | What it is | What it is not |
| --- | --- | --- |
| MOD14 Collection 6.1 | Terra MODIS Level-2 thermal anomalies and fire, 5-minute swath, 1 km class. CMR temporal extent begins 2000-02-24. DOI `10.5067/MODIS/MOD14.061`. | Not the FIRMS CSV. Not Aqua. |
| MYD14 Collection 6.1 | Aqua MODIS Level-2 thermal anomalies and fire, 5-minute swath, 1 km class. CMR temporal extent begins 2002-07-04. DOI `10.5067/MODIS/MYD14.061`. | Not Terra. Not a combined table. |
| MCD14ML, as named by FIRMS | The download readme's name for the standard-quality MODIS fire-location table distributed by FIRMS as `fire_archive_M-C61`. The University of Maryland guide describes `MCD14ML.YYYYMM.CCC.VV.txt` as the monthly location product. | Not shown by this retrieval as a CMR collection (`short_name=MCD14ML` returned zero hits). The guide's column layout is not the FIRMS 15-column header. |
| MCD14DL | CMR title: MODIS/Aqua Terra Thermal Anomalies/Fire locations 1 km FIRMS NRT. Version `6.1NRT`. DOI `10.5067/FIRMS/MODIS/MCD14DL.NRT.0061`. Temporal extent in CMR begins 2019-12-15. The download readme maps `fire_nrt_M-C61` to this product. | Not the standard archive, on the readme and in the CMR title. |
| VNP14IMG Collection 2 | S-NPP VIIRS Level-2 active fires, 6-minute swath, 375 m. CMR temporal extent begins 2012-01-17. DOI `10.5067/VIIRS/VNP14IMG.002`. | Not the 750 m product VNP14. Not NOAA-20 or NOAA-21. |
| VJ114IMG Collection 2 | NOAA-20 / JPSS-1 VIIRS Level-2 active fires, 6-minute swath, 375 m. CMR temporal extent begins 2018-01-01. DOI `10.5067/VIIRS/VJ114IMG.002`. | Not VJ214IMG. Not the 750 m product VJ114. |
| VJ214IMG Collection 2 | NOAA-21 / JPSS-2 VIIRS Level-2 active fires, 6-minute swath, 375 m. CMR temporal extent begins 2023-02-10. DOI `10.5067/VIIRS/VJ214IMG.002`. | Not VJ114IMG. Not the 750 m product VJ214. |
| FIRMS NRT VIIRS location files | Readme: `fire_nrt_SV-C2` is VNP14IMGTDL, `fire_nrt_J1V-C2` is VJ114IMGDL, `fire_nrt_J2V-C2` is VJ214IMGDL, processed by LANCE/FIRMS. | Those short names returned zero CMR hits in this retrieval. |
| FIRMS standard S-NPP location file | Readme: `fire_archive_SV-C2` is VNP14IMGTML, University of Maryland, about a 3-month lag, and it replaces the NRT file when available. | `VNP14IMGTML` returned zero CMR hits. The Collection 2 user's guide names the monthly file `VNP14IMGML`, without the extra `T`. |

The 750 m products VNP14, VJ114, and VJ214 are in CMR with the same start dates as their 375 m siblings and with different short names and a 750 m title. The Collection 2 375 m user's guide says the 750 m product is closer in performance to the 1 km Aqua MODIS fire product, and that the 375 m product detects more fire pixels. A historical series built from the July 375 m tables does not switch to the 750 m swaths.

Earthdata's VNP14IMG page, retrieved in the same batch, says delivery of Suomi NPP VIIRS science data products ceased on 2 November 2026 (2026/306), and it points users toward VJ214IMG as the primary transition target and VJ114IMG as the secondary target. That sentence names successors. It does not make the three 375 m products one product. The same page's temporal-extent field still reads `2012-01-17 to Present`. Both sentences are on the page. New observations after the cessation date are not assumed to exist.

## NOAA-20 and NOAA-21

The processing question splits into two questions. The Level-2 swath question is answered. The FIRMS table question is not.

**Answered from NASA catalogs.** NOAA-20 is JPSS-1. NOAA-21 is JPSS-2. Each has its own Collection 2 Level-2 375 m swath, VJ114IMG and VJ214IMG, produced independently. LAADS lists VJ214IMG with platform `JPSS2(NOAA21)`, instrument VIIRS, processing level Level-2, and ArchiveSet 5200. The same LAADS row labels the collection `NPP and JPSS1 VIIRS data 2.0`. That label is the archive-set name. The platform field is JPSS-2 / NOAA-21. The archive-set wording is not a reassignment of NOAA-21 data to NOAA-20.

The Collection 2 user's guide (Version 1.2, June 2025) names monthly location products `VJ114IMGML` and `VJ214IMGML` beside `VNP14IMGML`, with file names `Vxx14IMGML.YYYYMM.CC.VV.csv`, collection `02`, and within-collection version `03`. CMR returned zero hits for `VJ114IMGML`, `VJ214IMGML`, `VJ114IMGTML`, and `VJ214IMGTML`. This milestone did not log in to the University of Maryland SFTP server described in that guide, and it did not download those files.

**Not answered for the FIRMS tables.** The download readme retrieved at 2026-11-15T14:48:01Z says: "PLEASE NOTE the standard quality data is not yet available from FIRMS for NOAA-20 and NOAA-21." It defines `fire_nrt_J1V-C2` and `fire_nrt_J2V-C2`. It does not define `fire_archive_J1V-C2` or `fire_archive_J2V-C2`.

The FIRMS area API page and the data-availability page, retrieved in the same minute, list `VIIRS_NOAA20_SP` and `VIIRS_NOAA21_SP` as standard processing, beside the NRT codes. No keyed request was sent, so those codes were not asked for a date range.

The July 2024 files are named `fire_archive_J1V-C2_850320.csv` and `fire_archive_J2V-C2_850321.csv`. Their stored version text is `2`. Their stored satellite values are `N20` and `N21`, which match the FIRMS VIIRS attribute page. None of that is a processing stream. The files have no processing-stream column. `processing_level` for those two archives remains `unresolved`. The same restraint applies to the MODIS and S-NPP July files: the readme does define `fire_archive_M-C61` and `fire_archive_SV-C2` as standard products, and applying that sentence to a local filename is still an inference from the filename. Those July files stay unresolved as well.

## How the historical series should be built

1. Keep the July 2024 CSVs, ZIPs, and experiment outputs unchanged. A new order is a new directory. It does not overwrite request ids 850319, 850320, 850321, or 850322.
2. Acquire one collection per family. For MODIS fire locations, request Collection 6.1. For VIIRS 375 m, request Collection 2. Collection 5 MODIS and Collection 1 VIIRS are earlier generations. The Collection 6 user's guide says later collections supersede earlier ones, and it lists algorithm changes that define Collection 6 relative to the preceding record.
3. Keep standard and near-real-time files in separate series. The Collection 2 guide tells latency-insensitive scientific studies to favor the non-NRT stream. The FIRMS readme says the files are split so users can tell the streams apart.
4. Keep Terra and Aqua as separate satellites inside a combined MODIS file. The July contract already does this. A combined `M-C61` table is a container, not a new instrument.
5. Do not fill a missing platform from another platform. A date with no row is a date with no delivered row.
6. Do not calculate a harmonization coefficient, fit a regression in its place, or train XGBoost on this design.
7. Leave `same_fire` at `not_assessed`. Overlapping overpasses are a sampling condition, not an identity decision.
8. Prefer the fire-location tables that match the July FIRMS layout when the goal is to extend those tables. Use Level-2 swaths when the goal is the fire mask and algorithm QA, which the FIRMS CSV does not carry. State that choice in the manifest before the order. Do not silently substitute one for the other.

Collection 6 and Collection 6.1 are a special case inside MODIS. The May 2021 user's guide says no fire-algorithm change was made for Collection 6.1, that the thermal bands used for FRP were unchanged, and that the two collections may be intermixed. The same section reports a one-day class comparison in which 18 of 17,610 fire-class pixels changed class, and a January 2020 global sample in which the fire-pixel totals were 404,057 and 404,052. This strategy still requests only Collection 6.1, because that is the collection the FIRMS download page offers and the collection LAADS labels ArchiveSet 61. The guide's intermix sentence is about those two MODIS collections. It is not a sentence about MODIS and VIIRS, and it is not a sentence about NRT and standard.

## Where the series can start and stop

The overlap timeline is in `TEMPORAL_OVERLAP_TIMELINE.md`. The conservative FIRMS window that includes all five platforms on every retrieved FIRMS coverage line runs from 17 January 2024 through 13:00 UTC on 2 November 2026. The start is the later NOAA-21 date on the FIRMS VIIRS attribute page. The end is the FIRMS cessation time on the Earthdata transition note retrieved with this batch: new FIRMS S-NPP active-fire data cease at 13:00 UTC on 2 November 2026.

That window sits inside the MODIS orbit-drift period. LDOPE known issue `HC_MOD_26008`, retrieved the same day, says Terra's final inclination adjustment and drag make-up were in 2022 and Aqua's were in 2021, that drift has changed pixel size, spacing, scan gaps, bow-tie overlap, and diurnal sampling, that significant impacts were observed in late 2024, and that the effects on MODIS fire products are under investigation. A five-platform FIRMS record and a pre-drift MODIS diurnal record are not the same record. The sampling plan keeps them in different roles.

Level-2 swath coverage begins earlier than the conservative FIRMS window: NOAA-20 on 2018-01-01 and NOAA-21 on 2023-02-10. Those dates belong to VJ114IMG and VJ214IMG. They are not copied onto the FIRMS CSV until a FIRMS document and a manifest field agree.

## What will be sampled

`VALIDATION_SAMPLING_STRATEGY.md` fixes the dates before any count is consulted. Training, calibration, and validation are three disjoint UTC periods. July 2024 is in none of them. Day and night stay in every global day. Regions are analysis windows on those days, chosen from climatic seasons rather than from detection totals.

`ACQUISITION_PLAN.md` says how an order would be placed later. This milestone placed no order and called no keyed API.

## Unresolved questions

- Which FIRMS page governs NOAA-20 and NOAA-21 standard tables: the download readme, which says they are not yet available, or the API catalog, which lists `VIIRS_NOAA20_SP` and `VIIRS_NOAA21_SP`.
- Whether `fire_archive_J1V-C2` and `fire_archive_J2V-C2` are defined anywhere the readme does not state. This retrieval did not find that definition.
- Whether `VNP14IMGTML` and `VNP14IMGML` are one product under two short names. The strings differ. CMR had neither.
- Whether the July version text `2` was meant to match the attribute page's unsuffixed standard example. The page's examples are `2.0URT`, `2.0RT`, `1.0NRT`, and `1.0`. The file contains `2`.
- Whether the July version text `61.03` was meant to match the MODIS attribute example `6.1` or `6.1NRT`. The file contains `61.03`.
- The FIRMS readme's replacement lag is about 3 months. The download page's lag is about 5 months. Both pages were retrieved in the same batch.
- The MODIS attribute footnote says the type field is only available for `MCD14DL` and calls that product standard quality. The download readme and the CMR title call `MCD14DL` NRT and call `MCD14ML` the standard table. The footnote is not used.
- S-NPP stored instrument `SNPP` and satellite `SNPP` against the attribute page's satellite code `N`. Already recorded for July. Not a processing stream.
- The effect of the 6 August 2025 NISE AMSR2 input switch on MOD14 and MYD14. LDOPE says products that do not directly ingest the cloud mask showed no downstream effect in its evaluation. It does not name the fire product.
- A complete gap list. The LDOPE page retrieved here is a set of notes, not a mission-long inventory. The FIRMS readme names additional MODIS gaps in imprecise language.

## Hypotheses that are not applied

- `fire_archive_J1V-C2` is an unpublished standard filename, and the readme is stale.
- `fire_archive_J1V-C2` is near-real-time data written with an archive prefix.
- `VIIRS_NOAA20_SP` returns `VJ114IMGML`, or a FIRMS rearrangement of it.
- Version `2` means Collection 2 standard processing because an unsuffixed example on the attribute page denotes standard processing.
- VJ214IMG can replace VNP14IMG inside an existing S-NPP time series without a new calibration. Earthdata recommends the transition. The products remain separate.

## What this milestone did not do

No historical archive was downloaded. No July row was edited. No missing detection was inferred. No coefficient was fit. `same_fire` was not changed. The S-NPP gaps in July 2024 were not filled.

## Sources

Retrieved 2026-11-15T14:48:01Z–2026-11-15T14:48:50Z unless noted.

- FIRMS download readme, SHA-256 `57cbdf28b2a423a94f831ea04870a065052d47b4aff9c228afb53d28a82bef4e`: https://firms.modaps.eosdis.nasa.gov/download/Readme.txt
- FIRMS archive download page: https://firms.modaps.eosdis.nasa.gov/download/
- FIRMS data-availability API page: https://firms.modaps.eosdis.nasa.gov/api/data_availability/
- FIRMS area API page: https://firms.modaps.eosdis.nasa.gov/api/area/
- FIRMS VIIRS attribute page: https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html
- FIRMS MODIS attribute page: https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html
- CMR collection search, `short_name` as recorded in the timing log: https://cmr.earthdata.nasa.gov/search/collections.umm_json
- Earthdata MOD14 Collection 6.1: https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod14-061
- Earthdata MYD14 Collection 6.1: https://www.earthdata.nasa.gov/data/catalog/lpcloud-myd14-061
- Earthdata VNP14IMG V002: https://www.earthdata.nasa.gov/data/catalog/lpcloud-vnp14img-002
- Earthdata VJ114IMG V002: https://www.earthdata.nasa.gov/data/catalog/lpcloud-vj114img-002
- Earthdata VJ214IMG V002: https://www.earthdata.nasa.gov/data/catalog/lpcloud-vj214img-002
- LAADS product pages for MOD14, MYD14, VNP14IMG, VJ114IMG, and VJ214IMG under https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/
- LDOPE MODIS Collection 6.1 known issues: https://landweb.modaps.eosdis.nasa.gov/knownissue?as=61&sensor=MODIS
- Earthdata, transition from MODIS to VIIRS: https://www.earthdata.nasa.gov/data/alerts-outages/transition-from-modis-viirs
- Earthdata, FIRMS transition from Suomi NPP, page date modified 2026-11-03: https://www.earthdata.nasa.gov/news/blog/transitioning-from-suomi-npp-viirs-omps-what-firms-users-need-know
- Collection 2 VIIRS 375 m Active Fire Product User's Guide, Version 1.2, June 2025, PDF SHA-256 recorded in the timing log: https://www.earthdata.nasa.gov/s3fs-public/2025-06/VIIRS_C2_AF-375m_User_Guide_1.2.pdf
- MODIS Collection 6 and Collection 6.1 Active Fire Product User's Guide, Version 1.0, May 2021. Quotations were read from the text of https://modis-land.gsfc.nasa.gov/pdf/MODIS_C6_C6.1_Fire_User_Guide_1.0.pdf during this session. A PDF of the same title was retrieved from https://modis-fire.umd.edu/files/MODIS_C6_C6.1_Fire_User_Guide_1.0.pdf and hashed in the timing log. The two URLs were not byte-compared.
