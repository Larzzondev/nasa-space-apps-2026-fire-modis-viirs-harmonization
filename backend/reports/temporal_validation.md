# Temporal validation

Multi-date temporal validation is unavailable. Acquisition dates present: 2024-07-07. Row totals by date: 2024-07-07 (277,259 rows). The measurements below use only those dates. No additional dates were created.

## What is missing

- A second acquisition date is absent. Dates present: 2024-07-07. Cross-date counts, proportions, FRP distributions, and geographic persistence were not computed, and no dates were added.
- The local data directory has no FIRMS zip Readme, request manifest, HDF granule, or netCDF granule beside the four CSV files.
- No CSV column identifies NRT versus standard processing, and no column carries an I4 saturation quality flag.
- The FIRMS FAQ page linked from the download readme returned HTTP 403 in this pass, so its NRT-versus-standard comparison is not quoted.

## Provenance

Processing level is unresolved for every local archive. A filename that begins with `fire_archive` or `fire_nrt`, and a version value of `2` or `61.03`, are recorded below and are not treated as proof of standard or near-real-time processing.

### Files

- `modis/fire_archive_M-C61_850118.csv`: 20,410 rows; dates 2024-07-07; versions 61.03 (20,410); satellites Aqua 13,366, Terra 7,044; acquisition minutes Aqua 215 distinct HHMM, Terra 220 distinct HHMM. Processing level: unresolved. No processing-level column is present, so standard processing and near-real-time processing are not assigned. The filename and the version field are stored as file facts and are not used as that assignment.
- `viirs_noaa20/fire_archive_J1V-C2_850119.csv`: 82,372 rows; dates 2024-07-07; versions 2 (82,372); satellites NOAA-20 82,372; acquisition minutes NOAA-20 428 distinct HHMM. Processing level: unresolved. No processing-level column is present, so standard processing and near-real-time processing are not assigned. The filename and the version field are stored as file facts and are not used as that assignment.
- `viirs_noaa21/fire_archive_J2V-C2_850120.csv`: 87,637 rows; dates 2024-07-07; versions 2 (87,637); satellites NOAA-21 87,637; acquisition minutes NOAA-21 448 distinct HHMM. Processing level: unresolved. No processing-level column is present, so standard processing and near-real-time processing are not assigned. The filename and the version field are stored as file facts and are not used as that assignment.
- `viirs_snpp/fire_archive_SV-C2_850121.csv`: 86,840 rows; dates 2024-07-07; versions 2 (86,840); satellites S-NPP 86,840; acquisition minutes S-NPP 446 distinct HHMM. Processing level: unresolved. No processing-level column is present, so standard processing and near-real-time processing are not assigned. The filename and the version field are stored as file facts and are not used as that assignment.

### Documents retrieved for this pass

- The FIRMS download readme says a request can return near-real-time files, standard-quality files, or both, and that NRT data are replaced when standard data are available, after approximately three months. It defines fire_nrt_M-C61 as MCD14DL, fire_archive_M-C61 as standard-quality MCD14ML, fire_nrt_SV-C2 as VNP14IMGTDL, and fire_archive_SV-C2 as standard-quality VNP14IMGTML. It defines fire_nrt_J1V-C2 as VJ114IMGDL and fire_nrt_J2V-C2 as VJ214IMGDL. It does not define fire_archive_J1V-C2 or fire_archive_J2V-C2. It states: standard quality data is not yet available from FIRMS for NOAA-20 and NOAA-21. The characters after the product code are the download request id. The Collection / Version field is described as the way to distinguish MODIS from VIIRS when the files are combined, not as an NRT-versus-standard flag. Source: https://firms.modaps.eosdis.nasa.gov/download/Readme.txt (retrieved 2026-11-14).
- The FIRMS API data-availability page lists separate sensor codes for near-real-time and standard processing, including VIIRS_NOAA20_NRT, VIIRS_NOAA20_SP, VIIRS_NOAA21_NRT, VIIRS_NOAA21_SP, VIIRS_SNPP_NRT, VIIRS_SNPP_SP, MODIS_NRT, and MODIS_SP. Those codes are catalog labels. They are not columns in the local CSV files. Source: https://firms.modaps.eosdis.nasa.gov/api/data_availability/ (retrieved 2026-11-14).

