# FIRMS area API provenance, 7 July 2024

Created 2026-11-15T15:41:39Z.

## Result

Authenticated FIRMS requests were sent. The processing stream of the local files remains a separate conclusion.

Processing stream of the local NOAA-20 and NOAA-21 archive CSVs: `unresolved`.
`same_fire` is `not_assessed`. Product equivalence is `not_assessed`.
No harmonization coefficient was calculated. No missing observation was filled.

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

The code-examples page shows a `VIIRS_NOAA20_NRT` world request whose sample columns include `bright_ti4` and `bright_ti5` and whose sample version cell is `2.0NRT`. That example is not a 7 July 2024 standard-processing response, and its column names are not renamed onto the local header.

## Local July 7 archive CSVs

The comparison files are the single-day archive downloads `fire_archive_J1V-C2_850119.csv` and `fire_archive_J2V-C2_850120.csv`. They were opened read-only. The original request area is not stored with them, so it is not claimed to have been reproduced.

| Platform | File | Rows | SHA-256 | Observed extent (west, south, east, north) | Dates |
| --- | --- | ---: | --- | --- | --- |
| NOAA-20 | `fire_archive_J1V-C2_850119.csv` | 82372 | `b2febdffbf7ad9dcaf7066ed913b8e0028eebff94bb79a9dd4e2e346dd4f9907` | `-175.0715,-50.57444,175.63397,71.25928` | 2024-07-07 |
| NOAA-21 | `fire_archive_J2V-C2_850120.csv` | 87637 | `5be3094edf2dc4461b9eadc82c97657b730550aaa92000d88fc2b1fbe4b46917` | `-137.77524,-44.13126,175.6368,71.42756` | 2024-07-07 |

Each extent is the axis-aligned range of stored points. It is the smallest rectangle that contains those points. It is not the archive order's area of interest. Longitude slices outside that range were not part of the planned request.

Requests. Stored URLs keep the key position unsubstituted:

- `VIIRS_NOAA20_SP` `data_availability` sent=`true` HTTP `200` rows `None` bytes `63` seconds `0.671823` retries `0`. HTTP 200
  Response prefix: `data_id,min_date,max_date VIIRS_NOAA20_SP,2018-04-01,2026-07-31`
  Availability rows: `[{'data_id': 'VIIRS_NOAA20_SP', 'min_date': '2018-04-01', 'max_date': '2026-07-31'}]`.
- `VIIRS_NOAA20_SP` `area` sent=`true` HTTP `200` rows `82372` bytes `6675249` seconds `4.2878` retries `0`. HTTP 200
  API field summary: `{'rows': 82372, 'columns': ['latitude', 'longitude', 'bright_ti4', 'scan', 'track', 'acq_date', 'acq_time', 'satellite', 'instrument', 'confidence', 'version', 'bright_ti5', 'frp', 'daynight', 'type'], 'satellite': {'N20': 82372}, 'instrument': {'VIIRS': 82372}, 'version': {'2': 82372}, 'confidence': {'n': 72727, 'h': 2708, 'l': 6937}, 'acq_date': {'2024-07-07': 82372}, 'daynight': {'D': 51168, 'N': 31204}}`.
- `VIIRS_NOAA21_SP` `data_availability` sent=`true` HTTP `200` rows `None` bytes `63` seconds `0.555105` retries `0`. HTTP 200
  Response prefix: `data_id,min_date,max_date VIIRS_NOAA21_SP,2023-03-01,2026-07-31`
  Availability rows: `[{'data_id': 'VIIRS_NOAA21_SP', 'min_date': '2023-03-01', 'max_date': '2026-07-31'}]`.
- `VIIRS_NOAA21_SP` `area` sent=`true` HTTP `200` rows `87637` bytes `7093756` seconds `4.925763` retries `0`. HTTP 200
  API field summary: `{'rows': 87637, 'columns': ['latitude', 'longitude', 'bright_ti4', 'scan', 'track', 'acq_date', 'acq_time', 'satellite', 'instrument', 'confidence', 'version', 'bright_ti5', 'frp', 'daynight', 'type'], 'satellite': {'N21': 87637}, 'instrument': {'VIIRS': 87637}, 'version': {'2': 87637}, 'confidence': {'n': 74845, 'h': 6879, 'l': 5913}, 'acq_date': {'2024-07-07': 87637}, 'daynight': {'N': 37857, 'D': 49780}}`.

## Comparison

### VIIRS_NOAA20_SP

Archive rows `82372`. API rows `82372`. Exact shared-field matches `82372`. Archive rows without an API identity `0`. API rows without an archive identity `0`. Same identity with changed shared values `0`.
Columns only in the archive: `['brightness', 'bright_t31']`. Columns only in the API table: `['bright_ti4', 'bright_ti5']`.
Field names were not renamed. Product equivalence remains `not_assessed`. `same_fire` remains `not_assessed`.

### VIIRS_NOAA21_SP

Archive rows `87637`. API rows `87637`. Exact shared-field matches `87637`. Archive rows without an API identity `0`. API rows without an archive identity `0`. Same identity with changed shared values `0`.
Columns only in the archive: `['brightness', 'bright_t31']`. Columns only in the API table: `['bright_ti4', 'bright_ti5']`.
Field names were not renamed. Product equivalence remains `not_assessed`. `same_fire` remains `not_assessed`.

## Monthly archive checksums

- `fire_archive_J1V-C2_850320.csv` SHA-256 `9a192db30e307c257955047ca1177e3f2f463b8c8cdfda7b28ceac6b3aa92bd5` matches the ingestion manifest: `true`.
- `fire_archive_J2V-C2_850321.csv` SHA-256 `c86e46d4ca730eea6db448ff928126ddc6b44ba4c4d11dfbc3a2d999f4937007` matches the ingestion manifest: `true`.

## What this run leaves unresolved

- An absent API response is not zero fire activity.
- The observed coordinate extent is not the original order polygon.
- A catalog label Standard Processing does not assign the local file's stream.
- A Level-2 swath identifier is not a FIRMS location CSV.
- same_fire remains not_assessed.

The local NOAA-20 and NOAA-21 archive streams stay `unresolved`. A catalog label, an API version cell, or a row overlap does not by itself name the stream of the archive file.
