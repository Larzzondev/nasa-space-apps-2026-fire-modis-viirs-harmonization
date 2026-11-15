# Data and scientific limitations

This note records what the July 2024 FIRMS extracts support, and what they leave open. Numbers are copied from the tracked reports named in each section. A hypothesis is labeled as a hypothesis. A missing observation is not rewritten as a zero.

The interface that displays a subset of these aggregates is described in [ARCHITECTURE.md](ARCHITECTURE.md). The project overview is the [README](../README.md).

## How to read a count

An **observation** in this repository is one stored CSV row: one source file, one line, and the fifteen stored fields. A **detection** is that row read as one sensor's hot-spot record at one acquisition minute. It is not a physical fire, not a polygon, and not a unique event across overpasses.

A **candidate pair** is two archived rows, from two named sensors, whose great-circle separation and acquisition-time difference fall inside a stated threshold. One detection can belong to many pairs. The pair count is not a fire count.

An **analytical cluster** is a DBSCAN component on one UTC-date partition. A component id is a label inside that partition. Partition counts are not additive, and they are not a monthly fire total.

`same_fire` is `not_assessed` on the experiment configurations and on the July reports that state the field. The statements below remain false in this repository:

- A nearest neighbor is the same fire.
- A mutual nearest neighbor is the same fire.
- A one-to-one assignment is the same fire.
- A candidate pair is the same fire.
- An analytical cluster is the same fire.
- Spatial proximity, or a short time gap, establishes the same fire.

The definitions and the locks are in [`backend/research/SHARED_DATA_CONTRACT.md`](../backend/research/SHARED_DATA_CONTRACT.md).

## MODIS versus VIIRS

The July files contain five satellites and two instrument families. Terra and Aqua stay separate even when a published pair label says "MODIS (Terra and Aqua)." Suomi-NPP stores `instrument` as `SNPP`, not `VIIRS`. A display family of "VIIRS" may be stated beside that stored value. The stored value is not rewritten.

| | MODIS in these files | VIIRS 375 m in these files |
| --- | --- | --- |
| Platforms | Terra, Aqua | Suomi-NPP, NOAA-20, NOAA-21 |
| FIRMS product codes | `M-C61` | `SV-C2`, `J1V-C2`, `J2V-C2` |
| Version text stored | `61.03` | `2` |
| Confidence | Integer 0 through 100, including 0 | Flags `l`, `n`, `h` |
| Nominal pixel class | About 1 km at nadir | About 375 m at nadir |
| Brightness column | Stored `brightness`. July maxima are above 367 K. | Stored `brightness`. July maxima are exactly 367 K. |
| `bright_t31` | The column name is kept. The FIRMS MODIS page discusses channel 31. That sentence is not copied onto the VIIRS files. | The column name is kept. The thermal-field comparison does not treat `bright_t31`, `bright_ti5`, `T5`, and `FP_T5` as one schema. |
| July delivered rows | Terra 195,316, Aqua 481,320 | Suomi-NPP 1,635,020, NOAA-20 2,902,597, NOAA-21 2,771,214 |

Row counts are archive volume. The monthly exploratory report states that they are not a ranking of detection sensitivity. VIIRS 375 m tables contain more rows than the MODIS table in this month. That difference mixes pixel size, overpass timing, detection rules, and, for Suomi-NPP, missing dates. It is not a harmonization factor.

FRP is stored in megawatts in every file. July medians from [`backend/reports/monthly_eda_2024_07.md`](../backend/reports/monthly_eda_2024_07.md): Terra 19.1 MW, Aqua 21.6 MW, Suomi-NPP 5.06 MW, NOAA-20 5.14 MW, NOAA-21 6.09 MW. Means sit above the medians (Terra 45.551, Aqua 51.4279, Suomi-NPP 10.6144, NOAA-20 10.6352, NOAA-21 12.6347). Extremes are retained, including Aqua's maximum of 10,950 MW. Zero-FRP rows stay in the distributions: Terra 393, Aqua 155, NOAA-20 809, NOAA-21 1,710, Suomi-NPP 373.

Experiment B cites positive-FRP ratios only when both values are positive, and it states that a ratio quantile is not a confidence interval and not a coefficient. No slope or intercept is estimated. See [`backend/experiments/B_measurements/report.md`](../backend/experiments/B_measurements/report.md).

## Spatial resolution differences

