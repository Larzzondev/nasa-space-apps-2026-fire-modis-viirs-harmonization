# Acquisition plan

This plan describes how a later order would be made. No order was submitted on 2026-11-15. No MAP_KEY was read or written. No Earthdata session was opened. No granule and no multi-year archive was downloaded.

The July 2024 files stay in place:

| File | Measured bytes |
| --- | ---: |
| `backend/data/incoming/2024-07/DL_FIRE_M-C61_850319.zip` | 11,809,626 |
| `backend/data/incoming/2024-07/DL_FIRE_SV-C2_850322.zip` | 28,886,008 |
| `backend/data/incoming/2024-07/DL_FIRE_J1V-C2_850320.zip` | 51,356,014 |
| `backend/data/incoming/2024-07/DL_FIRE_J2V-C2_850321.zip` | 49,052,868 |
| `backend/data/raw/monthly_2024_07/modis/fire_archive_M-C61_850319.csv` | 54,196,122 |
| `backend/data/raw/monthly_2024_07/viirs_snpp/fire_archive_SV-C2_850322.csv` | 132,818,598 |
| `backend/data/raw/monthly_2024_07/viirs_noaa20/fire_archive_J1V-C2_850320.csv` | 235,770,840 |
| `backend/data/raw/monthly_2024_07/viirs_noaa21/fire_archive_J2V-C2_850321.csv` | 225,148,614 |

ZIP total: 141,104,516 bytes. CSV total: 647,934,174 bytes. A future order uses a new directory, `backend/data/incoming/historical/` for the provider ZIP and `backend/data/raw/historical/` for the extract. Those directories were not created in this milestone.

## Which archive answers which question

| Question | Archive | Why this one |
| --- | --- | --- |
| Extend the July FIRMS tables once a stream is named | FIRMS archive download, https://firms.modaps.eosdis.nasa.gov/download/ | Same table family as the July CSVs. Global or regional. Email delivery. |
| Prove the Level-2 swath exists for a date | CMR granule metadata, then LP DAAC or LAADS if a file is actually needed | CMR counts granules. It does not count fires. Opening a swath is a different product from the FIRMS CSV. |
| Standard monthly location files as the science team packages them | University of Maryland SFTP named in the user's guides | `MCD14ML` and `Vxx14IMGML`. Not confirmed to be the FIRMS CSV. This milestone did not connect. |
| Low-latency operations | LANCE / FIRMS NRT, including https://nrt4.modaps.eosdis.nasa.gov/archive/FIRMS/ | The scientific series does not mix this stream with standard files. The directory listing was read. The data files under it were not downloaded. |

The area API is a poor tool for this design. Its `DAY_RANGE` is 1 to 5, so a 21-day sample would be many calls, and it requires a MAP_KEY. The archive download page is the FIRMS path that matches a list of dates. The area API remains the path for a later one-day provenance check, because a keyed `VIIRS_NOAA20_SP` or `VIIRS_NOAA21_SP` response would be the first provider field that names a stream.

## Authentication

| Path | What the retrieved page requires | What this repository stores |
| --- | --- | --- |
| FIRMS archive download | An email address and a code emailed by the site, then a second email with the ZIP link. The retrieved HTML posts the address to `/api/auth/code/` and logs in through `/api/auth/login/download/email/`. | Nothing. The address and the code stay outside the repository. |
| FIRMS area, country, and data-availability APIs | A free MAP_KEY. The area page states the key is required because of server load. | Nothing. A future key goes in an untracked environment file. The country URL without a key returned HTTP 400 and the body `Invalid API call.` |
| LP DAAC and LAADS Level-2 orders | The product pages link to search and archive paths. This retrieval did not sign in. An Earthdata Login is the expected gate for those orders and was not tested. | No token. |
| University of Maryland SFTP | The user's guides publish a host and a shared login for the fire-location directories. | The password is not copied into this repository. The server was not contacted. |

## What can be ordered

FIRMS download-page coverage, retrieved 2026-11-15:

