# NASA Space Apps 2026 - MODIS and VIIRS Fire Harmonization

One Planet. Multiple Sensors. One Consistent Fire History.

This repository is the NASA Space Apps Challenge 2026 project for harmonizing MODIS and VIIRS active-fire hot spots. The scientific goal is a fire record that can be compared across Terra, Aqua, Suomi-NPP, NOAA-20, and NOAA-21 without treating every detection as a separate fire or treating every nearby pair as the same fire.

The FireLens demo is the interactive site. Run `npm install` and `npm run dev`, then open the local URL. It has four screens: a globe, a July 2024 historical explorer, a MODIS and VIIRS comparison, and a conceptual propagation sketch.

The globe draws a bounded synthetic sample labeled DEMO DATA. It is not the FIRMS archive. Historical counts, FRP summaries, confidence, and day/night figures are the July 2024 delivered-row statistics already recorded in `backend/reports/`. A date with no delivered rows, or a month with no loaded archive, is left blank. It is not shown as zero fires. The propagation screen is a demonstration simulation, not a validated forecast, and no forecast model is trained or deployed.

The scientific work so far is a reproducible audit of the July 2024 FIRMS extracts, centered on 2024-07-07. A harmonization algorithm and a predictive model are not implemented.

## 1. Project overview

MODIS and VIIRS have both mapped active fires for years. They do not measure the same pixel, use the same confidence scale, or publish one shared processing label in the FIRMS tables used here. Counts from one sensor cannot be subtracted from counts from another and called a change in fire activity.

This project separates three ideas that are often collapsed:

- A **detection** is one archived row: one sensor, one pixel, one acquisition time.
- A **proximity match** is two detections that fall inside a chosen distance and time window. It is evidence of nearness, not identity.
- A **physical fire** is a real burning event. Identifying one requires more than a pair of nearby rows, and this repository does not make that identification.

Fire Radiative Power (FRP) is the pixel-integrated radiant power of a detected hot spot, stored in megawatts (MW). It is the measurement a later calibration could compare. No calibration coefficient is calculated in this repository.

## 2. The scientific problem

A consistent multi-sensor fire history has to answer a narrow question: when two satellites report hot spots in the same region, how much of the difference is fire activity, and how much is the instrument, the pixel footprint, the overpass time, or the processing stream?

The current extracts cannot answer that across time. They contain one acquisition date. They also omit the processing-stream field needed to know whether a file is near-real-time or standard quality. The project therefore starts by measuring what the files actually contain, and by writing down what is still unknown, before any sensor is rescaled to another.

## 3. Why MODIS and VIIRS observations cannot be directly compared

The five satellites in this project are not interchangeable.

| Platform | Sensor | Role in these files |
| --- | --- | --- |
| Terra | MODIS | Morning and night observations. Stored confidence is an integer from 0 to 100. |
| Aqua | MODIS | Early-afternoon and night observations. Same confidence scale as Terra. On 2024-07-07, Aqua holds the largest FRP values in the extract. |
| Suomi-NPP | VIIRS, 375 m | The local file stores `satellite` and `instrument` as `SNPP`. Confidence is `l`, `n`, or `h`. |
| NOAA-20 (JPSS-1) | VIIRS, 375 m | Confidence is `l`, `n`, or `h`. The brightness column reaches an exact stored value of 367 K. |
| NOAA-21 (JPSS-2) | VIIRS, 375 m | Same VIIRS table shape as NOAA-20. Its orbit samples the same regions at a different time. |

Direct comparison fails for specific, observed reasons:

