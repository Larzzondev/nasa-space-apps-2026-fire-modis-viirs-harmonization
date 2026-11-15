# VIIRS thermal field mapping, 7 July 2024

Created 2026-11-15T16:00:00Z. Finished 2026-11-15T16:00:23Z.

The MAP_KEY is not in this file. Archive columns were not renamed. No scale was applied. No harmonization coefficient was calculated. `same_fire` is `not_assessed`. The processing stream of each local archive stays `unresolved`.

## Documented meaning

Retrieved pages are listed with hashes in the JSON report. The sentences below are phrases found in those responses.

The user's guide text layer was read at `2026-11-15T16:06:44Z` from SHA-256 `fb957afb6e465cb312fb8229a2b6e424c489344bb09e76a7baee80a248d1ccb7`. It matches the comparison-pass hash: `true`. Area requests were not repeated for that reading.

FIRMS VIIRS attribute page: `https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html` HTTP `200` on `2026-11-15T16:06:41Z`.
I-4 Kelvin statement present: `true`. Web-service alias `Bright_ti4 / Brightness (in web services)` present: `true`.
I-5 Kelvin statement present: `true`. Web-service alias `Bright_ti5 / Brightness_2 (in web services)` present: `true`.
I-4 wavelength phrase on that page: `3.55-3.93 µm`. `bright_t31` occurs on that page: `false`. `bright_t31` is named beside I-5: `false`. A scale factor is mentioned: `false`.

FIRMS MODIS attribute page: `https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html` HTTP `200`. `bright_t31` present: `true`. Channel 31 Kelvin statement present: `true`. That MODIS sentence is not applied to the VIIRS archive.

Earthdata active-fire attribute page: `https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs` HTTP `200`. I-4 Kelvin statement present: `true`. I-5 Kelvin statement present: `true`. Web-service aliases present: `true` and `true`. `bright_t31` named beside I-5: `false`.

Collection 2 375 m user's guide, Version 1.2, June 2025: `https://www.earthdata.nasa.gov/s3fs-public/2025-06/VIIRS_C2_AF-375m_User_Guide_1.2.pdf` HTTP `200`, `1602644` bytes, SHA-256 `fb957afb6e465cb312fb8229a2b6e424c489344bb09e76a7baee80a248d1ccb7`.
Level-2 `FP_T4` is I4 brightness temperature in kelvin: `true`. `FP_T5` is I5 brightness temperature in kelvin: `true`.
Monthly location fields `T4` and `T5` are I4 and I5 brightness temperature in K: `true` and `true`.
The guide calls I5 long-wave infrared: `true`. Nominal I4 saturation 367 K: `true`. The guide names the FIRMS archive columns: `false`. A scale factor is mentioned: `false`.

The user's guide monthly file uses `T4` and `T5`. The Level-2 swath uses `FP_T4` and `FP_T5`. The FIRMS archive CSV uses `brightness` and `bright_t31`. The area API CSV uses `bright_ti4` and `bright_ti5`. The attribute page's web-service names are `Brightness` and `Brightness_2`. These are separate names. This comparison does not treat them as one schema.

Level-2 catalog pages were retrieved for the scale-factor cells of `FP_T4` and `FP_T5`. Those cells belong to the swath product. They are not a FIRMS CSV scale.

- `https://www.earthdata.nasa.gov/data/catalog/lpcloud-vj114img-002` HTTP `200` bytes `254726`.
  `FP_T4`: I04 Brightness Temperature of Fire Pixel, valid range ~ 208 to 367. Units `Kelvin`, type `float32`, fill `N/A`, range `208 to 367`, scale factor `N/A`, offset `N/A`.
  `FP_T5`: I05 Brightness Temperature of Fire Pixel, valid range ~ 205 to 380. Units `Kelvin`, type `float32`, fill `N/A`, range `205 to 380`, scale factor `N/A`, offset `N/A`.
- `https://www.earthdata.nasa.gov/data/catalog/lpcloud-vj214img-002` HTTP `200` bytes `244301`.
  `FP_T4`: I04 Brightness Temperature of Fire Pixel. Units `Kelvin`, type `float32`, fill `N/A`, range `208 to 367`, scale factor `N/A`, offset `N/A`.
  `FP_T5`: I05 Brightness Temperature of Fire Pixel. Units `Kelvin`, type `float32`, fill `N/A`, range `205 to 380`, scale factor `N/A`, offset `N/A`.

## Comparison

Candidate pairs are `brightness` with `bright_ti4`, and `bright_t31` with `bright_ti5`. Rows are paired on the shared non-thermal columns. Difference is API minus archive, in the stored numeric units. Quantiles use Hyndman-Fan type 7. Crossed pairs are a control and are not a mapping.

Authenticated area requests sent: `true`.
Reason the requests were or were not sent: The attribute page defines bright_ti4 and bright_ti5 as Kelvin brightness temperatures. The two area requests were sent.

### NOAA-20

File `fire_archive_J1V-C2_850119.csv` SHA-256 before `b2febdffbf7ad9dcaf7066ed913b8e0028eebff94bb79a9dd4e2e346dd4f9907`. SHA-256 after `b2febdffbf7ad9dcaf7066ed913b8e0028eebff94bb79a9dd4e2e346dd4f9907`. Unchanged: `true`.
API source label recorded beside the file: `VIIRS_NOAA20_SP`. That label is not a processing-stream assignment.
Thermal relationship: `same_observations_field_equivalence_unresolved`.
Processing stream: `unresolved`. Product equivalence: `not_assessed`. `same_fire`: `not_assessed`.