Nominal classes and stored sizes are different quantities.

The product documents cited by the historical strategy describe MODIS fire locations as a 1 km class and the VIIRS products used here as 375 m swaths. The sensor-comparison screen draws that contrast as a nadir schematic: a 3 km frame holds nine ~1 km samples, or sixty-four 375 m samples. The screen says the grid is not a scan-angle footprint.

`scan` and `track` are the along-scan and along-track pixel sizes stored in the CSV, in kilometres. They grow away from nadir. On 7 July 2024, from [`backend/reports/eda_report.md`](../backend/reports/eda_report.md):

| Satellite | Scan median (km) | Scan maximum (km) | Track median (km) | Track maximum (km) |
| --- | ---: | ---: | ---: | ---: |
| Terra | 1.2 | 4.8 | 1.1 | 2 |
| Aqua | 1.2 | 4.8 | 1.1 | 2 |
| NOAA-20 | 0.42 | 0.8 | 0.42 | 0.78 |
| NOAA-21 | 0.44 | 0.8 | 0.5 | 0.78 |
| Suomi-NPP | 0.44 | 0.8 | 0.44 | 0.78 |

For the full month, Experiment B reports scan medians of 1.200 km (Terra), 1.300 km (Aqua), and 0.440 km (Suomi-NPP, NOAA-20, and NOAA-21). Experiment D multiplies stored `scan` by stored `track` and treats the product as a size proxy. The archive does not include the pixel polygon, the scan angle, or the ground orientation. Adjacent-scan overlap and Earth curvature inside the pixel are not corrected. The median of the products and the product of the medians are reported separately and are not treated as the same quantity.

Search radii used in the pair and cluster reports — 375 m, 750 m, 1 km, 2 km, and 5 km — are search limits. A 375 m radius is not a VIIRS pixel, and a 1 km radius is not a MODIS pixel. At 375 m and `min_samples` 4, the published within-sensor noise share is 1 for Terra and Aqua, and about 0.98 for each VIIRS satellite. A 375 m neighborhood is a different relative scale on a ~1 km MODIS pixel than on a 375 m VIIRS pixel. That is why Terra and Aqua are not pooled in the within-sensor clustering.

Equal-degree cells are not equal-area cells. Experiment D records that the 1° cell with the most Aqua rows is not the cell with the highest rows per 1,000 km². High-latitude bands cover less ground. A raw count there is not a density. No H3 resolution is selected.

## Confidence semantics

The two scales are stored as different types and are not converted.

**MODIS** confidence is an integer from 0 through 100. Zero is a stored confidence, not a missing value. For July, both Terra and Aqua have median 69. Terra has 2,414 rows at 0 and 30,113 rows at 100. Aqua has 4,240 rows at 0 and 29,197 rows at 100. The nearest-neighbor report also splits MODIS into the published classes 0–29, 30–79, and 80–100. That split is a reporting partition. It is not a second product, and it is not comparable to `l`, `n`, or `h`.

**VIIRS** confidence is `l` (low), `n` (nominal), or `h` (high). July counts from the monthly exploratory report:

| Satellite | Low | Nominal | High |
| --- | ---: | ---: | ---: |
| NOAA-20 | 265,829 | 2,479,081 | 157,687 |
| NOAA-21 | 257,640 | 2,324,309 | 189,265 |
| Suomi-NPP | 133,710 | 1,401,558 | 99,752 |

On 7 July, every stored `h` flag sits on brightness 367 K, and some 367 K rows are `l`. The same pattern holds for the month: every stored `h` flag is on brightness text `367`, and no `n` flag is on that value. The FIRMS attribute page associates high-confidence pixels with saturated pixels. The anomaly investigation quotes that statement and still treats row-level saturation as unproven, because the CSV has no I-4 saturation bit.

A MODIS value of 0 can sit on a very large FRP row. On 7 July, Aqua line 19920 stores FRP 7,328.1 MW with confidence 0, beside Aqua line 19915 at 7,956.3 MW with confidence 75. Both are daytime, 2232 UTC, scan 3.9 km, track 1.8 km, 912 m apart. The investigation records the rows. It does not classify them as one fire, and it does not classify closer VIIRS rows from earlier hours as the same fire. See [`backend/reports/anomaly_investigation.md`](../backend/reports/anomaly_investigation.md).

The 7 July comparison screen shows MODIS medians and does not repeat the month's counts of confidence 0 and 100. Those single-day tallies were not transcribed onto that control. The month screen does show them.