The download readme and the API catalog do not agree about NOAA-20 and NOAA-21 standard products: the readme says standard-quality data were not yet available, while the API page lists `VIIRS_NOAA20_SP` and `VIIRS_NOAA21_SP`. Neither page is a field in these CSVs. The approximately three-month replacement lag is also not used to assign a level, including when the acquisition date is earlier than this pass.

## VIIRS 367 K by date

The VIIRS table has one date, so it is the available measurement and not a repeat across dates. Confirmed saturated counts stay at zero because the archives have no Level-1 saturation flag. A high-confidence flag is not used as that flag.

| Satellite | Date | Rows | Exact text 367 | Numeric 367 | Share | Above 367 | In [360, 367) | In [366, 367) | Highest below 367 | Confirmed saturated |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| NOAA-20 | 2024-07-07 | 82,372 | 3,190 | 3,190 | 3.87% | 0 | 0 | 0 | 357.03 (1) | 0 |
| NOAA-21 | 2024-07-07 | 87,637 | 7,305 | 7,305 | 8.34% | 0 | 0 | 0 | 356.5 (1) | 0 |
| S-NPP | 2024-07-07 | 86,840 | 5,600 | 5,600 | 6.45% | 0 | 0 | 0 | 358.31 (1) | 0 |

## MODIS FRP by date and day/night

Terra and Aqua FRP quantiles are reported for the one date in the MODIS archive. A comparison of those quantiles between dates was not computed.
 Quantiles use the linear empirical method on the parsed FRP values. The maximum is the original CSV text with the greatest exact decimal value. An extreme row is one at or above the within-group 0.999 quantile. Cell coordinates are the floor of latitude and longitude, so each cell is the 1° square whose southwest corner is that pair. A cell count is a count of detection rows.

| Satellite | Date | Day/night | Rows | Minimum | p50 | p90 | p99 | p99.9 | Maximum text | Rows at maximum | Confidence at maximum |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| Terra | 2024-07-07 | day | 3,177 | 2.60 | 18.30 | 82.94 | 540.46 | 1,792.91 | 2901.5 | 1 | 100 |
| Terra | 2024-07-07 | night | 3,867 | 0.00 | 19.20 | 78.10 | 393.14 | 1,178.95 | 1632.2 | 1 | 100 |
| Terra | 2024-07-07 | day and night | 7,044 | 0.00 | 18.90 | 80.84 | 460.91 | 1,318.57 | 2901.5 | 1 | 100 |
| Aqua | 2024-07-07 | day | 12,152 | 0.00 | 19.20 | 95.28 | 543.38 | 1,923.92 | 7956.3 | 1 | 75 |
| Aqua | 2024-07-07 | night | 1,214 | 0.00 | 22.45 | 85.67 | 532.70 | 1,547.37 | 1627.1 | 1 | 100 |
| Aqua | 2024-07-07 | day and night | 13,366 | 0.00 | 19.50 | 94.05 | 543.07 | 1,773.25 | 7956.3 | 1 | 75 |

### Upper tail, geography, and time

| Satellite | Date | Day/night | p99.9 FRP | Extreme rows | Confidence | 1° cells | Densest cell | Cell share | Distinct minutes | Modal minute |
| --- | --- | --- | ---: | ---: | --- | ---: | --- | ---: | ---: | --- |
| Terra | 2024-07-07 | day | 1,792.91 | 4 | 100–100 (median 100.0) | 1 | 59°, -119° (4 rows) | 100.00% | 1 | 1910 |
| Terra | 2024-07-07 | night | 1,178.95 | 4 | 100–100 (median 100.0) | 1 | 38°, -113° (4 rows) | 100.00% | 2 | 0400 |
| Aqua | 2024-07-07 | day | 1,923.92 | 13 | 0–100 (median 100.0) | 6 | 37°, -113° (3 rows) | 23.08% | 5 | 2051 |
| Aqua | 2024-07-07 | night | 1,547.37 | 2 | 100–100 (median 100.0) | 2 | -26°, 30° (1 row) | 50.00% | 2 | 0948 |

### Rows holding the daytime or nighttime maximum