- **Detections are not fires.** Summing Terra, Aqua, and three VIIRS archives counts pixels, including many pixels from one burning area and from repeated overpasses.
- **Confidence scales differ.** A MODIS value of 75 and a VIIRS flag of `h` are not the same quantity. A MODIS value of 0 is a stored confidence, including on a very large Aqua FRP row.
- **Brightness is not one temperature.** VIIRS `brightness` is the FIRMS name for the I-4 channel. On this date it stops at the exact text `367`, with no values above it and none in the open interval from 360 K to 367 K. The files do not contain a Level-1 saturation flag, so those rows are not labeled confirmed saturated. MODIS brightness is a different stored temperature and reaches above 367 K, including a Terra daytime maximum whose stored brightness text is `500`.
- **FRP retrievals differ by sensor.** The unit is MW in every file. The algorithm, the pixel size, and the behavior at saturation are not the same. NOAA-21's largest FRP on this date does not sit on a 367 K brightness row.
- **Pixel geometry changes with scan angle.** `scan` and `track` are stored along-scan and along-track pixel sizes in kilometres. A 1 km proximity threshold is not a sensor footprint.
- **Proximity is not identity.** Two rows can be metres apart and many hours apart. On 2024-07-07, every satellite pair has zero proximity pairs at the same UTC minute inside 5 km. Inside wider windows, one detection can join many partners. Those pair totals are not a fire count.
- **Processing provenance is unresolved.** The FIRMS download readme and the FIRMS API catalog do not agree about NOAA-20 and NOAA-21 standard products. These CSVs do not store a processing-stream field. The filename prefix and the version column were recorded and were not used to assign near-real-time or standard processing.

## 4. Project objectives

1. Keep Terra, Aqua, Suomi-NPP, NOAA-20, and NOAA-21 distinct.
2. Describe each archive before interpreting it.
3. Test whether apparent anomalies, including the VIIRS 367 K brightness and extreme MODIS FRP, survive inspection of the original rows and of product documents.
4. Measure spatial and temporal proximity without declaring same-fire matches.
5. State which variables could enter a later calibration, and which must wait.
6. Specify the 30-date, five-sensor bundle required before a temporal validation can be claimed.
7. Show the audit on a globe once a verified dataset is connected to the interface.

Objectives 1 through 6 are underway for the audited extracts. Objective 7 is the FireLens demo: the globe shows the labeled synthetic sample, and the historical and sensor screens show the verified archive statistics.

## 5. Proposed scientific methodology

The methodology is a sequence. Later steps are not started until the earlier evidence exists.

1. **Inventory.** Read the CSV headers and values. Confirm satellites, instruments, dates, and code lists. Do not rename VIIRS `brightness` or `bright_t31` to channel names the file does not use.
2. **Provenance.** Require an explicit processing stream. Do not infer it from `fire_archive` or `fire_nrt`, or from version `2` or `61.03`.
3. **Describe one day, then repeat across days.** Report counts, FRP distributions, confidence, day and night, and geography as detection rows. Repeat the same measurements on additional dates before claiming that a pattern is stable.
4. **Inspect anomalies in the original rows.** Keep extreme FRP. Separate a stored number from a confirmed physical condition. A 367 K brightness without a saturation bit remains an observed value, not a confirmed saturated pixel.
5. **Match by proximity, then stop.** For configurable distances and time windows, report pair counts, the unique detections involved, and the distributions of distance and time gap. Set same-fire status to not assessed.
6. **Calibrate only after the design is ready.** FRP is the candidate measurement. `scan` and `track` are geometry. Day/night and satellite are strata. Coordinates and acquisition time are match keys. Brightness and confidence stay excluded until the scales and quality metadata support a shared use. No coefficient is fit in this phase.
7. **Do not add detections across sensors and call the sum a fire count.**

Harmonization coefficients, unique-fire clustering, anomaly baselines, and prediction are later steps. They are not in the code.

## 6. System architecture

Implemented and planned pieces are listed separately. Nothing in the planned column is a deployed service.

### Implemented

**Frontend.** A React single-page app named FireLens. The globe renders a deterministic synthetic hotspot sample with CesiumJS and an OpenStreetMap basemap, so it does not need a Cesium ion token. The historical explorer and the sensor comparison read July 2024 aggregate statistics transcribed from the tracked reports. They do not load the raw CSVs. CSV export writes the filtered delivered-row table. The propagation view is a canvas sketch with a persistent demonstration disclaimer. The interface does not call NASA.

**Scientific backend.** The Python package `backend/fire_data` reads local CSV archives and writes reports:

