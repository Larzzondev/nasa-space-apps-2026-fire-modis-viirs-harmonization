# FIRMS area API provenance, 7 July 2024

Created 2026-11-15T15:23:03Z.

## Result

Authenticated FIRMS requests were not sent.

Processing stream of the local NOAA-20 and NOAA-21 archive CSVs: `unresolved`.
`same_fire` is `not_assessed`. Product equivalence is `not_assessed`.
No harmonization coefficient was calculated. No missing observation was filled.

## Configuration required before a keyed request

`FIRMS_MAP_KEY` was absent from the process environment and from `backend/.env`.
The file did not exist at the time of this run (`env_file_exists` is false in the JSON).
Create `backend/.env` with one line, `FIRMS_MAP_KEY=<MAP_KEY issued by FIRMS>`. The value is the MAP_KEY issued at https://firms.modaps.eosdis.nasa.gov/api/map_key.
`MAP_KEY` is also read. The process environment takes precedence over the file.
The file is covered by the repository gitignore. It must not be committed. The client keeps the value out of reports, exception text, and stored URLs.

## Official API statements used

Area page: https://firms.modaps.eosdis.nasa.gov/api/area/
Data-availability page: https://firms.modaps.eosdis.nasa.gov/api/data_availability/
API index: https://firms.modaps.eosdis.nasa.gov/api/
API code examples: https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html

Area template present on the retrieved area page: `true`. Template: `/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]/[DATE]`.
Historical date syntax on that page: `YYYY-MM-DD`. The dated form returns that date through date plus day range minus one.
DAY_RANGE text: `1 .. 5`.
AREA_COORDINATES is `west,south,east,north` or the token `world`, defined on the page as `-180,-90,180,90`. Hemisphere names are rejected by the page. The maximum boundary is `-180,-90,180,90`.
Output format named by the area template and the API index: `csv`.
Transaction limit text found: `5000 transactions` per 10-minute interval. The page says a larger transaction may count as more than one request and gives a 7-day request as the example.
Target source identifiers present on the area page: VIIRS_NOAA20_SP, VIIRS_NOAA21_SP.
The area page labels `VIIRS_NOAA20_SP` as VIIRS NOAA-20 Standard Processing and `VIIRS_NOAA21_SP` as VIIRS NOAA-21 Standard Processing. Those are catalog labels.
The retrieved area page names a CSV query for a source code. It does not say that the response is the archive-download file fire_archive_J1V-C2 or fire_archive_J2V-C2. Equivalence stays not_assessed.

The code-examples page shows a `VIIRS_NOAA20_NRT` world request whose sample columns include `bright_ti4` and `bright_ti5` and whose sample version cell is `2.0NRT`. That example is not a 7 July 2024 standard-processing response, and its column names are not renamed onto the local header. The same page also contains `brightness` and `bright_t31` in a MODIS country example. Those strings are not a header returned for `VIIRS_NOAA20_SP` or `VIIRS_NOAA21_SP`.

## Local July 7 archive CSVs

The comparison files are the single-day archive downloads `fire_archive_J1V-C2_850119.csv` and `fire_archive_J2V-C2_850120.csv`. They were opened read-only. The original request area is not stored with them, so it is not claimed to have been reproduced.

| Platform | File | Rows | SHA-256 | Observed extent (west, south, east, north) | Dates |
| --- | --- | ---: | --- | --- | --- |
| NOAA-20 | `fire_archive_J1V-C2_850119.csv` | 82372 | `b2febdffbf7ad9dcaf7066ed913b8e0028eebff94bb79a9dd4e2e346dd4f9907` | `-175.0715,-50.57444,175.63397,71.25928` | 2024-07-07 |
| NOAA-21 | `fire_archive_J2V-C2_850120.csv` | 87637 | `5be3094edf2dc4461b9eadc82c97657b730550aaa92000d88fc2b1fbe4b46917` | `-137.77524,-44.13126,175.6368,71.42756` | 2024-07-07 |

Each extent is the axis-aligned range of stored points. It is the smallest rectangle that contains those points. It is not the archive order's area of interest. Longitude slices outside that range were not part of the planned request.

Planned requests, with the key still unsubstituted:

- `VIIRS_NOAA20_SP`: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/VIIRS_NOAA20_SP/-175.0715,-50.57444,175.63397,71.25928/1/2024-07-07` sent=`false`. FIRMS_MAP_KEY is not configured. The authenticated URL was not opened.
- `VIIRS_NOAA21_SP`: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/VIIRS_NOAA21_SP/-137.77524,-44.13126,175.6368,71.42756/1/2024-07-07` sent=`false`. FIRMS_MAP_KEY is not configured. The authenticated URL was not opened.

## Comparison

Not performed. No API table was returned, so record counts, coordinate differences, timestamp differences, duplicate observations, and missing observations were not calculated from an API response.
An empty response was not received and is not interpreted as zero fire activity.

## Monthly archive checksums

- `fire_archive_J1V-C2_850320.csv` SHA-256 `9a192db30e307c257955047ca1177e3f2f463b8c8cdfda7b28ceac6b3aa92bd5` matches the ingestion manifest: `true`.
- `fire_archive_J2V-C2_850321.csv` SHA-256 `c86e46d4ca730eea6db448ff928126ddc6b44ba4c4d11dfbc3a2d999f4937007` matches the ingestion manifest: `true`.

## What this run leaves unresolved

- An absent API response is not zero fire activity.
- The observed coordinate extent is not the original order polygon.
- A catalog label Standard Processing does not assign the local file's stream.
- A Level-2 swath identifier is not a FIRMS location CSV.
- same_fire remains not_assessed.

The download readme's statement that standard-quality NOAA-20 and NOAA-21 data are not yet available from FIRMS was not replaced by an API response. Both local files stay unresolved.
