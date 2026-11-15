# Milestone 13 timing

Started: 2026-11-15T15:41:39Z
Finished: 2026-11-15T15:41:56Z

The MAP_KEY is not in this file.

## Python

Interpreter: `C:\Users\Administrator\Documents\Personal\Code\NASA Hackathon - Space Apps Challenge 2026\nasa-fire-harmonization\backend\.venv\Scripts\python.exe`.
Version: `3.12.14`.
Windows Store stub: `false`.

## Accounting

Wall clock: 17.626673 seconds.
CPU seconds: 4.359375.
Peak working set: 376532992 bytes.
Authenticated data requests sent: `true`.
Retries on data requests: 0.

## Documentation fetches

| URL | HTTP | Seconds | Bytes | Retries |
| --- | ---: | ---: | ---: | ---: |
| https://firms.modaps.eosdis.nasa.gov/api/ | 200 | 0.571008 | 5966 | 0 |
| https://firms.modaps.eosdis.nasa.gov/api/area/ | 200 | 0.633704 | 25596 | 0 |
| https://firms.modaps.eosdis.nasa.gov/api/data_availability/ | 200 | 0.640514 | 17834 | 0 |
| https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html | 200 | 0.894775 | 369354 | 0 |

## Data requests

| Source | Kind | Sent | HTTP | Seconds | Bytes | Rows |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| VIIRS_NOAA20_SP | data_availability | true | 200 | 0.671823 | 63 | None |
| VIIRS_NOAA20_SP | area | true | 200 | 4.2878 | 6675249 | 82372 |
| VIIRS_NOAA21_SP | data_availability | true | 200 | 0.555105 | 63 | None |
| VIIRS_NOAA21_SP | area | true | 200 | 4.925763 | 7093756 | 87637 |

## pytest

Exit code 0. 148 passed, 0 failed. Pytest reported 46.21 seconds. The command stopwatch was 46.62 seconds. Interpreter: `backend/.venv/Scripts/python.exe`.

Provenance and API requests: 17.627 seconds. Pytest: 46.62 seconds. Sum of those two stopwatches: 64.247 seconds. The gap between them was not instrumented. Data-request retries: 0.