| Satellite | Date | Day/night | Line | UTC | Latitude | Longitude | FRP | Confidence | Brightness | Scan | Track |
| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- | --- | --- | --- |
| Terra | 2024-07-07 | day | 17222 | 1910 | 59.7563 | -118.5394 | 2901.5 | 100 | 500 | 1.5 | 1.2 |
| Terra | 2024-07-07 | night | 1512 | 0400 | 38.4555 | -112.3279 | 1632.2 | 100 | 394.2 | 4 | 1.9 |
| Aqua | 2024-07-07 | day | 19915 | 2232 | 48.1499 | -120.4706 | 7956.3 | 75 | 475.9 | 3.9 | 1.8 |
| Aqua | 2024-07-07 | night | 20209 | 2316 | -25.6652 | 30.5474 | 1627.1 | 100 | 406 | 3.3 | 1.7 |

## Cross-satellite proximity

Distance is the ECEF chord on a sphere of radius 6371008.8 m, the same sphere used for the exploratory overlap summary. Time separation is the absolute difference of UTC minutes, with the date included so that the same clock time on two dates is not treated as the same minute. Radii: 375, 1,000, 5,000 m. Windows: 0, 30, 180 minutes. A proximity pair is not a confirmed same-fire match. One detection can appear in more than one pair, so the pair column is not a count of fires and is not summed across satellite pairs.