| Command | What it does now | Output |
| --- | --- | --- |
| `python -m fire_data discover` | Measures the four archives | `backend/reports/discovery.json` |
| `python -m fire_data validate` | Checks the observed column contract | Exit status |
| `python -m fire_data eda` | One-day exploratory summary and figures | `backend/reports/eda_report.md`, `eda_summary.json`, `figures/` |
| `python -m fire_data.investigate` | VIIRS 367 K and the two extreme Aqua FRP rows | `backend/reports/anomaly_investigation.md` |
| `python -m fire_data.temporal` | Provenance notes and single-date proximity | `backend/reports/temporal_validation.md` |
| `python -m fire_data.readiness` | Provenance matrix, matcher audit, 30-date specification | `backend/reports/data_readiness.md` |

There is no HTTP service between the frontend and the backend.

### Planned, not built

- A harmonization pipeline that estimates sensor adjustments.
- A historical anomaly engine and any predictive model.
- A calendar driven by real detections rather than the selected month alone.
- Parquet or GeoParquet analytical tables.
- Firebase Firestore for application state or alerts.
- A public API.

Three.js is not a dependency. CesiumJS is the globe.

## 7. Technology stack

**Frontend, installed and used**

- React 19 and React DOM
- TypeScript 7
- Vite 8
- Tailwind CSS 4
- CesiumJS 1, with workers copied to `/cesiumStatic`
- Lucide React for icons
- Oxlint for lint

**Scientific backend, installed and used**

- Python 3.11 or newer
- pytest, NumPy, SciPy, and Matplotlib, pinned in `backend/requirements.txt`

**Declared only as future storage**

- Parquet or GeoParquet for analytical tables, if a later phase adds them
- Firebase Firestore for selected application data, if a later phase adds it

No Firebase SDK, service account, or Firestore rules are in this repository.

## 8. NASA FIRMS data sources and acquisition

The analysis reads FIRMS active-fire CSV extracts. It does not call the FIRMS web-service API, and it does not contain a FIRMS `MAP_KEY`.

