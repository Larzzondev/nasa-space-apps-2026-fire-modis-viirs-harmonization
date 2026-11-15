# Shared data contract

This contract is the common language for the four July 2024 experiments. It records definitions that the existing ingestion, coverage, exploratory, candidate-pair, nearest-neighbor, and within-sensor work already use. It does not add a harmonization coefficient, a same-fire decision, or a repaired S-NPP day.

The machine-checked form is [`experiment_config.schema.json`](experiment_config.schema.json). The four example configurations in [`examples/`](examples/) are valid instances. A prepared run writes `manifest.json`, which must validate against `#/$defs/experimentRun`.

## Authority and immutability

The scientific inputs are the four extracted FIRMS CSVs under `backend/data/raw/monthly_2024_07/` and the ingestion manifest `backend/reports/ingestion_2024_07.json`. Experiments open those CSVs read-only. They do not write beside them, do not replace them, and do not write into `backend/reports/` files that already record a completed analysis.

| Sensor | CSV | Rows | SHA-256 | Stored instrument | Version text | Confidence |
| --- | --- | ---: | --- | --- | --- | --- |
| modis | `modis/fire_archive_M-C61_850319.csv` | 676,636 | `97e1a4312fbe488e63fd06461865b21dd5d01c419f2e80fa6e178c0015f10c81` | MODIS | 61.03 | `modis_0_100` |
| viirs_snpp | `viirs_snpp/fire_archive_SV-C2_850322.csv` | 1,635,020 | `bc5ff311c2df9113baf4eedaf4247d55954e8f4fa2ca052f940a943365314f21` | SNPP | 2 | `viirs_lnh` |
| viirs_noaa20 | `viirs_noaa20/fire_archive_J1V-C2_850320.csv` | 2,902,597 | `9a192db30e307c257955047ca1177e3f2f463b8c8cdfda7b28ceac6b3aa92bd5` | VIIRS | 2 | `viirs_lnh` |
| viirs_noaa21 | `viirs_noaa21/fire_archive_J2V-C2_850321.csv` | 2,771,214 | `c86e46d4ca730eea6db448ff928126ddc6b44ba4c4d11dfbc3a2d999f4937007` | VIIRS | 2 | `viirs_lnh` |

Total delivered rows: 7,985,467. Terra 195,316 and Aqua 481,320 come from the MODIS file. Each VIIRS file contributes one satellite. `processing_stream` stays null. The filename prefix and the version text are not a processing level.

The header on every file is:

`latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight,type`

The first data row of each monthly file stores the instrument and version text in the table above. That check read four rows. It is not a new full-column audit. The one-day source contract already required these instrument strings, and the July loader keeps the instrument value it reads.

## Observation and detection

An **observation** is one stored CSV row: one source file, one line, and the fifteen stored fields. The row is immutable. Exact duplicate rows are retained. The July temporal scan found 0 extra full lines and 5 extra location-time keys (1 in NOAA-20, 4 in NOAA-21). Those keys stay in the data.

A **detection**, in this repository, is that same archived row read as one sensor's hot-spot record at one acquisition minute. It is not a physical fire, not a polygon footprint, and not a unique event across overpasses. Counting detections counts rows. A denser sensor is not, by that count, a better sensor.

## Satellite and instrument identity

Satellites stay separate unless a published pair label explicitly groups them.

| Stored `satellite` | Display name | Archive | Stored `instrument` |
| --- | --- | --- | --- |
| Terra | Terra | MODIS | MODIS |
| Aqua | Aqua | MODIS | MODIS |
| SNPP | S-NPP | VIIRS S-NPP | SNPP |
| N20 | NOAA-20 | VIIRS NOAA-20 | VIIRS |
| N21 | NOAA-21 | VIIRS NOAA-21 | VIIRS |

Terra and Aqua are not pooled in within-sensor clustering. Some candidate-pair and nearest-neighbor tables use the label `MODIS (Terra and Aqua)` while each row keeps its own satellite. An experiment that cites those tables must keep that label visible. It must not silently replace Terra and Aqua with one instrument.

S-NPP's stored instrument is `SNPP`, not `VIIRS`. A display family of "VIIRS" may be stated beside the stored value. The stored value is not rewritten.

NOAA-20 and NOAA-21 processing level is unresolved. The local filenames use `fire_archive`, while the FIRMS download readme says standard-quality data are not yet available for those sensors. The version column is not used as a processing stream.

## Acquisition timestamp and UTC

`acq_date` is `YYYY-MM-DD`. `acq_time` is `HHMM`. Both are UTC. The files have no seconds. A difference of zero minutes means the same archived minute. It does not prove the same instant.

The July analysis epoch is minutes from 2024-07-01 00:00 UTC:

`(day_of_month - 1) * 1440 + hour * 60 + minute`