## July 2024 dataset coverage

The monthly integrity check in [`backend/reports/temporal_coverage_2024_07.md`](../backend/reports/temporal_coverage_2024_07.md) passed. Total delivered rows: 7,985,467. Reference total: 7,985,467. Difference: 0.

| Dataset | Delivered rows | SHA-256 |
| --- | ---: | --- |
| MODIS `fire_archive_M-C61_850319.csv` | 676,636 | `97e1a4312fbe488e63fd06461865b21dd5d01c419f2e80fa6e178c0015f10c81` |
| VIIRS S-NPP `fire_archive_SV-C2_850322.csv` | 1,635,020 | `bc5ff311c2df9113baf4eedaf4247d55954e8f4fa2ca052f940a943365314f21` |
| VIIRS NOAA-20 `fire_archive_J1V-C2_850320.csv` | 2,902,597 | `9a192db30e307c257955047ca1177e3f2f463b8c8cdfda7b28ceac6b3aa92bd5` |
| VIIRS NOAA-21 `fire_archive_J2V-C2_850321.csv` | 2,771,214 | `c86e46d4ca730eea6db448ff928126ddc6b44ba4c4d11dfbc3a2d999f4937007` |

Terra 195,316 and Aqua 481,320 are the split of the MODIS file. Exact duplicate rows retained: 0. Extra location-time keys retained: 5 (1 in NOAA-20, 4 in NOAA-21). Empty cells: none reported. Malformed fields: none reported. No row was removed.

The separate 7 July sample (request ids 850118–850121) has 277,259 rows: Terra 7,044, Aqua 13,366, NOAA-20 82,372, NOAA-21 87,637, Suomi-NPP 86,840. The monthly file delivers the same five counts on 2024-07-07. The monthly exploratory report records a difference of zero for each.

Delivery status, as used by the temporal scan and the shared contract:

| Status | Meaning |
| --- | --- |
| `rows_delivered` | The CSV has at least one row with that acquisition date. |
| `zero_rows_delivered` | The CSV is present and has no row with that date. The delivered-row count in the file is zero. That is not zero fire activity. |
| `source_file_missing` | The CSV itself is absent. There is no delivered-row count. |

Terra, Aqua, NOAA-20, and NOAA-21 have rows on all 31 dates. Suomi-NPP has rows on 21 dates. A cross-sensor date is compared only when both sides have at least one row that UTC date.

`acq_time` resolves to one minute. A difference of zero minutes means the same archived minute somewhere in the comparison being discussed. It does not prove the same instant, and a closest-minute median of zero in Experiment C ignores location. That median can be zero when two satellites store the same clock time somewhere on Earth that date. It is not the separation of a spatially nearby pair.

July 31 has no next-date neighbor inside this extract, because 1 August is outside it. That exclusion is not a zero-detection day.

## S-NPP data gaps

Suomi-NPP dates with no delivered rows: 10, 11, 12, 13, 14, 15, 25, 26, 27, and 28 July 2024. They stay out of denominators. They are not filled from NOAA-20, NOAA-21, Terra, or Aqua, and they are not given a cluster count of zero.

The coverage investigation keeps FIRMS evidence and Level-2 swath evidence in separate classes. The Level-2 product queried in CMR is `VNP14IMG` (VIIRS/NPP Active Fires 6-Min L2 Swath 375 m V002). That swath is not the FIRMS fire-location table. Cataloged granules that were not opened do not become fire counts. `confirmed_zero_detections` and `archive_delivery_gap` were not assigned.

