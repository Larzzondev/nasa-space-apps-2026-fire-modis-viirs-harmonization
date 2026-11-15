# Experiment design

Four investigations can run from the validated July 2024 MODIS and VIIRS archives. This milestone specifies those investigations and the isolated directories they will use. It does not execute them, and it does not harmonize the sensors.

The shared definitions are in [`SHARED_DATA_CONTRACT.md`](SHARED_DATA_CONTRACT.md). Which jobs can run together is in [`DEPENDENCY_GRAPH.md`](DEPENDENCY_GRAPH.md). The comparison table and resource bounds are in [`EXPERIMENT_MATRIX.md`](EXPERIMENT_MATRIX.md).

## What is already measured

These reports stay in place. The experiments cite them and do not overwrite them.

| Question already answered | Report | Use |
| --- | --- | --- |
| Ingestion, checksums, and the rule that an absent date is absent | `reports/ingestion_2024_07.json` | Input contract |
| Daily delivered rows, duplicate keys, and S-NPP zero-row dates | `reports/temporal_coverage_2024_07.md` | Experiment C |
| FIRMS versus Level-2 evidence for the S-NPP gaps | `reports/coverage_investigation_2024_07.md` | Experiment C |
| FRP, brightness, confidence, day/night, and 1° concentration | `reports/monthly_eda_2024_07.md` | Experiments B and D |
| Many-to-many candidate pairs and time-separation bins | `reports/spatiotemporal_analysis_2024_07.md` | Experiment C |
| Directed, mutual, and one-to-one neighbors, plus positive-FRP ratios | `reports/nearest_neighbor_analysis_2024_07.md` | Experiment B |
| Within-sensor neighbors and DBSCAN, including the seven full-month settings and the 27-cell representative-date factorial | `reports/within_sensor_analysis_2024_07.md` | Experiments A and D |

The full-month pair indexes are expensive. Experiment A in the first batch reuses the published DBSCAN settings. It does not build a second full-month graph. A configuration may later select `full_month_rebuild`, which is a separate scope with the cost class recorded in the matrix. That scope is not the default.

## Execution architecture

Each experiment is one configuration file:

- [`examples/experiment_a.json`](examples/experiment_a.json)
- [`examples/experiment_b.json`](examples/experiment_b.json)
- [`examples/experiment_c.json`](examples/experiment_c.json)
- [`examples/experiment_d.json`](examples/experiment_d.json)

`fire_data.experiments` validates a configuration and can prepare a run directory. Preparation does not open the CSVs. The scientific functions themselves are not in this milestone, so a prepared manifest has `science_executed: false` and `results: null`.

From `backend/`:

```bash
.venv\Scripts\python -m fire_data.experiments validate research\examples\experiment_a.json
.venv\Scripts\python -m fire_data.experiments prepare research\examples\experiment_a.json --run-id batch-1
.venv\Scripts\python -m pytest tests\test_experiment_framework.py
```

`prepare` writes only:

```text
experiments/<experiment_id>/runs/<run_id>/config.json
experiments/<experiment_id>/runs/<run_id>/manifest.json
```

The default work root is `backend/`. Run directories are gitignored. An existing run id is left untouched. Configurations cannot set `overwrite` to true, cannot point one experiment at another's directory, and cannot name `data/` or `reports/` as the output directory.

A future scientific module must:

1. Validate its configuration with the schema.
2. Refuse to start unless `same_fire` is `not_assessed` and the other scientific locks hold.
3. Open the four CSVs read-only and check the SHA-256 and row counts in the configuration before interpreting a result.
4. Leave a date with no rows out of every denominator.
5. Write figures, metrics, and the completed manifest only under that run directory.
6. Record the Python, NumPy, SciPy, Matplotlib, and pytest versions, the git commit, the configuration hash, and the measured timing fields it actually collects.
7. Leave `science_wall_clock_seconds`, `cpu_seconds`, and `peak_working_set_bytes` null when the operating system or the run did not measure them.

Separate Git worktrees can each check out this repository and prepare a different experiment id. The CSVs are gitignored, so a new worktree does not contain them. Execution, when it is added, must be given the existing read-only monthly directory. Copying the CSVs in order to edit them is out of contract. Preparation itself does not need the CSVs, which is what the tests check.

Suggested worktree layout, from the repository root:

```bash
git worktree add ..\worktrees\exp-a -b experiment-a
git worktree add ..\worktrees\exp-b -b experiment-b
git worktree add ..\worktrees\exp-c -b experiment-c
git worktree add ..\worktrees\exp-d -b experiment-d
```

Each worktree prepares only its own id. None of them writes `reports/within_sensor_analysis_2024_07.json` or the other protected reports listed in the schema.

## Experiment A: spatial-temporal clustering

### Question

How stable are the within-sensor analytical components when the neighborhood changes, and which of those changes are only the midnight margin?

### What is reused

