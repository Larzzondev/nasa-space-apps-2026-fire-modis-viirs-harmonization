# Temporal overlap timeline

Dates are UTC. A period is **usable** only for the product family named in that row, and only where no listed exception applies. **Potentially incompatible** means a retrieved NASA document describes a processing, calibration, orbit, or coverage change that can change the measurement, and this repository has not measured that change outside July 2024. **Unavailable** means a retrieved document places the interval outside production or inside a stated gap. **Unresolved** means the documents disagree or do not specify the boundary.

`same_fire` is `not_assessed` in every period. Overlapping clocks are not identity. No coefficient is calculated. July 2024 rows are not edited and are not given new detections.

Sources for the dates are the documents retrieved 2026-11-15T14:48:01Z–2026-11-15T14:48:50Z and listed in `HISTORICAL_DATA_STRATEGY.md`, plus the July 2024 coverage investigation retrieved 2026-11-15T04:20:00Z.

## Platform introduction

| Platform | Spacecraft launch, where a fire guide states it | First date that matters for fire data | Document |
| --- | --- | --- | --- |
| Terra MODIS | 18 December 1999 | Level-2 `MOD14` `061` begins 2000-02-24. FIRMS Terra fire layer and the distributed location/CMG series begin 1 November 2000. | User's guide section 8.1.2 and 8.3.10; CMR; FIRMS MODIS attribute page |
| Aqua MODIS | 4 May 2002 | Level-2 `MYD14` `061` begins 2002-07-04. FIRMS attribute page says 3 July 2002. | User's guide; CMR; FIRMS attribute page |
| VIIRS S-NPP | The Collection 2 guide says the sensor was deployed in October 2011. This retrieval did not open a separate launch bulletin. | Catalog `VNP14IMG` begins 2012-01-17. Guide: adopt 20 January 2012. FIRMS: 20 January 2012. | Collection 2 guide; CMR; FIRMS pages |
| VIIRS NOAA-20 | Not taken from a launch bulletin in this retrieval. The readme identifies NOAA-20 as JPSS-1. | Level-2 `VJ114IMG` begins 2018-01-01. FIRMS download page: 1 April 2018. FIRMS attribute page: 1 January 2020. | CMR; FIRMS pages; readme |
| VIIRS NOAA-21 | Not taken from a launch bulletin in this retrieval. The readme identifies NOAA-21 as JPSS-2. | Level-2 `VJ214IMG` begins 2023-02-10. FIRMS download page: 1 March 2023. FIRMS attribute page: 17 January 2024. | CMR; FIRMS pages; readme |

## Timeline