| Dates | Local FIRMS rows | What the investigation supports |
| --- | --- | --- |
| 10–15 July | No rows on those UTC dates | The LP DAAC geolocation alert places these dates inside a stated VIIRS gap, from 21:42 UTC on 9 July through 17:42 UTC on 16 July. The same alert records an earlier notice that starts the anomaly at 21:46 UTC on 9 July. The Level-2 class for the full UTC dates 10–15 July is `confirmed_source_unavailable`. The FIRMS class is `unknown`. The alert names the Level-2 fire product. It does not name this FIRMS CSV as its own product. On 10 July, CMR still lists 79 `VNP14IMG` granules; those files were not opened. |
| 16 July, before 17:42 UTC | No rows in that interval | Level-2 class `confirmed_source_unavailable` for the interval the alert covers. |
| 16 July, after 17:42 UTC | 15,643 rows through the end of the UTC day | Both classes `confirmed_data_available` for that later interval. Hours with rows: 17–23. |
| 24 July, before 05:28 UTC | 14,621 rows | Both classes `confirmed_data_available`. Hours with rows: 0–5. |
| 24 July, 05:28–18:22 UTC | No rows in that interval | LP DAAC describes an outage. Level-2 class `confirmed_source_unavailable`. FIRMS class `unknown`. |
| 24 July, after 18:22 UTC | No rows in that interval | Both classes `unknown`. The retrieved alert body does not add a recovery narrative for this later window. |
| 25–28 July | No rows | Both classes `unknown`. The coverage note does not class these dates as a confirmed outage. The 24 July alert page, as retrieved, does not name 25–29 July. |
| 29 July, before 15:24 UTC | No rows in that interval | Both classes `unknown`. |
| 29 July, after 15:24 UTC | 17,802 rows | Both classes `confirmed_data_available`. Hours with rows: 15–23. |

Source: [`backend/reports/coverage_investigation_2024_07.md`](../backend/reports/coverage_investigation_2024_07.md) and the delivered-date table in [`backend/experiments/C_overpasses/report.md`](../backend/experiments/C_overpasses/report.md).

NOAA-21 on 20 July is a different kind of gap. The file delivered 33,039 rows. UTC hours 08–13 have no rows. Those hours are not labeled an outage, and the day is not an empty day.

Other satellites having rows on a Suomi-NPP gap date does not establish an Suomi-NPP outage, and it does not fill the Suomi-NPP file.

## Thermal measurement caveats

`brightness` is the stored column. VIIRS files are not renamed to `bright_ti4`.

For every July VIIRS archive, the stored maximum brightness is 367 K, no row is above 367 K, and no row falls in [360 K, 367 K). Monthly counts of brightness text exactly `367`, from the monthly exploratory report:

| Archive | `h` on `367` | `l` on `367` | `n` on `367` | Rows above 367 K | Rows in [360 K, 367 K) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Suomi-NPP | 99,752 | 9,011 | 0 | 0 | 0 |
| NOAA-20 | 157,687 | 16,553 | 0 | 0 | 0 |
| NOAA-21 | 189,265 | 17,239 | 0 | 0 | 0 |

The 7 July sample, counted in the anomaly investigation, is the same ceiling at one-day scale: NOAA-20 3,190 rows (3.87%), NOAA-21 7,305 (8.34%), Suomi-NPP 5,600 (6.45%). No row is above 367 K, and no row falls in [360 K, 367 K).

The Collection 2 VIIRS 375 m user's guide, version 1.2, describes 367 K as the nominal I-4 saturation assignment in the typical saturation case. The anomaly investigation separates that document sentence from the rows. Whether each 367 K row is that typical assignment is a hypothesis. The CSVs do not carry a Level-1 saturation flag, so the reports do not mark individual rows as confirmed saturated.

MODIS brightness is a different stored temperature. The 7 July exploratory summary records a Terra maximum of 500 K. The monthly summary records Terra's maximum at 500 K and Aqua's at 510 K. The July Terra FRP maximum, 6,002.5 MW, is stored with brightness 500. Those MODIS values sit above the VIIRS ceiling. They are a different stored temperature, and they are not evidence that a VIIRS file dropped a higher brightness.

`bright_t31` stays under that name. The thermal-field mapping on 7 July compared FIRMS pages, the Earthdata attribute page, and the user's guide. Those documents use `Brightness` / `bright_ti4` / `T4` / `FP_T4` for I-4 and `Brightness_2` / `bright_ti5` / `T5` / `FP_T5` for I-5, and the MODIS page discusses channel 31 beside `bright_t31`. The FIRMS CSV uses `brightness` and `bright_t31`. The comparison does not treat those names as one schema, and it does not apply a scale factor. See [`backend/reports/viirs_thermal_field_mapping_2024_07_07.md`](../backend/reports/viirs_thermal_field_mapping_2024_07_07.md).

FRP at the VIIRS ceiling is not one number. On 7 July, NOAA-20's largest FRP in that one-day archive is 1,168.99 MW and its brightness text is 367. The month maxima for the three VIIRS satellites are 2,825.18 MW (NOAA-20), 2,858.66 MW (NOAA-21), and 2,824.71 MW (Suomi-NPP), each on brightness 367, with confidences `h`, `h`, and `l` respectively. A large FRP on 367 K is a stored pair of columns. It is not, by itself, a confirmed saturated retrieval.

