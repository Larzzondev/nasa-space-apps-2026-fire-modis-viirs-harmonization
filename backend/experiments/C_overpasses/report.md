# Experiment C: temporal sampling and overpasses

Question: how far apart are the stored acquisition minutes, how often does each satellite report, and which comparisons have no rows on one side?

The clock is UTC and the resolution is one minute. A gap describes the stored clock. It is not an orbital element, and a short gap is not identity. `same_fire` stays `not_assessed`.

Absent dates were not filled. S-NPP's zero-row dates stay out of every comparison. The partial dates 16, 24, and 29 July are used only where rows are present.

## Delivered dates

| Satellite | Dates with rows | Dates without rows | Median distinct minutes on a delivered date | Median rows on a delivered date |
| --- | ---: | ---: | ---: | ---: |
| Terra | 31 | 0 | 234.0 | 6162.0 |
| Aqua | 31 | 0 | 226.0 | 15517.0 |
| S-NPP | 21 | 10 | 455.0 | 82443.0 |
| NOAA-20 | 31 | 0 | 467.0 | 92596.0 |
| NOAA-21 | 31 | 0 | 462.0 | 87637.0 |

S-NPP dates with zero delivered rows: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28. Each one has a delivered-row count of zero because the CSV has no row that date. That is not zero fire activity.

Partial S-NPP dates that still have rows:

- 2024-07-16: 15643 rows, hours with rows [17, 18, 19, 20, 21, 22, 23].
- 2024-07-24: 14621 rows, hours with rows [0, 1, 2, 3, 4, 5].
- 2024-07-29: 17802 rows, hours with rows [15, 16, 17, 18, 19, 20, 21, 22, 23].

NOAA-21 on 20 July has 33039 delivered rows. Hours without rows: [8, 9, 10, 11, 12, 13]. Those hours are not labeled as an outage.

## Within-satellite gaps

The pooled counts are gaps between consecutive distinct acquisition minutes inside one UTC date.

| Satellite | Consecutive pairs | 1–5 min | 6–30 min | 31–90 min | 91 min or more |
| --- | ---: | ---: | ---: | ---: | ---: |
| Terra | 7125 | 5996 | 657 | 445 | 27 |
| Aqua | 6993 | 5861 | 654 | 451 | 27 |
| S-NPP | 8674 | 7949 | 513 | 212 | 0 |
| NOAA-20 | 14383 | 13154 | 902 | 327 | 0 |
| NOAA-21 | 14193 | 12968 | 880 | 344 | 1 |

Cross-midnight gaps are the clock distance from the last stored minute of one delivered date to the first stored minute of the next delivered date. A missing date makes that gap null. July 31 has no 1 August neighbor inside this extract.

## Dates a comparison can use

A date is compared only when both satellites have at least one row that UTC date.

| Pair | Dates compared | Dates not compared | Closest-minute median | Dates whose closest minutes exceed 30 |
| --- | ---: | ---: | ---: | ---: |
| Terra and Aqua | 31 | 0 | 0.0 | 0 |
| Terra and S-NPP | 21 | 10 | 0.0 | 0 |
| Terra and NOAA-20 | 31 | 0 | 0.0 | 0 |
| Terra and NOAA-21 | 31 | 0 | 0.0 | 0 |
| Aqua and S-NPP | 21 | 10 | 0.0 | 0 |
| Aqua and NOAA-20 | 31 | 0 | 0.0 | 0 |
| Aqua and NOAA-21 | 31 | 0 | 0.0 | 0 |
| S-NPP and NOAA-20 | 21 | 10 | 0.0 | 0 |
| S-NPP and NOAA-21 | 21 | 10 | 0.0 | 0 |
| NOAA-20 and NOAA-21 | 31 | 0 | 0.0 | 0 |

The closest-minute median ignores location. It can be zero when two satellites store the same `acq_time` somewhere on Earth that date. It is not the separation of a spatially nearby pair, and it does not establish the same fire.

S-NPP's ten zero-row dates reduce a comparison that includes S-NPP from 31 dates to 21 when the other satellite has rows on all 31 dates.

## Published spatially constrained time bins

These median bins are copied from the candidate-pair report at 5 km and 60 minutes. They were not recomputed. NOAA-20 and NOAA-21 falling in a 50–51 minute bin is why a 30-minute window contains no pairs for that couple: the acquisitions used by those pairs are farther apart than 30 minutes. That empty window is not a spatial miss.

| Published label | Median bin start (min) | Median bin end (min) | Pairs in the histogram |
| --- | ---: | ---: | ---: |
| Terra and Aqua | 17.0 | 18.0 | 41362 |
| MODIS (Terra and Aqua) and S-NPP | 28.0 | 29.0 | 2995557 |
| MODIS (Terra and Aqua) and NOAA-20 | 28.0 | 29.0 | 5161059 |
| MODIS (Terra and Aqua) and NOAA-21 | 28.0 | 29.0 | 5248283 |
| S-NPP and NOAA-20 | 24.0 | 25.0 | 27216791 |
| S-NPP and NOAA-21 | 25.0 | 26.0 | 24272835 |
| NOAA-20 and NOAA-21 | 50.0 | 51.0 | 65082849 |

## Coverage evidence

The coverage investigation keeps FIRMS evidence and Level-2 evidence in separate classes. This experiment cites that report and does not extend a Level-2 sentence into a FIRMS outage class. It does not download a replacement S-NPP archive.

## Limits

- No date was filled. A zero delivered-row count is not zero fire activity.
- Hour gaps are not given an outage class.
- Temporal coincidence was not used as physical fire matching.
- NOAA-20 and NOAA-21 processing level stays unresolved.
- No harmonization coefficient was calculated.