The seven full-month DBSCAN settings and the 27-cell factorial on the representative dates. Noise shares, owned sizes, and the rule that partition counts are not additive are already published. The first-batch configuration sets `execution_scope` to `published_baseline_plus_representative_date`.

### What is investigated

On each satellite's representative date, and only on that date for any new labeling:

- **DBSCAN, as already defined.** Core rows are connected components of the spatial-temporal neighborhood. `min_samples` includes the row. This remains the baseline. Single-linkage at one radius on that same graph is the same core structure, so it is not a second algorithm.
- **Border assignment.** The published rule gives a border row to the neighboring core component with the smallest core index. The sensitivity check is how many border rows would move if that tie-break changed. The result is a count of label changes. It is not a better fire map.
- **Same-minute components.** The published 0-minute setting is the archived minute. The new comparison is restricted to the representative date and asks how much of the 30-minute component structure is already present at that minute.
- **Margin-only neighbors.** Count owned rows whose in-window neighbor exists only because of the 180-minute adjacent-date margin. That count is the cross-midnight continuity question. Those rows do not merge the two dates into one component inventory.
- **Noise-label stability.** Compare noise versus not-noise between two settings on the same rows. Report the share of rows whose noise label flips. Do not treat cluster identifiers as stable across dates, because the partitions are separate and the counts are not additive.

Alternative methods that need a new dependency are out of scope. scikit-learn DBSCAN and a Euclidean ball in scaled latitude, longitude, and time stay rejected.

Satellites are not pooled. Terra's same-day nearest median is about 1.0 km and the VIIRS medians are about 380 m, so one radius is a different relative scale on MODIS than on VIIRS. Results stay per satellite.

### Acceptance

- The run directory is `experiments/A/runs/<run_id>/` and does not replace the within-sensor report.
- `same_fire` is `not_assessed`. `clusters_are_confirmed_fires` is false.
- Empty S-NPP dates are absent, not zero cluster counts.
- `min_samples` still includes the row, and the report says so.
- The representative dates match the published dates.
- The earth radius is 6,371,008.8 m and the distance is the great-circle length from the ECEF chord.
- No harmonization coefficient is written.

### Reproducibility

Validate and prepare with the commands above and `research/examples/experiment_a.json`. A future execution reads the July CSVs through the existing loader, checks the manifest row counts, and labels only the representative dates unless the configuration explicitly says `full_month_rebuild`.

## Experiment B: sensor measurement relationships

### Question

How do FRP, brightness, scan, track, and day/night differ among the five satellites, and which of those differences are already visible inside the published positive-FRP ratios?

### What is reused

Monthly FRP, brightness, confidence, and day/night summaries. The directed nearest-neighbor FRP ratios at the published radii, which are descriptive samples and not coefficients. At 1 km, examples of those published median ratios include Terra/Aqua 1.031, MODIS/S-NPP 0.327, MODIS/NOAA-20 0.366, MODIS/NOAA-21 0.422, S-NPP/NOAA-20 1.029, S-NPP/NOAA-21 1.301, and NOAA-20/NOAA-21 1.219. The ratio is partner divided by reference, and only when both FRP values are positive.

### What is investigated

New conditional distributions, without a fitted slope or intercept:

- FRP quantiles by satellite, including non-positive values, then split by day/night and by scan quartile.
- Brightness quantiles on the same strata. The VIIRS 367 K value stays a stored value. Rows at that value are counted. They are not marked confirmed saturated.
- Scan and track on the same strata, so a larger FRP can be read against a larger pixel instead of being treated as a larger fire.
- The published day/night pair labels (`D-D`, `D-N`, `N-D`, `N-N`) cited as stored flags of the two rows, not as a shared fire.
- Native confidence on its own scale. MODIS class bins may be repeated only as the published 0–29, 30–79, and 80–100 reporting split.

Terra and Aqua are reported separately. A cited pair that was published as `MODIS (Terra and Aqua)` keeps that label.

`type` may be counted as the stored codes 0, 1, 2, and 3. Those codes are not given new names. `bright_t31` is not renamed and is not entered into a coefficient.

### Acceptance

- `estimate_calibration_coefficient` and `fit_regression` remain false.
- Quantiles that claim to describe all rows include non-positive FRP, and the count of excluded non-positive pairs is reported beside any ratio.
- Confidence scales are not converted.
- `brightness_367_is_confirmed_saturation` is false.
- `same_fire` is `not_assessed`.
- The output directory is `experiments/B/runs/<run_id>/`.

### Reproducibility

Validate and prepare `research/examples/experiment_b.json`. A future execution is a single pass over the five satellite tables plus citation of the nearest-neighbor JSON. It does not refit the one-to-one assignment and does not train a model.

## Experiment C: temporal sampling and overpass analysis

### Question

How far apart are the acquisitions, how often does each satellite report, and which detection comparisons are unavailable because a date or an hour has no rows?

### What is reused