| Interval | Platforms in documented production | Status | Why |
| --- | --- | --- | --- |
| 2000-02-24 through 2000-10-31 | Terra `MOD14` Level 2 and Level 3. Location and CMG products withheld. | Potentially incompatible for a time series. Unavailable for the FIRMS location table. | Pre-November 2000 calibration and dead detectors. Guide section 7.2.1 lists striping and both missed small fires and missed large fires. |
| 2000-11-01 through 2002-07-03 | Terra FIRMS fire layer and Terra Level 2. Aqua not yet in the fire record. | Usable as a Terra-only Collection 6.1 series if the order is Collection 6.1. Not a two-MODIS series. | FIRMS Terra start. Aqua's later of the two published starts is 2002-07-04. |
| 2002-07-03 | Aqua on the FIRMS attribute page only. | Unresolved | One-day disagreement with CMR `MYD14`, which starts 2002-07-04. |
| 2002-07-04 through 2012-01-19 | Terra and Aqua. | Usable for MODIS Collection 6.1 location tables, except the gaps below. No VIIRS fire record yet. | Both MODIS Level-2 records have started. S-NPP effective start is the next day. |
| 2012-01-17 through 2012-01-19 | Terra, Aqua, and cataloged `VNP14IMG`. | Potentially incompatible for VIIRS. | Catalog start is 17 January. The guide tells users to begin on 20 January because early orbits were still stabilizing thermal calibration. |
| 2012-01-20 through 2017-12-31 | Terra, Aqua, S-NPP 375 m. | Usable for MODIS Collection 6.1 plus S-NPP Collection 2, except stated gaps. NOAA-20 Level 2 has not started. | Intersection of the FIRMS S-NPP start and the day before the `VJ114IMG` start. |
| 2018-01-01 through 2018-03-31 | Level-2 NOAA-20 has started. FIRMS download coverage has not. | Usable for `VJ114IMG`. Unavailable for the FIRMS download line. Unresolved for any FIRMS standard table. | Three NOAA-20 start dates. The earliest is the Level-2 catalog. |
| 2018-04-01 through 2019-12-31 | FIRMS download page includes NOAA-20. The attribute page does not. | Potentially incompatible for a FIRMS NOAA-20 series. Usable for `VJ114IMG`. | Download page versus attribute page. |
| 2020-01-01 through 2020-12-31 | Terra, Aqua, S-NPP, and NOAA-20 on every retrieved FIRMS coverage line that names NOAA-20. NOAA-21 has not started. | Usable for those four, with the processing-stream condition below. Before the final maneuver years named by LDOPE. | Attribute-page NOAA-20 start is 1 January 2020. Aqua's final IAM/DMU year is 2021 and Terra's is 2022. |
| 2021-01-01 through 2022-12-31 | Terra, Aqua, S-NPP, and NOAA-20. NOAA-21 Level-2 has not started; that start is 2023-02-10. | Potentially incompatible for MODIS diurnal and pixel geometry. | LDOPE: Aqua final inclination and drag maneuvers in 2021, Terra in 2022. |
| 2023-02-10 through 2023-02-28 | `VJ214IMG` has started. FIRMS download coverage has not. | Usable for the Level-2 swath. Unavailable on the FIRMS download line. | CMR start 2023-02-10. Download line starts 1 March 2023. |
| 2023-03-01 through 2024-01-16 | FIRMS download page includes NOAA-21. The VIIRS attribute page does not. | Potentially incompatible for a five-platform FIRMS set. Usable for `VJ214IMG` as a swath. | The two FIRMS pages. |
| 2024-01-17 through 2024-11-01, excluding the July 2024 S-NPP gaps | All five platforms appear on every retrieved FIRMS coverage line. | Usable for a five-platform FIRMS comparison only where the stream is explicit. Potentially incompatible with pre-2021 MODIS overpass timing. | Conservative FIRMS intersection. Late-2024 drift impacts are the LDOPE statement. July exceptions are the next rows. |
| 2024-07-09 21:42 UTC through 2024-07-16 17:42 UTC | S-NPP VIIRS Level 2 named in the LP DAAC geolocation alert. | Unavailable for that S-NPP product in the stated window. The other platforms are not declared down by that alert. | Coverage investigation, LP DAAC alert. |
| 2024-07-16 17:42 UTC through 2024-07-24 05:28 UTC | S-NPP rows exist in the local FIRMS CSV on the investigated side of each boundary. | Local S-NPP rows are present only where that investigation counted them. This timeline does not add rows. | Coverage investigation. |
| 2024-07-24 05:28 UTC through 18:22 UTC | S-NPP VIIRS, LP DAAC anomaly. | Unavailable for the named Level-2 product in that window. | LP DAAC alert. |
| 2024-07-24 18:22 UTC through 2024-07-29 15:24 UTC | Local S-NPP CSV has no rows for the full missing dates, and no retrieved LP DAAC sentence covers every hour. | Unresolved for the cause. The local CSV still has no rows. Rows are not filled. | Coverage investigation. |
| 2024-11 through 2026-11-02 13:00 UTC | Five platforms, inside the period LDOPE calls significantly affected for MODIS sampling. | Usable as a drift-era five-platform description. Potentially incompatible with a 2002–2020 MODIS diurnal baseline. | LDOPE `HC_MOD_26008`: significant impacts observed in late 2024; fire-product effects under investigation. |
| 2025-08-06 onward for operational MODIS processing | Input change from legacy NISE to NISE AMSR2. | Unresolved for the fire product. | LDOPE `TM_MOD_25218`. The note reports no downstream effect in products that do not directly ingest the cloud mask. It does not name MOD14 or MYD14. |
| 2026-03-26 20:00 UTC through 2026-03-27 19:25 UTC | Terra MODIS. | Unavailable for the granules LDOPE lists. | LDOPE `TM_MOD_26085`. This is one note, not a full 2026 gap list. |
| 2026-11-02 13:00 UTC | New FIRMS S-NPP active-fire data. | Unavailable after this instant. | Earthdata FIRMS transition note. |
| 2026-11-02, the calendar day, for Suomi NPP VIIRS science products | Earthdata says delivery ceased on this day. | Unavailable for new S-NPP VIIRS science products. The catalog widget still says Present. | Earthdata VNP14IMG page. |
| After 2026-11-02 | NOAA-20, NOAA-21, and MODIS are not given an end date by the pages above. | A four-platform continuation is a different design. It is not opened here. MODIS shutdown is described only as late 2026 or early 2027. | Earthdata MODIS-to-VIIRS transition. |

