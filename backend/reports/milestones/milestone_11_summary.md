# Milestone 11: first experiment batch

Experiments A, B, C, and D read the same July 2024 CSVs and wrote separate directories. No source row was edited. No missing S-NPP date was filled. No harmonization coefficient was calculated. `same_fire` remains `not_assessed`.

## Completion

| Experiment | Status | Records processed | Wall clock (s) | Peak working set (bytes) |
| --- | --- | ---: | ---: | ---: |
| A | completed | 284355 | 22.166 | 256012288 |
| B | completed | 7985467 | 29.243 | 505827328 |
| C | completed | 7985467 | 19.108 | 116903936 |
| D | completed | 7985467 | 23.274 | 494911488 |

## Experiment A

The seven full-month settings were cited and not fit again. The representative-date factorial matches the published report: True. Component labels are analytical ids inside one date. They are not fire ids.

| Satellite | Owned rows | Primary noise share | Border rows that change | Margin-only rows at 30 min |
| --- | ---: | ---: | ---: | ---: |
| Terra | 6162 | 0.996 | 1 | 0 |
| Aqua | 15517 | 0.986 | 2 | 0 |
| S-NPP | 82443 | 0.527 | 21 | 0 |
| NOAA-20 | 92596 | 0.544 | 25 | 0 |
| NOAA-21 | 87637 | 0.422 | 39 | 5 |

## Experiment B

All-row quantiles keep non-positive FRP. Positive-only quantiles are separate. Published 1 km ratios were cited and were not refit. No slope or intercept was estimated.

| Satellite | FRP p50 (MW) | Non-positive FRP | Scan p50 (km) | Day FRP p50 | Night FRP p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Terra | 19.100 | 393 | 1.200 | 19.200 | 19.100 |
| Aqua | 21.600 | 155 | 1.300 | 21.900 | 18.400 |
| S-NPP | 5.060 | 373 | 0.440 | 7.030 | 1.770 |
| NOAA-20 | 5.140 | 809 | 0.440 | 7.040 | 1.780 |
| NOAA-21 | 6.090 | 1710 | 0.440 | 8.480 | 2.090 |

## Experiment C

Comparisons use a UTC date only when both satellites have rows. The closest stored minute ignores location and is not a fire match. The 5 km, 60 minute candidate-pair time bins are cited, not rebuilt.

NOAA-20 and NOAA-21 have 31 compared dates. Their closest-minute median is 0.0 minutes. That number is not the spatially constrained pair separation.
The published NOAA-20/NOAA-21 candidate pairs inside 5 km and 60 minutes have a median time bin of 50.0–51.0 minutes. A 30-minute window is empty for that couple because those acquisitions are farther apart than 30 minutes, not because the rows fail a spatial test.

## Experiment D

scan and track are stored lengths in kilometres. Their product treats those lengths as the sides of a rectangle. The archive does not include the pixel polygon, the scan angle, or the ground orientation. Adjacent-scan overlap and Earth curvature inside the pixel are not corrected. scan multiplied by track is a stored-size proxy, not an exact physical pixel area.

H3 selected: False. The h3 package is not installed. No average cell area was read from the library, and none was invented.

| Satellite | Median of scan × track (km²) | Product of medians (km²) | 1° count cell is the rate cell | High-latitude row share |
| --- | ---: | ---: | --- | ---: |
| Terra | 1.320 | 1.320 | True | 0.145 |
| Aqua | 1.430 | 1.430 | False | 0.052 |
| S-NPP | 0.198 | 0.194 | True | 0.072 |
| NOAA-20 | 0.198 | 0.194 | True | 0.080 |
| NOAA-21 | 0.199 | 0.198 | True | 0.081 |

## Cross-experiment findings

A 375 m neighborhood and a 1 km neighborhood are different relative scales once the stored sizes are visible. MODIS median `scan × track` is near 1 km², while each VIIRS median is well below that. Experiment A's published full-month baseline already shows Terra and Aqua entirely in noise at 375 m, while the VIIRS sensors are not. Those two results describe archived rows. They do not say which sensor detects fires better.

Experiment B's scan-quartile medians are the place to read a larger FRP against a larger stored pixel. Experiment D says that stored pixel is a rectangle proxy. Neither result is a calibration slope.

Experiment A can use a 30-minute window inside one satellite. Experiment C shows why that same window is the wrong description of NOAA-20 versus NOAA-21: their spatially constrained pairs sit near 50 minutes. A 30-minute cross-sensor window looks like a miss for a reason that belongs to the clock.

S-NPP's empty dates are absent in every experiment. They are not zero clusters, zero FRP, or zero density.

## Limits

- Candidate pairs, nearest neighbors, and analytical components are not confirmed fires.
- NOAA-20 and NOAA-21 processing level stays unresolved.
- XGBoost was not trained.
- H3 was not selected.

## Next research milestone

On the representative dates, the 1 km and 30 minute margin-only share stays at or below 0.0001. A full-month rebuild aimed at that midnight question is not the next measurement. The next research milestone should keep `same_fire` at `not_assessed`, leave the S-NPP gaps empty, and decide whether the representative-date noise sensitivity is enough to justify one full-month pass of the border and noise-label questions. That pass is still not a harmonization and not an H3 selection.

Batch wall clock: 283.533 seconds. Active execution, the sum of the measured command durations: 212.730 seconds.