Day and night in the summaries are the stored `daynight` flag, `D` or `N`. They are not recomputed from the clock or from longitude. July day/night totals are in the monthly exploratory report and are the figures transcribed into the sensor screen.

## Candidate spatial-temporal pairs versus confirmed fires

Candidate pairs for July are published in [`backend/reports/spatiotemporal_analysis_2024_07.md`](../backend/reports/spatiotemporal_analysis_2024_07.md). Distance is the great-circle length on a sphere of radius 6,371,008.8 m. The reference sensor's UTC date owns the pair. The other sensor may fall up to the window across midnight. One detection can enter many pairs.

At 1 km and 30 minutes:

| Pair | Compared dates | Excluded dates | Candidate pairs | Reference rows with a candidate |
| --- | ---: | ---: | ---: | ---: |
| Terra and Aqua | 31 | 0 | 5,976 | 3,987 |
| MODIS (Terra and Aqua) and Suomi-NPP | 21 | 10 | 293,942 | 76,889 |
| MODIS (Terra and Aqua) and NOAA-20 | 31 | 0 | 565,132 | 159,844 |
| MODIS (Terra and Aqua) and NOAA-21 | 31 | 0 | 548,204 | 151,724 |
| Suomi-NPP and NOAA-20 | 21 | 10 | 5,138,443 | 1,093,114 |
| Suomi-NPP and NOAA-21 | 21 | 10 | 4,705,012 | 1,044,632 |
| NOAA-20 and NOAA-21 | 31 | 0 | 0 | 0 |

The excluded dates are the ten Suomi-NPP dates with no rows. They are not stored as zero pairs.

NOAA-20 and NOAA-21 have no candidate pairs inside 30 minutes at the published radii. Inside 5 km and 60 minutes, their median time difference falls in the 50–51 minute bin (65,082,849 pairs in that histogram, cited by Experiment C from the candidate-pair report). The shorter window is empty because those acquisitions are farther apart than 30 minutes, not because the report found the rows to be far apart on the ground. That empty window is not a spatial miss, and the 60-minute pairs are still not confirmed fires.

Among pairs inside 5 km and 60 minutes, the median separation falls in the 2,250–2,500 m bin for every published pair. A disk contains more ground toward its outer edge, so that shared bin is not a preferred fire size.

The nearest-neighbor report adds a directed nearest neighbor, a mutual nearest neighbor, and a one-to-one bookkeeping assignment. At 1 km, Terra–Aqua in a 30-minute window matches 3,987 reference rows and leaves 191,329 unmatched. Mutual neighbors are 75.8% of those directed matches. The one-to-one rule can prefer an earlier, longer pair over a later, closer pair. A Hungarian comparison covered at most 80 reference rows and was not expanded to the month. None of these assignments sets `same_fire`. See [`backend/reports/nearest_neighbor_analysis_2024_07.md`](../backend/reports/nearest_neighbor_analysis_2024_07.md).

Within-sensor DBSCAN, at 1 km, 30 minutes, and `min_samples` 4, has published noise shares of Terra 98.2%, Aqua 98.9%, Suomi-NPP 44.4%, NOAA-20 46.3%, and NOAA-21 47.0%. At 375 m and `min_samples` 4, Terra and Aqua are entirely noise. Same-day nearest neighbors are a separate query. The published median same-day nearest distance is 1,026.9 m for Terra, 1,118.2 m for Aqua, and about 380 m for each VIIRS sensor. A neighbor is not a confirmed fire. See [`backend/reports/within_sensor_analysis_2024_07.md`](../backend/reports/within_sensor_analysis_2024_07.md).

The one-day temporal audit is a methodological check on 7 July only. It is not a multi-date validation. Across satellite pairs, the same UTC minute produces zero pairs inside 5 km on that date. Wider windows produce many-to-many pairs. See [`backend/reports/temporal_validation.md`](../backend/reports/temporal_validation.md).

## Unresolved scientific questions

These questions are open because the files or the retrieved documents do not close them.

