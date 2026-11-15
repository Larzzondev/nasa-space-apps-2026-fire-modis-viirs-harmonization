# Experiment A: spatial-temporal clustering

Question: how stable are the within-sensor analytical components on the representative date when the neighborhood or the border rule changes, and how much of that neighborhood exists only because of the midnight margin?

Scope: `published_baseline_plus_representative_date`. The seven full-month settings are cited. They were not fit again. New labels cover one UTC date per satellite plus the 180-minute adjacent-date margin. `full_month_rebuild` was not run.

`same_fire` is `not_assessed`. A component id is an analytical label inside one date partition. It is not a fire identifier. Partition counts are not additive and are not a monthly fire total.

Distance is the great-circle length recovered from the ECEF chord on a sphere of radius 6371008.8 m. `min_samples` includes the row.

## Representative dates

| Satellite | Date | Owned rows | Margin context rows | Dates without rows | Factorial matches published |
| --- | --- | ---: | ---: | ---: | --- |
| Terra | 2024-07-12 | 6162 | 1437 | 0 | True |
| Aqua | 2024-07-19 | 15517 | 1799 | 0 | True |
| S-NPP | 2024-07-30 | 82443 | 7587 | 10 | True |
| NOAA-20 | 2024-07-29 | 92596 | 13106 | 0 | True |
| NOAA-21 | 2024-07-07 | 87637 | 8670 | 0 | True |

Dates without rows stay out of the cluster denominators. They are not entered as zero clusters. S-NPP's empty dates are in that satellite's list when the file has no row for them.

## Published full-month baseline

These noise shares are copied from the within-sensor report. This run did not recompute them.

| Satellite | 375 m / 30 min | 1 km / 30 min | 2 km / 30 min | 1 km / 0 min | 1 km / 180 min | min_samples 2 | min_samples 8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra | 1.000 | 0.982 | 0.676 | 0.982 | 0.949 | 0.738 | 1.000 |
| Aqua | 1.000 | 0.989 | 0.751 | 0.989 | 0.975 | 0.753 | 1.000 |
| S-NPP | 0.982 | 0.444 | 0.376 | 0.446 | 0.405 | 0.186 | 0.710 |
| NOAA-20 | 0.983 | 0.463 | 0.391 | 0.465 | 0.425 | 0.202 | 0.726 |
| NOAA-21 | 0.982 | 0.470 | 0.396 | 0.472 | 0.431 | 0.210 | 0.729 |

The 1 km, 30 minute, `min_samples` 4 column is the primary setting. At 375 m the published MODIS noise share is 1. Terra and Aqua are not pooled, because a 375 m radius is a different relative scale on MODIS than on VIIRS.

## Representative-date factorial

The 27 cells were labeled again from the July CSVs and compared with the published representative-date factorial. A match is an exact match of owned rows, noise rows, clustered rows, and the partition component count.

| Satellite | Primary noise share | Primary components | Primary clustered rows |
| --- | ---: | ---: | ---: |
| Terra | 0.996 | 5 | 22 |
| Aqua | 0.986 | 31 | 217 |
| S-NPP | 0.527 | 4876 | 39012 |
| NOAA-20 | 0.544 | 5379 | 42201 |
| NOAA-21 | 0.422 | 5075 | 50628 |

Noise share moves with radius, window, and `min_samples`. The factorial table in `results.json` is the sensitivity record. Component ids are not aligned across those cells.

## Border assignment

The published rule gives a border row to the neighboring core component with the smallest core index. The alternate rule uses the largest core index. The count below is the number of owned border rows whose label changes. It is not a better fire map.

| Satellite | Border rows | Border rows that change | Core rows whose label changes |
| --- | ---: | ---: | ---: |
| Terra | 16 | 1 | 0 |
| Aqua | 128 | 2 | 0 |
| S-NPP | 3713 | 21 | 0 |
| NOAA-20 | 4532 | 25 | 0 |
| NOAA-21 | 4514 | 39 | 0 |

## Same archived minute

The 0-minute window is the archived `acq_time`. The comparison asks how much of the 30-minute component structure, at 1 km and `min_samples` 4, is already present at that minute.

| Satellite | Clustered at 30 min | Also clustered at 0 min | Share | Components that stay one 0-minute component |
| --- | ---: | ---: | ---: | ---: |
| Terra | 22 | 22 | 1.000 | 5 |
| Aqua | 217 | 217 | 1.000 | 31 |
| S-NPP | 39012 | 38836 | 0.995 | 4820 |
| NOAA-20 | 42201 | 42004 | 0.995 | 5320 |
| NOAA-21 | 50628 | 50462 | 0.997 | 5007 |

## Cross-midnight margin

A margin-only row has at least one neighbor inside the stated radius and window on an adjacent date, and no neighbor inside that same limit on its own date. Those rows are context. They are not copied into a second date and they do not add the two dates into one component inventory.

| Satellite | 0 min | 30 min | 180 min |
| --- | ---: | ---: | ---: |
| Terra | 0 | 0 | 1 |
| Aqua | 0 | 0 | 0 |
| S-NPP | 0 | 0 | 134 |
| NOAA-20 | 0 | 0 | 138 |
| NOAA-21 | 0 | 5 | 85 |

## Noise-label stability

Each published one-factor setting is compared with the primary setting on the same owned rows. The share is the fraction of rows whose noise label flips. Cluster ids are not treated as the same object across settings.

The per-setting shares are in `results.json` under `noise_label_stability_against_primary`.

## Limits

- No row is labeled the same fire as another row.
- Empty dates are absent. They are not zero-fire days and they were not filled.
- NOAA-20 and NOAA-21 processing level stays unresolved.
- No harmonization coefficient was calculated. XGBoost was not trained.
- scikit-learn DBSCAN was not used. The neighborhood is a spatial radius combined with a time window.