| Satellite A | Satellite B | Radius (m) | Max Δt (min) | Proximity pairs | A with a neighbor | B with a neighbor | Same fire |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Terra | Aqua | 375 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | Aqua | 375 | 30 | 9 | 9 | 9 | not_assessed |
| Terra | Aqua | 375 | 180 | 161 | 158 | 156 | not_assessed |
| Terra | Aqua | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | Aqua | 1,000 | 30 | 68 | 46 | 54 | not_assessed |
| Terra | Aqua | 1,000 | 180 | 970 | 640 | 661 | not_assessed |
| Terra | Aqua | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | Aqua | 5,000 | 30 | 402 | 96 | 120 | not_assessed |
| Terra | Aqua | 5,000 | 180 | 6,258 | 1,031 | 1,220 | not_assessed |
| Terra | NOAA-20 | 375 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | NOAA-20 | 375 | 30 | 214 | 139 | 199 | not_assessed |
| Terra | NOAA-20 | 375 | 180 | 3,158 | 1,573 | 3,079 | not_assessed |
| Terra | NOAA-20 | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | NOAA-20 | 1,000 | 30 | 1,032 | 296 | 665 | not_assessed |
| Terra | NOAA-20 | 1,000 | 180 | 15,874 | 2,578 | 9,962 | not_assessed |
| Terra | NOAA-20 | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | NOAA-20 | 5,000 | 30 | 5,402 | 336 | 1,013 | not_assessed |
| Terra | NOAA-20 | 5,000 | 180 | 85,634 | 2,897 | 16,139 | not_assessed |
| Terra | NOAA-21 | 375 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | NOAA-21 | 375 | 30 | 511 | 354 | 496 | not_assessed |
| Terra | NOAA-21 | 375 | 180 | 3,006 | 1,578 | 2,938 | not_assessed |
| Terra | NOAA-21 | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | NOAA-21 | 1,000 | 30 | 2,498 | 724 | 1,565 | not_assessed |
| Terra | NOAA-21 | 1,000 | 180 | 16,210 | 2,603 | 10,158 | not_assessed |
| Terra | NOAA-21 | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | NOAA-21 | 5,000 | 30 | 11,549 | 840 | 2,360 | not_assessed |
| Terra | NOAA-21 | 5,000 | 180 | 96,100 | 2,935 | 16,968 | not_assessed |
| Terra | S-NPP | 375 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | S-NPP | 375 | 30 | 54 | 37 | 51 | not_assessed |
| Terra | S-NPP | 375 | 180 | 3,133 | 1,537 | 3,053 | not_assessed |
| Terra | S-NPP | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | S-NPP | 1,000 | 30 | 310 | 101 | 187 | not_assessed |
| Terra | S-NPP | 1,000 | 180 | 16,422 | 2,499 | 10,238 | not_assessed |
| Terra | S-NPP | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| Terra | S-NPP | 5,000 | 30 | 1,693 | 137 | 292 | not_assessed |
| Terra | S-NPP | 5,000 | 180 | 93,237 | 2,786 | 16,740 | not_assessed |
| Aqua | NOAA-20 | 375 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | NOAA-20 | 375 | 30 | 4,655 | 3,170 | 4,628 | not_assessed |
| Aqua | NOAA-20 | 375 | 180 | 7,501 | 4,323 | 7,313 | not_assessed |
| Aqua | NOAA-20 | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | NOAA-20 | 1,000 | 30 | 23,916 | 7,293 | 16,746 | not_assessed |
| Aqua | NOAA-20 | 1,000 | 180 | 39,752 | 9,267 | 26,288 | not_assessed |
| Aqua | NOAA-20 | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | NOAA-20 | 5,000 | 30 | 111,618 | 9,443 | 28,498 | not_assessed |
| Aqua | NOAA-20 | 5,000 | 180 | 200,689 | 11,715 | 43,802 | not_assessed |
| Aqua | NOAA-21 | 375 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | NOAA-21 | 375 | 30 | 1,763 | 1,213 | 1,726 | not_assessed |
| Aqua | NOAA-21 | 375 | 180 | 6,588 | 3,613 | 6,407 | not_assessed |
| Aqua | NOAA-21 | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | NOAA-21 | 1,000 | 30 | 10,005 | 2,847 | 6,949 | not_assessed |
| Aqua | NOAA-21 | 1,000 | 180 | 37,393 | 7,815 | 24,812 | not_assessed |
| Aqua | NOAA-21 | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | NOAA-21 | 5,000 | 30 | 54,190 | 3,874 | 12,060 | not_assessed |
| Aqua | NOAA-21 | 5,000 | 180 | 220,512 | 10,719 | 44,180 | not_assessed |
| Aqua | S-NPP | 375 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | S-NPP | 375 | 30 | 13 | 10 | 13 | not_assessed |
| Aqua | S-NPP | 375 | 180 | 7,031 | 3,833 | 6,820 | not_assessed |
| Aqua | S-NPP | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | S-NPP | 1,000 | 30 | 69 | 24 | 53 | not_assessed |
| Aqua | S-NPP | 1,000 | 180 | 39,149 | 8,338 | 26,106 | not_assessed |
| Aqua | S-NPP | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| Aqua | S-NPP | 5,000 | 30 | 303 | 32 | 113 | not_assessed |
| Aqua | S-NPP | 5,000 | 180 | 218,425 | 11,390 | 45,944 | not_assessed |
| NOAA-20 | NOAA-21 | 375 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | NOAA-21 | 375 | 30 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | NOAA-21 | 375 | 180 | 100,849 | 49,357 | 52,073 | not_assessed |
| NOAA-20 | NOAA-21 | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | NOAA-21 | 1,000 | 30 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | NOAA-21 | 1,000 | 180 | 395,259 | 62,200 | 66,884 | not_assessed |
| NOAA-20 | NOAA-21 | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | NOAA-21 | 5,000 | 30 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | NOAA-21 | 5,000 | 180 | 2,073,568 | 69,345 | 74,359 | not_assessed |
| NOAA-20 | S-NPP | 375 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | S-NPP | 375 | 30 | 77,181 | 48,320 | 48,275 | not_assessed |
| NOAA-20 | S-NPP | 375 | 180 | 110,911 | 54,686 | 57,007 | not_assessed |
| NOAA-20 | S-NPP | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | S-NPP | 1,000 | 30 | 275,306 | 60,860 | 59,844 | not_assessed |
| NOAA-20 | S-NPP | 1,000 | 180 | 419,339 | 65,991 | 70,103 | not_assessed |
| NOAA-20 | S-NPP | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-20 | S-NPP | 5,000 | 30 | 1,275,182 | 67,478 | 65,817 | not_assessed |
| NOAA-20 | S-NPP | 5,000 | 180 | 2,083,460 | 72,106 | 76,638 | not_assessed |
| NOAA-21 | S-NPP | 375 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-21 | S-NPP | 375 | 30 | 73,884 | 45,522 | 46,063 | not_assessed |
| NOAA-21 | S-NPP | 375 | 180 | 113,992 | 55,809 | 56,034 | not_assessed |
| NOAA-21 | S-NPP | 1,000 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-21 | S-NPP | 1,000 | 30 | 275,918 | 56,235 | 59,107 | not_assessed |
| NOAA-21 | S-NPP | 1,000 | 180 | 447,758 | 68,910 | 69,735 | not_assessed |
| NOAA-21 | S-NPP | 5,000 | 0 | 0 | 0 | 0 | not_assessed |
| NOAA-21 | S-NPP | 5,000 | 30 | 1,379,296 | 61,395 | 65,630 | not_assessed |
| NOAA-21 | S-NPP | 5,000 | 180 | 2,354,224 | 75,649 | 76,190 | not_assessed |

