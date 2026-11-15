# Milestone 13 timing

Started: 2026-11-15T15:23:03Z
Finished: 2026-11-15T15:23:08Z

The MAP_KEY is not in this file.

## Python

Interpreter: `C:\Users\Administrator\Documents\Personal\Code\NASA Hackathon - Space Apps Challenge 2026\nasa-fire-harmonization\backend\.venv\Scripts\python.exe`.
Version: `3.12.14`.
Windows Store stub: `false`.

## Accounting

Wall clock: 4.934643 seconds.
CPU seconds: 1.03125.
Peak working set: 134795264 bytes.
Authenticated data requests sent: `false`.
Retries on data requests: 0.

## Documentation fetches

| URL | HTTP | Seconds | Bytes | Retries |
| --- | ---: | ---: | ---: | ---: |
| https://firms.modaps.eosdis.nasa.gov/api/ | 200 | 0.952886 | 5966 | 0 |
| https://firms.modaps.eosdis.nasa.gov/api/area/ | 200 | 0.717009 | 25596 | 0 |
| https://firms.modaps.eosdis.nasa.gov/api/data_availability/ | 200 | 0.8462 | 17834 | 0 |
| https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html | 200 | 1.375614 | 369354 | 0 |

## Data requests

| Source | Kind | Sent | HTTP | Seconds | Bytes | Rows |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| VIIRS_NOAA20_SP | area | false | None | None | None | None |
| VIIRS_NOAA21_SP | area | false | None | None | None | None |

## pytest

Exit code 0. 147 passed, 0 failed. Pytest reported 45.78 seconds. The command stopwatch, including process startup, was 46.17 seconds. This run is the confirmation against the final tree.

Interpreter: `backend/.venv/Scripts/python.exe`, Python 3.12.14. Windows Store stub: false.

Installed in that environment: pytest 9.2.0, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2.

Milestone 12 invoked `py` and `python`. Those commands are Windows Store stubs and exited 9009 before pytest started. This run did not use them.

## Measured intervals

Provenance and documentation: 4.935 seconds. Pytest command: 46.17 seconds. Sum of those two stopwatches: 51.105 seconds. The editing interval between them was not instrumented and is not added as CPU time.

Authenticated data requests: 0. Retries on those requests: 0. Response bytes and row counts for the area API: none, because the requests were not opened.