| Selection | Coverage line on that page |
| --- | --- |
| MODIS Collection 6.1 | 1 November 2000 – present |
| VIIRS S-NPP 375 m | 20 January 2012 – 2 November 2026 |
| VIIRS NOAA-20 375 m | 1 April 2018 – present |
| VIIRS NOAA-21 375 m | 1 March 2023 – present |

The page says near-real-time data are replaced by standard science-quality data as they become available, with approximately a 5 month lag. The readme inside the same service says approximately 3 months, and it says standard-quality data are not yet available from FIRMS for NOAA-20 and NOAA-21. An order for those two sensors records the page the operator used and keeps the `Readme.txt` that arrives in the ZIP. Until that readme, or an API source code stored in the manifest, names the stream, the new file stays `processing_level: unresolved` as well.

The attribute pages give different coverage lines: Aqua from 3 July 2002, Terra from 1 November 2000, S-NPP from 20 January 2012 through 2 November 2026, NOAA-20 from 1 January 2020, NOAA-21 from 17 January 2024. The sampling strategy uses the intersection, not the earliest advertisement.

Level-2 orders, if a later milestone needs the fire mask, use these short names and collections only:

| Short name | Collection | Archive |
| --- | --- | --- |
| `MOD14`, `MYD14` | `061` | LAADS ArchiveSet 61 and LP DAAC |
| `VNP14IMG`, `VJ114IMG`, `VJ214IMG` | `002` | LAADS ArchiveSet 5200 and LP DAAC |

`MOD14` NRT `6.1NRT` and `MYD14` NRT `6.1NRT` are separate CMR collections beginning 2021-02-07. They are not the historical standard order.

## Request limits

| Interface | Limit stated on the retrieved page |
| --- | --- |
| Area API `DAY_RANGE` | 1 through 5 days. |
| Area API area | A bounding box or the token `world`, which the page defines as `-180,-90,180,90`. Hemisphere names are rejected. |
| MAP_KEY | 5,000 transactions per 10-minute interval. A larger transaction may count as more than one request. The page's example is a 7-day request. Increases are by request to FIRMS, not by retrying. |
| Archive download page | No numeric cap was stated in the HTML retrieved on 2026-11-15. The page says the request is processed and an email follows. A cap is not invented here. |
| CMR | Used only as a collection search with `page_size=20`. No download throttle was encountered. Granule searches are a later milestone. |

A global historical pull through the area API would fight the 5-day limit and the transaction budget. It is not the design.

## File sizes that were measured

2024-07-07 global CSVs already on disk:

| File | Bytes |
| --- | ---: |
| `fire_archive_M-C61_850118.csv` | 1,635,095 |
| `fire_archive_SV-C2_850121.csv` | 7,050,277 |
| `fire_archive_J1V-C2_850119.csv` | 6,691,837 |
| `fire_archive_J2V-C2_850120.csv` | 7,113,989 |
| Sum | 22,491,198 |

The MODIS user's guide says an `MCD14ML` monthly file typically has about 200,000 to 500,000 lines. The July 2024 MODIS FIRMS file has 676,636 data rows. July is one month. It is not used as a typical month, and the guide's line count is not a FIRMS byte count. S-NPP's July file is an incomplete month because of the known gaps, so its 132,818,598 bytes are a lower figure for that sensor than a complete July would have been. How much lower is not known, because the missing intervals were not reconstructed.

### Planning ceiling, not a measurement

If every future global day had the same CSV bytes as 2024-07-07, which no document claims:

| Planned set | Days | Sensors | Ceiling at the 2024-07-07 byte sizes |
| --- | ---: | --- | ---: |
| Five-platform sample | 21 | all four FIRMS files | 21 × 22,491,198 = 472,315,158 bytes |
| MODIS continuity, 2003, 2007, 2011 | 24 | MODIS file only | 24 × 1,635,095 = 39,242,280 bytes |
| MODIS plus S-NPP, 2013, 2015, 2017 | 24 | MODIS and S-NPP files | 24 × (1,635,095 + 7,050,277) = 208,448,928 bytes |
| Four-platform year 2020 | 8 | MODIS, S-NPP, NOAA-20 | 8 × (1,635,095 + 7,050,277 + 6,691,837) = 123,017,672 bytes |