The daily delivered-row matrix. The S-NPP zero-row dates and the partial dates 16, 24, and 29 July. The coverage investigation's separation of FIRMS evidence from Level-2 evidence. The published time-difference bins, including Terra–Aqua at 17–18 minutes inside 5 km and 60 minutes, and NOAA-20–NOAA-21 at 50–51 minutes inside that same window.

### What is investigated

- The distribution of archived UTC minutes by satellite and by date: how many distinct `acq_time` values occur, and which hours have rows.
- The gap between consecutive distinct acquisition minutes of the same satellite. That gap describes the stored clock. It is not an orbital element retrieved from a spacecraft ephemeris, and the files do not contain one.
- The time-separation distributions already published, cited rather than recomputed, plus any finer split that still uses the archived minute.
- The set of reference rows that cannot be compared on a date because the other sensor has no rows that date. S-NPP's ten zero-row dates are the main case. They reduce the compared-date count from 31 to 21 wherever S-NPP is one side.
- Hour gaps inside a delivered day, such as NOAA-21 on 20 July, reported as hours without rows. They are not given an outage class unless a cited alert already supports that class.
- The effect of the 30-minute and 60-minute windows on NOAA-20 versus NOAA-21: the 30-minute window is empty because the acquisitions are about 50 minutes apart.

Partial S-NPP intervals are not repaired. FIRMS class and Level-2 class stay in separate columns when both are cited.

### Acceptance

- `fill_absent_dates`, `absent_date_is_zero_fire`, and `repair_partial_delivery` are false.
- A comparison is computed only when both sensors have at least one row on that UTC date.
- The clock is UTC and the resolution is one minute.
- `same_fire` is `not_assessed`. A short time gap is not identity.
- The output directory is `experiments/C/runs/<run_id>/`.

### Reproducibility

Validate and prepare `research/examples/experiment_c.json`. A future execution reads acquisition dates and times. It does not download a replacement S-NPP archive and does not call the FIRMS API.

## Experiment D: spatial resolution and aggregation

### Question

How large are the stored MODIS and VIIRS footprints in this month, how uneven is the geographic sample, and which aggregation methods are even candidates?

### What is reused

Published scan and track medians: Terra scan 1.20 km and track 1.10 km, Aqua scan 1.30 km and track 1.10 km, and each VIIRS sensor scan and track about 0.44 km. The 1° concentration counts and the 2° occupancy counts. The statement that equal-degree cells are not equal-area cells. The statement that search radii are not footprints.

### What is investigated

- The distribution of `scan`, `track`, and the product `scan * track` in square kilometres, by satellite. The product is a stored-size proxy, not a measured ground polygon. The product of the medians is not reported as the median of the products.
- How that product grows away from the small end of the scan distribution. Scan and track are already in kilometres and increase off nadir. The experiment describes that growth. It does not invent a scan angle the file does not contain.
- Geographic sampling on the existing 1° and 2° grids, with row counts and with the spherical zone rate from `cell_area_km2`. High-latitude cells are smaller. A raw count is not a density.
- Candidate aggregation methods, none of them selected:
  - equal-degree 1° cells
  - equal-degree 2° cells
  - the same cells converted with the spherical zone area
  - H3 cells as an unselected candidate

H3 is not installed and is not required. No resolution is chosen. If a later run imports an H3 library, it must read that library's average cell area at the resolutions it tries and compare those areas with the observed `scan * track` distribution. A resolution is not selected inside this experiment. `h3_selected` stays false.

An aggregation cell is not an analytical cluster, and neither is a fire. Experiment D does not relabel Experiment A's components.

### Acceptance

- `h3_selected` is false and `h3_library_required` is false.
- `thresholds_are_sensor_footprints` is false.
- `equal_degree_cells_are_equal_area` is false.
- `product_of_medians_is_median_of_products` is false.
- The footprint proxy is the distribution of `scan * track`, not a single adopted cell size.
- `same_fire` is `not_assessed`.
- The output directory is `experiments/D/runs/<run_id>/`.

### Reproducibility

Validate and prepare `research/examples/experiment_d.json`. A future execution can compute the footprint proxy in one pass. It must not add the `h3` package in order to make the candidate look selected.

## Milestone acceptance

This milestone is accepted when all of the following hold:

- The schema loads and uses only keywords the in-repo validator implements.
- All four example configurations validate.
- The four configurations share one input contract and write to four different directories.
- Archive row counts match `EXPECTED_ROWS`, and archive checksums match `reports/ingestion_2024_07.json`.
- Experiment A's earth radius equals `EARTH_RADIUS_M`, and its representative dates equal `reports/milestones/milestone_09_metrics.json`.
- Configurations that set a same-fire label, a filled date, a coefficient, an XGBoost flag, a crossed output directory, a calibration slope, a filled S-NPP date, or a selected H3 resolution are rejected.
- `prepare` writes `config.json` and `manifest.json`, reads zero source rows, and refuses to overwrite an existing run.
- The existing pytest suite passes.
- No raw CSV, ZIP, or credential file is added to Git.

The commands that check this are in the architecture section above, together with `python -m pytest` from `backend/`.