Download tables from the [FIRMS archive download tool](https://firms.modaps.eosdis.nasa.gov/download/). The product codes used for this project are:

- MODIS Collection 6.1, Terra and Aqua together in one FIRMS table (`M-C61`)
- VIIRS 375 m Suomi-NPP (`SV-C2`)
- VIIRS 375 m NOAA-20 (`J1V-C2`)
- VIIRS 375 m NOAA-21 (`J2V-C2`)

Request the same area and the same dates for every sensor. Keep the provider filename. Record the processing stream in a note beside the download. The filename prefix and the version column are not sufficient, especially for NOAA-20 and NOAA-21, where the FIRMS download readme and the FIRMS API availability catalog disagree. Details and the required manifest fields are in [`backend/reports/data_readiness.md`](backend/reports/data_readiness.md).

If a FIRMS `MAP_KEY` is required for a later API client, put it in an untracked environment file. Do not commit it. The current code has no place to put that key because it does not call the API.

Place CSVs under `backend/data/raw/` using the paths in [`backend/data/raw/README.md`](backend/data/raw/README.md). Those files are gitignored.

The July 2024 monthly intake is separate from the 7 July sample. Copy four unmodified FIRMS ZIP archives into `backend/data/incoming/2024-07/`: MODIS C6.1 (`M-C61`), VIIRS S-NPP (`SV-C2`), VIIRS NOAA-20 (`J1V-C2`), and VIIRS NOAA-21 (`J2V-C2`). From `backend/`:

```bash
.venv\Scripts\python -m fire_data.ingest --dry-run
.venv\Scripts\python -m fire_data.ingest
```

The dry run does not extract files. The second command writes CSVs under `backend/data/raw/monthly_2024_07/` and `backend/reports/ingestion_2024_07.json`. It does not replace the 7 July sample. A date missing from a CSV stays absent and is not counted as zero detections. Those ZIPs have not been ingested in this repository yet.

## 9. Data provenance and reproducibility

Reproducibility here means another person can rerun the same commands on the same local CSVs and obtain the same report types. It does not mean the processing center of each file has been identified.

What is verified from the files:

- One acquisition date, 2024-07-07.
- 277,259 detection rows: Terra 7,044, Aqua 13,366, NOAA-20 82,372, NOAA-21 87,637, Suomi-NPP 86,840.
- A shared 15-column header: `latitude`, `longitude`, `brightness`, `scan`, `track`, `acq_date`, `acq_time`, `satellite`, `instrument`, `confidence`, `version`, `bright_t31`, `frp`, `daynight`, `type`.
- MODIS version text `61.03`. VIIRS version text `2`.
- No processing-stream column, no product short name, no provider checksum, and no area-of-interest field.

What remains unverified:

- Whether each file is near-real-time or standard quality.
- Whether VIIRS `bright_t31` is I-5, and whether MODIS `bright_t31` is channel 31, beyond the column name.
- Whether any proximity pair is one physical fire.

The readiness matrix in [`backend/reports/data_readiness.md`](backend/reports/data_readiness.md) marks each field verified, unverified, or missing. Reports under `backend/reports/` are committed so the measurements can be read without the raw CSVs. Regenerating them requires the local archives.

## 10. Current implementation and scientific findings

These statements are limited to 2024-07-07. They are not a seasonal result and not a completed harmonization.

**Exploratory analysis.** [`backend/reports/eda_report.md`](backend/reports/eda_report.md) describes detection counts, FRP, confidence, the day/night flag, UTC hour, and geography. Detection counts are archive rows. MODIS and VIIRS confidence stay on separate scales. Extreme FRP values are retained. Figures are in `backend/reports/figures/`.

**VIIRS brightness.** NOAA-20, NOAA-21, and Suomi-NPP each have a maximum stored brightness of exactly 367 K. The counts are 3,190 (3.87%), 7,305 (8.34%), and 5,600 (6.45%). No row is above 367 K, and no row falls in [360 K, 367 K). The Collection 2 VIIRS 375 m user's guide describes 367 K as the nominal I-4 saturation assignment in the typical saturation case. These CSVs do not carry the Level-1 flag, so the investigation does not mark individual rows as confirmed saturated. Every `h` flag on this date sits on 367 K, and some 367 K rows are `l`. See [`backend/reports/anomaly_investigation.md`](backend/reports/anomaly_investigation.md).

**Extreme MODIS FRP.** Two Aqua rows, 7,956.3 MW and 7,328.1 MW, were acquired at 2232 UTC, 912 m apart, with scan 3.9 km and track 1.8 km. Confidences are 75 and 0. Same-minute neighbors within 5 km are other Aqua rows from that overpass. Closer VIIRS rows are hours earlier. They are not classified as the same fire.

**Temporal and proximity audit.** [`backend/reports/temporal_validation.md`](backend/reports/temporal_validation.md) is a single-date methodological audit, not a multi-date validation. Across all satellite pairs, the same UTC minute produces zero pairs inside 5 km. Wider windows produce many-to-many pairs. NOAA-20 and NOAA-21, for example, have 2,073,568 pairs inside 5 km and 180 minutes, drawn from 69,345 NOAA-20 rows and 74,359 NOAA-21 rows. That pair count is not a fire count.

**Readiness.** Brightness and confidence are excluded from calibration until further evidence. FRP is the candidate measurement. The 30-date acquisition specification records zero dates acquired beyond the file already on disk. See [`backend/reports/data_readiness.md`](backend/reports/data_readiness.md).

## 11. Local installation and development

### Frontend

Node.js 22 or newer and npm 11. The commands below were run with Node.js 24 and npm 11.

```bash
npm install
npm run dev
```

Vite prints a local URL, usually `http://localhost:5173`.

World imagery and world terrain need a Cesium ion token. Without one, the globe uses OpenStreetMap imagery and the WGS84 ellipsoid.

```bash
copy .env.example .env
```

On macOS or Linux, use `cp .env.example .env`. Set `VITE_CESIUM_ION_TOKEN` in `.env` only. Leave it empty to keep OpenStreetMap. `.env` is gitignored. `.env.example` contains an empty placeholder.

OpenStreetMap tiles used in development must follow the [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/).

### Backend

From `backend/`, with Python 3.11 or newer:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

On macOS or Linux, use `.venv/bin/python`.

Put the FIRMS CSVs in `backend/data/raw/` before the commands that read them. Discovery, validation, EDA, investigation, temporal audit, and readiness all expect those local files.

After the four July 2024 ZIP archives are copied into `backend/data/incoming/2024-07/`:

```bash
.venv\Scripts\python -m fire_data.ingest --dry-run
.venv\Scripts\python -m fire_data.ingest
```

## 12. Testing and validation

Frontend:

```bash
npm run lint
npm run build
npm run preview
```

`npm run build` runs the TypeScript project build, then the Vite production bundle. `npm run preview` serves that bundle.

Backend, from `backend/`:

```bash
.venv\Scripts\python -m pytest
.venv\Scripts\python -m fire_data discover
.venv\Scripts\python -m fire_data validate
.venv\Scripts\python -m fire_data eda
.venv\Scripts\python -m fire_data.investigate
.venv\Scripts\python -m fire_data.temporal
.venv\Scripts\python -m fire_data.readiness
```

`validate` exits with status 1 when an archive fails the observed contract. `eda` accepts `--thresholds-m 375,1000,5000`. The other commands write only their own report files. They do not modify the raw CSVs.

## 13. Project roadmap

Done for one day:

- Dashboard scaffold with a Cesium globe and explicit DEMO labeling.
- Archive discovery, validation, exploratory analysis, anomaly investigation, single-date proximity audit, and a data-readiness review.

Next, in order:

1. Acquire the 30-date, five-sensor bundle with an explicit processing stream in the manifest.
2. Repeat the 367 K and FRP audits across those dates.
3. Decide a harmonization design from variables that pass the readiness review.
4. Connect verified aggregates to the globe, calendar, and export.
5. Only then consider an anomaly baseline or a predictive model.

## 14. Known limitations and unresolved questions

- The scientific results are one global day, 2024-07-07.
- The product short name and processing stream are missing for every local archive.
- The FIRMS download readme says NOAA-20 and NOAA-21 standard-quality data were not available. The FIRMS API catalog lists standard-processing sensor codes for both. Neither identifier is stored in the CSVs.
- VIIRS rows at 367 K are not confirmed saturated.
- Proximity pairs are not same-fire matches. `same_fire` is `not_assessed`.
- The frontend metrics, calendar, and export do not read the backend reports.
- No harmonization coefficient, anomaly score, or forecast is computed.
- A license file has not been added. See the acknowledgments for the recommended license and the decision still required.

## 15. Intended impact and target users

The intended result is a fire history that researchers and challenge reviewers can compare across MODIS and VIIRS without confusing sensor differences with changes in burning. The users are:

- NASA Space Apps judges reviewing what is implemented and what is still proposed.
- Fire-data researchers who need the detection, proximity, and provenance distinctions stated explicitly.
- Developers extending the dashboard only after the scientific contract is stable.

The FIRMS disclaimer applies to the underlying data: these products are not advised for tactical decisions at local scale. This project does not change that limit.

## 16. Contributors and acknowledgments

The public repository is `larzzondev/nasa-space-apps-2026-fire-modis-viirs-harmonization`. Individual contributor names should be added by the team. This file does not invent a contributor list.

Data and documents used in the audit come from NASA FIRMS and LANCE, the FIRMS download readme, the FIRMS API data-availability page, the FIRMS VIIRS attribute description, LAADS DAAC product pages, and the Collection 2 VIIRS 375 m Active Fire Product User's Guide. Active-fire science products acknowledged there are produced with the University of Maryland and distributed by FIRMS.

Software noted in the reports includes CesiumJS. OpenStreetMap imagery is used only when no Cesium ion token is configured.

**License.** No license file is in the repository yet. Apache-2.0 is the recommended open-source license for this scientific software because it is permissive and includes an explicit patent grant. Do not add it until the copyright holders confirm that choice. Third-party data and Cesium ion services keep their own terms.

## Repository layout

```text
src/                  React dashboard. DEMO data only.
backend/fire_data/    Discovery, validation, EDA, investigation, temporal audit, readiness, ingestion.
backend/tests/        Pytest suite.
backend/reports/      Committed scientific reports and figures.
backend/data/raw/     Local FIRMS CSVs, including the untouched 7 July sample. Gitignored.
backend/data/incoming/2024-07/  Drop folder for the four July 2024 ZIP archives. Gitignored.
.env.example          Empty Cesium ion placeholder.
```