1. **Processing stream.** The FIRMS download readme says standard-quality data are not yet available from FIRMS for NOAA-20 and NOAA-21, and it does not define `fire_archive_J1V-C2` or `fire_archive_J2V-C2`. The API availability page lists `VIIRS_NOAA20_SP` and `VIIRS_NOAA21_SP`. Neither identifier is a column in the CSVs. The project also does not apply the readme's `fire_archive` mapping to the MODIS or Suomi-NPP filenames. `processing_level` stays `unresolved` for the July tables. No keyed API request was sent, so the standard-processing codes were not asked for a date range.

2. **Product identity of the CSV versus the swath.** `VNP14IMG`, `VJ114IMG`, and `VJ214IMG` are Level-2 swaths. The FIRMS location tables are a different packaging. CMR granule counts are not fire counts. A missing granule is not treated as a FIRMS outage.

3. **Suomi-NPP on 25–28 July, and the hours after 18:22 UTC on 24 July and before 15:24 UTC on 29 July.** The local file has no rows in those intervals. The retrieved alerts do not cover them with an explicit sentence. The class stays `unknown`.

4. **Whether 367 K is saturated on a given row.** The ceiling is observed. The user's guide describes a nominal saturation assignment. The CSV cannot confirm the bit.

5. **Whether `bright_t31` is MODIS channel 31 or VIIRS I-5 in these files.** The column name and the external documents suggest those channels under other names. The mapping report does not merge the schemas.

6. **Whether any candidate pair, neighbor, or cluster is one physical fire.** `same_fire` remains `not_assessed`.

7. **A harmonization coefficient.** None is calculated. July FRP ratios, where published, describe candidate samples whose rows are spatially clustered. They are not a calibration.

8. **A forecast.** The propagation screen is a sketch. XGBoost is not trained. No predictive model is deployed.

9. **MODIS orbit drift.** The historical strategy cites LDOPE known issue `HC_MOD_26008`: Terra and Aqua inclination adjustments were in 2022 and 2021, significant sampling impacts were observed in late 2024, and the effects on MODIS fire products are under investigation. That sentence is an external status report. This repository does not measure the fire-product effect.

10. **What the globe coordinates are.** The 1,484 Cesium points are synthetic illustrative positions for 1–7 July 2024. They are not a sample drawn from the FIRMS latitudes and longitudes, and they must not be validated against the archive as if they were.

The 7 July readiness review ([`backend/reports/data_readiness.md`](../backend/reports/data_readiness.md)) also records fields the one-day files do not carry: product short name, provider checksum, area of interest, production timestamp, and a projection statement inside the file. The download readme describes FIRMS coordinates as WGS84 in general. That general sentence is not a field in the CSV.

## Future harmonization work

The written sequence, from [`backend/research/HISTORICAL_DATA_STRATEGY.md`](../backend/research/HISTORICAL_DATA_STRATEGY.md), [`backend/research/ACQUISITION_PLAN.md`](../backend/research/ACQUISITION_PLAN.md), and [`backend/research/VALIDATION_SAMPLING_STRATEGY.md`](../backend/research/VALIDATION_SAMPLING_STRATEGY.md):

1. Keep the July 2024 CSVs, ZIPs, and experiment outputs unchanged. A new order uses a new directory.
2. Assign a processing stream only when provider metadata, or a document that defines that exact file, names the stream.
3. Acquire one collection per product family. The strategy requests MODIS Collection 6.1 and VIIRS Collection 2 375 m products, and it keeps standard and near-real-time files in separate series. No historical order was submitted. No `MAP_KEY` was stored.
4. Keep Terra and Aqua distinct inside a combined MODIS file. Do not fill a missing platform from another platform.
5. Leave July 2024 out of training, calibration, and validation. The month already has within-sensor, candidate-pair, nearest-neighbor, and experiment results. Reusing it as a fitting sample would treat a studied month as new data.
6. Fit a coefficient, if one is ever fit, on a calibration period, and judge it on a validation period. The training period is reserved for describing distributions and for choosing analysis settings. Those periods are a calendar rule until the files exist. They are not a dataset today.
7. Keep FRP as the candidate measurement. Keep `scan` and `track` as geometry. Keep day/night and satellite as strata. Leave brightness and confidence on their native scales until the quality metadata supports a shared use.
8. Do not train XGBoost, select an H3 resolution, or replace the propagation sketch with a forecast under the current contract.

The globe can show verified coordinates only after those rows are loaded with `source: 'firms'` and with the same detection-versus-fire distinction the reports already use. That connection is future work.