## Collection boundaries that cut across the timeline

| Change | When the retrieved document places it | Consequence for a historical series |
| --- | --- | --- |
| MODIS Collection 5 to Collection 6 | Collection 6 Tier-1 production, including active fire, commenced in February 2015. The guide lists fourteen fire-product changes, including ocean processing, FRP method, and the `MCD14ML` type and day/night fields. | Collection 5 is an earlier algorithm. It is not appended to a Collection 6.1 series. |
| MODIS Collection 6 to 6.1 | Mini-reprocessing began in 2018 and included land products in late 2020. Collection 6 forward land processing stopped on 15 February 2023. | Order Collection 6.1. The fire guide says Collection 6 and 6.1 may be intermixed and reports a 0.001% difference in a January 2020 fire-pixel total. This strategy still does not mix the collection identifiers. |
| VIIRS Collection 1 to Collection 2 | Collection 2 uses Collection 2 Level-1B, which the guide says removes the spurious bad scans of the earlier inputs, and it uses new quality flags to remove spurious detections that were common in Collection 1. | Order Collection 2. Do not append Collection 1. |
| VIIRS monthly `type` versions 1 and 2 | Corrected May 2025. Files reprocessed to version 3. | A monthly location file is version `03` if that product is used. The July FIRMS version cell `2` is not that `VV` field. |
| NRT, RT, and URT versus standard | Continuous. FIRMS replaces NRT with standard on a lag the readme calls about 3 months and the download page calls about 5 months. RT and URT are removed when NRT arrives or after 6 hours. | One series, one stream. The lag disagreement stays unresolved, so a manifest records the stream the provider names rather than a computed age. |

## Gaps named without a full interval

The FIRMS readme says MODIS data are missing from the end of June to the beginning of July 2001, that 2002 is missing some data throughout, that 2007 has some missing data from mid August, and that part of 21 April 2009 and all of 22 April 2009 are missing. It also says there might be erroneous data. Those phrases are not precise enough to draw a closed interval. A sample date that might fall inside "mid August 2007" stays on the calendar and is judged from the file that arrives. It is not replaced by searching for a busier day.

LDOPE lists further Terra losses, including 2025/154, 2025/132, 2025/085, 2024/205, and a rolling ephemeris note. The retrieved page is not a complete catalog. An order checks the current known-issue page again. A listed granule gap removes that granule. It does not become a zero-fire day, and it does not get filled from another satellite.

## What "overlap" means here

A usable overlap is a UTC interval where each required product's own document includes the interval, the collections match the series, and no stated outage covers it.

It is not any of the following:

- The same fire seen twice.
- The same pixel.
- The same confidence number.
- The same FRP algorithm.
- A license to copy NOAA-20 or NOAA-21 into an S-NPP gap.
- A license to treat the 375 m and 750 m VIIRS products as one record.
- A license to treat the five-platform window of 2024–2026 as orbitally equivalent to Terra and Aqua before the final maneuvers.

The July 2024 candidate-pair report already measured NOAA-20 and NOAA-21 detection times inside 5 km and 60 minutes at a median bin of 50–51 minutes. That is a statement about archived July rows. The FIRMS attribute page's "about 50 minutes" is a statement about the orbits. The two sentences are consistent in direction and are not the same measurement. Neither one sets `same_fire`.