Sum of those ceilings: 843,024,038 bytes, about 0.79 GiB of CSV, before ZIP overhead and before a second copy of the ZIP. The 2020 and 2013–2017 rows reuse a 2024 S-NPP and NOAA-20 day. That is a storage ceiling for disk planning. It is not an expected fire-season volume.

Level-2 swath volumes were not measured. A day of `VNP14IMG` in the July coverage investigation contained on the order of 241 granules when the day was complete. Granule bytes were not read. A swath order is a separate budget and is not part of this sample.

The MODIS guide warns that a fire-location file has no cloud or missing-data layer, and that time steps shorter than about eight days carry large sampling bias if they are used as a gridded time series. This plan orders full UTC dates and does not convert them into a daily climate grid.

## Metadata the manifest must hold before analysis

For each ZIP and each extracted CSV:

- provider filename and request id
- product code (`M-C61`, `SV-C2`, `J1V-C2`, `J2V-C2`) or Level-2 short name
- processing stream, copied from the enclosed readme or from the API source code, or the literal `unresolved`
- collection, stored separately from the stream
- satellite and instrument values as stored, not as renamed
- area and the UTC date list requested
- projection statement from the provider readme
- production or email time
- SHA-256 of the ZIP before extraction and SHA-256 of the CSV after extraction
- source URL and retrieval time
- HTTP or email outcome

The FIRMS readme does not mention a provider checksum. None is invented. The local SHA-256 is the integrity check. Recompute it before analysis and stop if it differs.

The enclosed `Readme.txt` is kept beside the ZIP. It is the document that either names the stream or, for NOAA-20 and NOAA-21, may continue to say standard data are unavailable.

## Retry and failure

| Outcome | What is kept | What is not done |
| --- | --- | --- |
| Network or HTTP failure | The status, the URL, the time, and the attempt count. One retry is enough to separate a blip from an outage. Further retries wait for a person. | A CSV is not created to represent the failure. |
| Email order with no link | The request time and the product list. | Another sensor is not substituted. |
| ZIP that fails to open, or a hash that changes | The damaged bytes in a rejected folder, or their deletion recorded in the manifest. | The partial CSV is not analyzed. |
| Header-only CSV | The file. The readme says this is a request that found no fire points. | Rows are not imputed. The date remains a delivered empty file, which is different from a missing file. |
| A platform absent from an order that asked for five | The order is incomplete. | The date does not enter the five-platform set. |
| A known outage | The alert citation. | Detections are not copied from NOAA-20, NOAA-21, Terra, or Aqua. |

The country endpoint's HTTP 400 in this milestone is an example of the first row. It was retried once, failed again, and was not turned into a dataset.

## Computational expectation

The July 2024 experiment batch read 7,985,467 rows and 647,934,174 bytes. Experiment B's measured wall time on that full table was 29.243 seconds, with a peak working set of 505,827,328 bytes, as recorded in `milestone_11_timing.md`. That measurement is not rescaled into a prediction for 21 unseen days. Row counts for the sample dates are unknown until the files exist. Disk and memory at the time of this plan are in the milestone 12 timing report. They describe the machine that wrote the plan, not a cluster that will process the archive.

## What remains manual

The first future acquisition that can move NOAA-20 and NOAA-21 out of `unresolved` is a single-day comparison, not this sample. It would request `VIIRS_NOAA20_SP` and `VIIRS_NOAA21_SP` for 2024-07-07, or an archive-download ZIP whose enclosed readme names a standard short name, and it would write the result beside the existing July file. The existing file would not be replaced. If the provider still withholds a stream name, the sample in `VALIDATION_SAMPLING_STRATEGY.md` waits.