That epoch is defined only inside this July extract. It is not a Unix timestamp. June 30 and August 1 are outside the extract. A missing neighbor on those dates is null, not zero.

A 0-minute window is the archived `acq_time`. Wider windows are search limits. They are not statements that two sensors observed together. The reference sensor's UTC date owns a cross-sensor pair. The other sensor may fall inside the window across midnight. One row is not copied into a second date.

Within-sensor DBSCAN uses one UTC date plus rows from the adjacent dates whose clocks fall inside a 180-minute margin. Margin rows are context. They are not counted again as reference rows. Cluster counts from those partitions are not additive and are not a month-long census.

## FRP and brightness

FRP is the stored fire radiative power in megawatts. It is not fire size and it is not total fire energy. Quantiles keep zero and negative values. No FRP filter removes them from a distribution.

A ratio of two FRP values, when one is reported, is the other sensor's FRP divided by the reference sensor's FRP, and only when both values are positive. Non-positive rows stay in the match counts and are counted as excluded from the ratio. A ratio quantile is not a confidence interval and not a harmonization coefficient. The paired rows are spatially clustered.

`brightness` is the stored column. VIIRS files are not renamed to `bright_ti4`. In the July VIIRS archives the stored maximum is 367 K, no row is above 367 K, and no row falls in [360 K, 367 K). Every stored `h` flag sits on brightness text `367`, and some `367` rows are `l`. The CSVs have no Level-1 saturation flag, so 367 K is not marked as confirmed saturation. MODIS brightness is a different stored temperature and can exceed 367 K.

`bright_t31` stays under that column name. These files do not say whether it is MODIS channel 31 or VIIRS I-5.

## Native confidence

MODIS confidence is the stored integer from 0 through 100, including 0. VIIRS confidence is the stored flag `l`, `n`, or `h`. The scales are not converted into one score.

The nearest-neighbor report also splits MODIS into the published classes 0–29, 30–79, and 80–100. That split is a reporting partition. It is not a second product and it is not comparable to `l`, `n`, or `h`.

Inside `ObservationTable`, day/night is encoded as 0 for `D` and 1 for `N`, and a VIIRS flag is encoded as an index into `l`, `n`, `h`. Those integers are an in-memory index. They are not MODIS confidence. Outputs that report confidence or day/night use the stored labels, or they state the encoding.

## Spatial distance and Earth model

Distances use a sphere of radius 6,371,008.8 m, the constant `EARTH_RADIUS_M` in `fire_data.eda_spatial`. Latitude and longitude become Earth-centered coordinates on that sphere. A `scipy.spatial.cKDTree` searches the chord length. The reported separation is the great-circle length recovered from the chord:

`2 * R * arcsin(chord / (2 * R))`

The same radius is used by the haversine helper. Search radii are not sensor footprints. A 1 km threshold is not a MODIS pixel, and a 375 m threshold is not a VIIRS pixel.

Equal-degree cells are not equal-area cells. The spherical zone area used for a rate is the existing `cell_area_km2` calculation on this same sphere. A count in a 1° or 2° cell is a count of archived rows, not a count of fires. The median separation inside a 5 km window falls in the 2,250–2,500 m bin for every published pair. A disk contains more ground toward its outer edge, so that shared bin is not a preferred fire size.

Candidate-pair search is partitioned into 20° tiles so the full distance matrix is not built.

## Missing and incomplete coverage

A date is described by the file, not by a filled value.

| Status | Meaning |
| --- | --- |
| `rows_delivered` | The CSV has at least one row with that acquisition date. |
| `zero_rows_delivered` | The CSV is present and has no row with that date. The delivered-row count is zero. That is not zero fire activity. |
| `source_file_missing` | The CSV itself is absent. There is no delivered-row count. |

S-NPP dates with zero delivered rows are 10–15 July and 25–28 July 2024. They stay out of denominators. They are not filled from NOAA-20, NOAA-21, Terra, or Aqua, and they are not given a cluster count of zero.

S-NPP delivery on 16, 24, and 29 July is partial. Those dates are used only where rows are present. The coverage investigation keeps FIRMS evidence and Level-2 swath evidence separate. `confirmed_source_unavailable` is used only where an LP DAAC sentence covers the stated interval, and it is not extended past that sentence. It is not automatically a FIRMS outage. Cataloged `VNP14IMG` granules that were not opened do not become fire counts.

July 31 has no next-date neighbor inside this extract, because 1 August is outside it. That exclusion is not a zero-detection day. NOAA-21 on 20 July has delivered rows and also has UTC hours with no rows. Those hour gaps are not labeled as an outage.

A cross-sensor date is compared only when both sides have at least one row that UTC date.

## Candidate pair

