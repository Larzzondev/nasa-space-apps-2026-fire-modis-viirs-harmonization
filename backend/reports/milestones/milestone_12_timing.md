# Milestone 12 timing

Instrumented start: 2026-11-15T14:48:01.7080734Z
Fetch script completed: 2026-11-15T14:48:50.6172985Z
Validation started: 2026-11-15T14:56:42.4943008Z
Completed: 2026-11-15T14:56:44.6755954Z

Repository reading before the instrumented start was not timed. Durations below are measured. A null CPU or memory figure was not measured and is not stored as zero.

## Host

Measured at validation, from Win32_ComputerSystem, Win32_OperatingSystem, Win32_Processor, and the C: drive:

- Physical cores: 12
- Logical processors: 20
- Sockets: 1
- Physical memory: 34164097024 bytes
- Free physical memory: 14423945216 bytes
- Free disk: 286602977280 bytes

## Commands

| Command | Result | Wall (s) | What was measured |
| --- | --- | ---: | --- |
| nasa_document_fetch | exit 0 | 48.909 | 46 HTTP requests. Sum of per-request stopwatches: 43.148 s. |
| document_checks | pass | 0.029 | The five strategy files exist and contain the required provenance sentences. |
| july_csv_sha256 | pass | 0.657 | SHA-256 of the four July 2024 CSVs matched the shared data contract. |
| pytest_historical_strategy | not run | 0.221 | The Windows Python launcher exited 9009. pytest did not start. |

Total wall clock from the first timed retrieval to the end of validation: 522.968 seconds.
Active execution, the sum of the four non-overlapping measured intervals: 44.055 seconds.
Document composition between the fetch and the validation was 471.877 seconds of wall clock. CPU during that interval was not measured.
Scripted retry sleep: 2.0 seconds, two one-second waits inside the fetch. Those waits are included in the 48.909 second fetch, not added again.
Retries: 2. Cancellations: 0.

The 4.761 second difference between the fetch wall and the sum of request stopwatches is script overhead plus the two one-second sleeps. It is not a fifth science task.

## Retrieval failures

Both attempts were kept. Neither failure was turned into a data file.

| Request | HTTP | Attempts | Body |
| --- | ---: | ---: | --- |
| `https://firms.modaps.eosdis.nasa.gov/api/country/` | 400 | 2 | `Invalid API call.` The URL was called without a MAP_KEY. |
| `https://www.earthdata.nasa.gov/data/catalog/lpcloud-mcd14ml-061` | 404 | 2 | An Earthdata page at that guessed path was not found. CMR `short_name=MCD14ML` also returned zero hits. The FIRMS readme and the MODIS user's guide still name MCD14ML. |

## July integrity

| CSV | Bytes | SHA-256 matches contract |
| --- | ---: | --- |
| `fire_archive_M-C61_850319.csv` | 54196122 | true |
| `fire_archive_SV-C2_850322.csv` | 132818598 | true |
| `fire_archive_J1V-C2_850320.csv` | 235770840 | true |
| `fire_archive_J2V-C2_850321.csv` | 225148614 | true |

The hash command read the files and did not write them.

## What was not measured

- CPU seconds and peak working set for the HTTP client.
- Wall clock of the repository reading that happened before 2026-11-15T14:48:01Z.
- CPU during the 471.877 second composition interval.
- A pytest result. `backend/tests/test_historical_strategy.py` is in the tree. The machine's `py` and `python` commands are the Windows Store stub and returned exit 9009.

Per-request status, byte count, and SHA-256 are in `milestone_12_timing.json`.
