# FIRMS archive discovery and validation

This backend reads the four NASA FIRMS CSV extracts in `data/raw` and checks them against the columns and codes those files actually contain. It can also summarize that one day of detections. It does not calculate a harmonization factor, and it does not serve the frontend.

The CSV extracts are gitignored. `data/raw/README.md` lists the paths the current code expects. Download instructions and the public-repository rules are in the root `README.md`.

## Archives

| Source | File | Rows | Acquisition date |
| --- | --- | --- | --- |
| MODIS | `data/raw/modis/fire_archive_M-C61_850118.csv` | 20,410 | 2024-07-07 |
| VIIRS NOAA-20 | `data/raw/viirs_noaa20/fire_archive_J1V-C2_850119.csv` | 82,372 | 2024-07-07 |
| VIIRS NOAA-21 | `data/raw/viirs_noaa21/fire_archive_J2V-C2_850120.csv` | 87,637 | 2024-07-07 |
| VIIRS S-NPP | `data/raw/viirs_snpp/fire_archive_SV-C2_850121.csv` | 86,840 | 2024-07-07 |

All four files use the same header:

`latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight,type`

The VIIRS extracts use those column names as stored. They are not renamed to `bright_ti4` or `bright_ti5`. The S-NPP file stores `instrument` as `SNPP` and `satellite` as `SNPP`. MODIS confidence is an integer from 0 through 100. VIIRS confidence is `l`, `n`, or `h`.

## Setup

From this directory, with Python 3.11 or newer:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

On macOS or Linux, use `.venv/bin/python` instead of `.venv\Scripts\python`.

## Run

```bash
.venv\Scripts\python -m fire_data discover
.venv\Scripts\python -m fire_data validate
.venv\Scripts\python -m fire_data eda
.venv\Scripts\python -m pytest
```

`discover` writes `reports/discovery.json`. `validate` exits with status 1 when an archive fails the observed contract.

`eda` writes `reports/eda_report.md`, `reports/eda_summary.json`, and `reports/figures/`. The summary is a one-day global description of 2024-07-07. Detection counts are archive rows, not unique fires. MODIS confidence and VIIRS confidence stay on their own scales. Extreme FRP values are retained. The default spatial-overlap radii are 375 m, 1,000 m, and 5,000 m:

```bash
.venv\Scripts\python -m fire_data eda --thresholds-m 375,1000,5000
```

`investigate` writes `reports/anomaly_investigation.md` and `reports/anomaly_summary.json`. It examines the stored VIIRS brightness value 367 K and the Aqua FRP rows 7956.3 and 7328.1. It does not change the exploratory report or the raw archives.

```bash
.venv\Scripts\python -m fire_data.investigate
```

`temporal` writes `reports/temporal_validation.md`, `reports/temporal_summary.json`, and the CSV files in `reports/temporal/`. It records provenance and the acquisition dates that are actually present. It does not assign standard or near-real-time processing from a filename, and it does not change the earlier reports or the raw archives.

```bash
.venv\Scripts\python -m fire_data.temporal
```

`readiness` writes `reports/data_readiness.md` and `reports/data_readiness.json`. It reviews provenance, the proximity matcher, and the specification for a later 30-date bundle. It does not assign a processing stream from a filename or a version value, and it does not change the earlier reports or the raw archives.

```bash
.venv\Scripts\python -m fire_data.readiness
```

`ingest` reads four unmodified FIRMS ZIP archives from `data/incoming/2024-07/` and extracts one CSV into each subdirectory of `data/raw/monthly_2024_07/`. It does not write into the 7 July 2024 sample directories, does not overwrite an existing extract, and does not treat a missing date as zero detections. A dry run validates the archives and writes nothing.

Copy the four ZIPs into `data/incoming/2024-07/` first. From this directory:

```bash
.venv\Scripts\python -m fire_data.ingest --dry-run
.venv\Scripts\python -m fire_data.ingest
```

The second command writes `reports/ingestion_2024_07.json` only after the ZIPs are present. The incoming ZIPs and the extracted CSVs stay gitignored.

`within_sensor_analysis` reads those July extracts and writes `reports/within_sensor_analysis_2024_07.md`, `reports/within_sensor_analysis_2024_07.json`, and `reports/figures/within_sensor_2024_07/`. It measures nearest neighbors, neighborhood counts, and DBSCAN components inside each satellite. Those results are not confirmed fires, `same_fire` stays `not_assessed`, and a date with no rows is left null. It does not calculate a harmonization coefficient or train a model.

```bash
.venv\Scripts\python -m fire_data.within_sensor_analysis
```