## Variables suitable for a later calibration

These variables share a stored unit or a stored role that a later calibration could stratify. No coefficient is calculated.

| Variable | Support | Rationale |
| --- | --- | --- |
| `frp` | single_date_only | FRP is stored in MW for Terra, Aqua, NOAA-20, NOAA-21, and S-NPP. It can be stratified by satellite and by the stored day/night flag. A coefficient is not estimated. The retrievals are sensor-specific, and this extract has one acquisition date. |
| `scan` | single_date_only | Stored along-scan pixel size in km. Usable as an observation-geometry covariate, not as a fire attribute to rescale. |
| `track` | single_date_only | Stored along-track pixel size in km. Usable as an observation-geometry covariate. |
| `daynight` | single_date_only | Stored day/night flag. Usable as a stratum. It is not recomputed from solar zenith angle in this pass. |
| `latitude` | single_date_only | Match coordinate only. It is not a quantity to harmonize across sensors. |
| `longitude` | single_date_only | Match coordinate only. It is not a quantity to harmonize across sensors. |
| `acq_date` | single_date_only | Match time key. Only 2024-07-07 is present, so the key cannot yet support a temporal repeat. |
| `acq_time` | single_date_only | UTC HHMM match key within the dates that are present. Several minutes occur on 2024-07-07. |
| `satellite` | single_date_only | Sensor stratum. Detections from different satellites are not additive fire counts. |

## Variables requiring special treatment

| Variable | Support | Rationale |
| --- | --- | --- |
| `brightness` | needs_metadata | VIIRS brightness has an exact stored value at 367 K and no values above it in this extract. The CSV has no Level-1 saturation flag, so those rows are not confirmed saturated. MODIS brightness is a different stored temperature and reaches above 367 K. |
| `confidence` | needs_metadata | MODIS confidence is an integer from 0 through 100. VIIRS confidence is l, n, or h. The scales are not interchangeable. A MODIS value of 0 is a stored confidence, including on large FRP rows. |
| `version` | needs_metadata | The version field records the collection identifier seen in the file. It does not identify NRT versus standard processing. |
| `instrument` | needs_metadata | The S-NPP archive stores instrument as SNPP. The NOAA-20 and NOAA-21 archives store VIIRS. The token is not a processing level. |
| `bright_t31` | needs_metadata | The column is present and numeric. The files do not state whether it is MODIS channel 31 or VIIRS I-5. |
| `type` | needs_metadata | Stored codes include 0, 1, 2, and 3. This pass does not drop a class and does not treat every row as the same fire type. |
| `processing_level` | needs_metadata | Absent from every local archive. NOAA-20 and NOAA-21 in particular cannot be pooled under a standard-product assumption. |
| `proximity_pairs` | single_date_only | A pair inside a distance and time window is a proximity match. It is not a confirmed same-fire match and the pairs are not summed across sensors as fires. |

## Limitations

- The result is limited to the acquisition dates actually stored in the local archives.
- Provenance stops at unresolved for every file. Collection version and the archive filename are not a processing-level measurement.
- VIIRS rows at 367 K are counted. They are not labeled confirmed saturated.
- Day and night follow the stored flag.
- The 0.999 FRP quantile is internal to each satellite, date, and day/night group in this extract.
- Proximity does not adjust for scan-dependent pixel growth or geolocation error.
- No harmonization coefficient is calculated.

## Unresolved questions

- Which processing stream produced each local file, in particular the NOAA-20 and NOAA-21 archives named `fire_archive_J1V-C2` and `fire_archive_J2V-C2`.
- Whether the current API standard-processing codes describe products that can be joined to these download files.
- Whether any individual VIIRS detection at 367 K is the Level-1 saturation case, the fold-over case, or the aggregation case.
- Whether `bright_t31` is MODIS channel 31 in the MODIS file and VIIRS I-5 in the VIIRS files.
- Whether any proximity pair is the same physical fire.
- How often the 367 K value, the MODIS FRP maxima, and the proximity rates recur on other dates.

## Reproduction

From the backend directory:

```bash
.venv\Scripts\python -m fire_data.temporal
```

The command writes `reports/temporal_validation.md`, `reports/temporal_summary.json`, and the CSV files in `reports/temporal/`. It leaves the exploratory report, the anomaly report, and `data/raw/` unchanged.