A candidate pair is two archived rows, from two named sensors, whose great-circle separation and acquisition-time difference fall inside a stated threshold. One detection can belong to many pairs. The pair count is not a fire count. A candidate pair does not prove that the two rows observe the same fire.

Published search radii are 375 m, 750 m, 1 km, 2 km, and 5 km. Published windows are 5, 15, 30, and 60 minutes. NOAA-20 and NOAA-21 have no candidate pairs inside 30 minutes. Inside 5 km and 60 minutes their median time difference falls in 50–51 minutes. The shorter windows are empty because those acquisitions are farther apart than 30 minutes, not because the rows are far apart on the ground.

## Analytical cluster

An analytical cluster is a DBSCAN component on one UTC-date partition, using the joint neighborhood of a spatial radius and a time window. `min_samples` includes the row itself. Core rows form connected components. A border row is assigned to the neighboring component whose lowest core index is smallest. Label `-1` is noise.

The published full-month settings are the seven settings around 1 km, 30 minutes, and `min_samples` 4. The 27-cell factorial was limited to one representative date per satellite: the earliest date whose row count is closest to the median of dates that contain rows. Those dates are Terra 2024-07-12, Aqua 2024-07-19, S-NPP 2024-07-30, NOAA-20 2024-07-29, and NOAA-21 2024-07-07.

At 1 km, 30 minutes, and `min_samples` 4, the published noise shares are Terra 98.2%, Aqua 98.9%, S-NPP 44.4%, NOAA-20 46.3%, and NOAA-21 47.0%. At 375 m and `min_samples` 4, Terra and Aqua are entirely noise and the VIIRS sensors are about 98% noise. A component is not a confirmed fire. Partition cluster-count sums are not additive.

scikit-learn is not a project dependency. A Euclidean ball in scaled latitude, longitude, and time is not the neighborhood. The neighborhood is a spatial radius combined with a time window.

Same-day nearest neighbors are a separate query. They are not clusters and they are not same-fire matches. The published median same-day nearest distance is 1,026.9 m for Terra, 1,118.2 m for Aqua, and about 380 m for each VIIRS sensor.

## Same-fire status

`same_fire` is `not_assessed` on every experiment configuration, every run manifest, and every existing July scientific report that states the field. No row is labeled as the same fire as another row.

These statements remain false:

- A nearest neighbor is the same fire.
- A mutual nearest neighbor is the same fire.
- A one-to-one assignment is the same fire.
- A candidate pair is the same fire.
- An analytical cluster is the same fire.
- Temporal separation, or the lack of it, establishes the same fire.
- Spatial proximity establishes the same fire.

The one-to-one rule used in the nearest-neighbor report is bookkeeping. Within each UTC date it takes eligible pairs in order of increasing separation, and a detection used on an earlier date stays used. A later, closer pair can lose to an earlier, longer pair. The Hungarian comparison covered at most 80 reference rows. It was not expanded to the month.

## Fields the analysis table does not carry per row

`ObservationTable` carries satellite, instrument, confidence scale, July day, minute, latitude, longitude, FRP, brightness, scan, track, encoded day/night, and encoded confidence. The within-sensor duplicate inventory omits `version`, `type`, and `bright_t31`. The July temporal scan remains the authority for exact CSV duplicates.

`type` stores 0, 1, 2, or 3. This repository has not assigned those codes a land-cover name and has not dropped a class. An experiment may count the stored codes. It may not invent a class name the file does not contain.

## Shared output record

A prepared or completed run writes only under `experiments/<experiment_id>/runs/<run_id>/`. The directory is created only if it does not already exist. The manifest includes:

- `same_fire`: `not_assessed`
- `harmonization_coefficient`: null
- `xgboost_trained`: false
- `missing_dates_filled`: false
- `processing_level`: `unresolved`
- `science_executed`: false until an experiment is actually run
- `results`: null while science has not been executed
- `source_rows_read` and `records_processed`: measured counts, which are 0 for preparation
- software versions for Python, NumPy, SciPy, Matplotlib, and pytest, plus `git_commit` when `git rev-parse HEAD` returns a 40-character commit and null when it does not
- `timing.science_wall_clock_seconds`, `cpu_seconds`, and `peak_working_set_bytes`: null when those quantities were not measured

Unmeasured timing stays null. It is not stored as zero.

## What this contract does not authorize

- Modifying original observations.
- Filling missing S-NPP dates or repairing 16, 24, or 29 July.
- Treating proximity, a cluster, or an assignment as the same physical fire.
- Inferring NOAA-20 or NOAA-21 processing level.
- Calculating a final harmonization coefficient or fitting a regression to stand in for one.
- Training XGBoost.
- Selecting an H3 resolution.
- Pooling Terra and Aqua without the published pair label.
- Converting confidence scales.
- Calling a stored brightness of 367 K a confirmed saturated pixel.