Area request sent `true` HTTP `200` rows `82372` bytes `6675249` seconds `3.038315` retries `0`.
Archive rows `82372`. API rows `82372`. Aligned unique rows `82372`. Ambiguous rows whose joint thermal multiset matched `0`. Unaligned archive rows `0`. Unaligned API rows `0`.
`brightness` versus `bright_ti4`: name documented `true`, exact numeric equality `82372`, raw string equality `82372`, numeric pairs `82372`, maximum absolute difference `0`, mean absolute difference `0`, mean signed difference `0`, offset `none_observed`, missing archive/api/both `0`/`0`/`0`, invalid archive/api `0`/`0`.
Absolute-difference quantiles: `{'0': '0', '0.25': '0', '0.5': '0', '0.75': '0', '0.95': '0', '0.99': '0', '1': '0'}`.
`bright_t31` versus `bright_ti5`: name documented `false`, exact numeric equality `82372`, raw string equality `82372`, numeric pairs `82372`, maximum absolute difference `0`, mean absolute difference `0`, mean signed difference `0`, offset `none_observed`, missing archive/api/both `0`/`0`/`0`, invalid archive/api `0`/`0`.
Absolute-difference quantiles: `{'0': '0', '0.25': '0', '0.5': '0', '0.75': '0', '0.95': '0', '0.99': '0', '1': '0'}`.
Crossed control `brightness` versus `bright_ti5`: exact numeric equality `0` of `82372` numeric pairs. This control is not a field mapping.
Crossed control `bright_t31` versus `bright_ti4`: exact numeric equality `0` of `82372` numeric pairs. This control is not a field mapping.

### NOAA-21

File `fire_archive_J2V-C2_850120.csv` SHA-256 before `5be3094edf2dc4461b9eadc82c97657b730550aaa92000d88fc2b1fbe4b46917`. SHA-256 after `5be3094edf2dc4461b9eadc82c97657b730550aaa92000d88fc2b1fbe4b46917`. Unchanged: `true`.
API source label recorded beside the file: `VIIRS_NOAA21_SP`. That label is not a processing-stream assignment.
Thermal relationship: `same_observations_field_equivalence_unresolved`.
Processing stream: `unresolved`. Product equivalence: `not_assessed`. `same_fire`: `not_assessed`.

Area request sent `true` HTTP `200` rows `87637` bytes `7093756` seconds `4.062924` retries `0`.
Archive rows `87637`. API rows `87637`. Aligned unique rows `87637`. Ambiguous rows whose joint thermal multiset matched `0`. Unaligned archive rows `0`. Unaligned API rows `0`.
`brightness` versus `bright_ti4`: name documented `true`, exact numeric equality `87637`, raw string equality `87637`, numeric pairs `87637`, maximum absolute difference `0`, mean absolute difference `0`, mean signed difference `0`, offset `none_observed`, missing archive/api/both `0`/`0`/`0`, invalid archive/api `0`/`0`.
Absolute-difference quantiles: `{'0': '0', '0.25': '0', '0.5': '0', '0.75': '0', '0.95': '0', '0.99': '0', '1': '0'}`.
`bright_t31` versus `bright_ti5`: name documented `false`, exact numeric equality `87637`, raw string equality `87637`, numeric pairs `87637`, maximum absolute difference `0`, mean absolute difference `0`, mean signed difference `0`, offset `none_observed`, missing archive/api/both `0`/`0`/`0`, invalid archive/api `0`/`0`.
Absolute-difference quantiles: `{'0': '0', '0.25': '0', '0.5': '0', '0.75': '0', '0.95': '0', '0.99': '0', '1': '0'}`.
Crossed control `brightness` versus `bright_ti5`: exact numeric equality `1` of `87637` numeric pairs. This control is not a field mapping.
Crossed control `bright_t31` versus `bright_ti4`: exact numeric equality `1` of `87637` numeric pairs. This control is not a field mapping.

## Checksums

- `fire_archive_J1V-C2_850320.csv` SHA-256 `9a192db30e307c257955047ca1177e3f2f463b8c8cdfda7b28ceac6b3aa92bd5` matches the ingestion manifest: `true`.
- `fire_archive_J2V-C2_850321.csv` SHA-256 `c86e46d4ca730eea6db448ff928126ddc6b44ba4c4d11dfbc3a2d999f4937007` matches the ingestion manifest: `true`.

## Timing

Wall clock: 22.959564 seconds.
CPU seconds: 8.75.
Peak working set: 362438656 bytes.
Authenticated data-request retries: 0.
Cancellations: 0.
Documentation bytes: 2289740. Area-response bytes: 13769005.

Pytest exit code 0. Passed 165. Failed 0. Pytest reported 46.35 seconds. The command stopwatch was 54.76 seconds. Interpreter: `C:\Users\Administrator\Documents\Personal\Code\NASA Hackathon - Space Apps Challenge 2026\nasa-fire-harmonization\backend\.venv\Scripts\python.exe`.

Original day files and monthly files were read and hashed. They were not rewritten.
