# Experiment B: sensor measurement relationships

Question: how do FRP, brightness, scan, track, confidence, and day/night differ among the five satellites when every stored row stays in the distribution?

No slope, intercept, or harmonization coefficient is estimated. The published positive-FRP ratios are cited. They are partner divided by reference, and only when both values are positive. Non-positive rows remain in the all-row quantiles and are counted beside any ratio.

`same_fire` is `not_assessed`. Terra and Aqua stay separate. A cited pair keeps its published label.

## All-row distributions

The p50 column is the linear quantile of every finite row, including non-positive FRP. The median column is `numpy.median` of those same rows.

| Satellite | Rows | FRP p50 (MW) | FRP non-positive | Brightness p50 (K) | Scan p50 (km) | Track p50 (km) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra | 195316 | 19.100 | 393 | 316.700 | 1.200 | 1.100 |
| Aqua | 481320 | 21.600 | 155 | 322.300 | 1.300 | 1.100 |
| S-NPP | 1635020 | 5.060 | 373 | 336.100 | 0.440 | 0.440 |
| NOAA-20 | 2902597 | 5.140 | 809 | 336.210 | 0.440 | 0.440 |
| NOAA-21 | 2771214 | 6.090 | 1710 | 335.880 | 0.440 | 0.450 |

## Day and night

Day and night are the stored flags. They are not recomputed from the clock.

| Satellite | Day rows | Day FRP p50 | Night rows | Night FRP p50 | Night brightness p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Terra | 104032 | 19.200 | 91284 | 19.100 | 313.600 |
| Aqua | 448221 | 21.900 | 33099 | 18.400 | 311.500 |
| S-NPP | 1125000 | 7.030 | 510020 | 1.770 | 308.570 |
| NOAA-20 | 2018537 | 7.040 | 884060 | 1.780 | 308.760 |
| NOAA-21 | 1907205 | 8.480 | 864009 | 2.090 | 308.740 |

## Scan quartiles

Quartile edges are computed inside each satellite. A larger FRP in a larger scan bin is a conditional description of the stored columns. It is not a fire-size result and it is not a fitted line.

| Satellite | Q1 FRP p50 | Q2 FRP p50 | Q3 FRP p50 | Q4 FRP p50 | Q4 scan p50 (km) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Terra | 12.500 | 13.300 | 19.100 | 41.700 | 2.500 |
| Aqua | 13.500 | 16.700 | 22.200 | 44.200 | 2.600 |
| S-NPP | 4.130 | 4.580 | 5.310 | 6.810 | 0.570 |
| NOAA-20 | 4.170 | 4.520 | 5.440 | 7.050 | 0.570 |
| NOAA-21 | 4.810 | 5.320 | 6.470 | 8.690 | 0.570 |

## Brightness at 367 K

A stored VIIRS brightness of 367 K is counted. It is not marked as confirmed saturation. The files have no Level-1 saturation flag. MODIS brightness is a different stored temperature.

| Satellite | Rows at 367 K | Rows in [360, 367) | Rows above 367 K |
| --- | ---: | ---: | ---: |
| Terra | 29 | 2293 | 6693 |
| Aqua | 105 | 7052 | 19451 |
| S-NPP | 108763 | 0 | 0 |
| NOAA-20 | 174240 | 0 | 0 |
| NOAA-21 | 206504 | 0 | 0 |

## Native confidence and type

MODIS confidence stays on 0–100. The 0–29, 30–79, and 80–100 groups repeat the published reporting split. VIIRS flags stay `l`, `n`, and `h`. The scales are not converted. `type` is counted as the stored codes 0, 1, 2, and 3. Those codes are not named.

Counts are in `results.json`.

## Published positive-FRP ratios

These ratios were not recomputed. Each one is the other sensor's FRP divided by the reference sensor's FRP when both are positive. The excluded-pair count sits beside the ratio. A ratio quantile is not a coefficient.

| Published label | Window (min) | Ratio rows | p50 | Excluded non-positive pairs |
| --- | ---: | ---: | ---: | ---: |
| Terra and Aqua | 30 | 3970 | 1.031 | 17 |
| MODIS (Terra and Aqua) and S-NPP | 30 | 76808 | 0.327 | 81 |
| MODIS (Terra and Aqua) and NOAA-20 | 30 | 159710 | 0.366 | 134 |
| MODIS (Terra and Aqua) and NOAA-21 | 30 | 151532 | 0.422 | 192 |
| S-NPP and NOAA-20 | 30 | 1092569 | 1.029 | 545 |
| S-NPP and NOAA-21 | 30 | 1043398 | 1.301 | 1234 |

The 30-minute window is the cited comparison above. Other 1 km windows remain in the JSON. Published day/night pair labels at 1 km and 30 minutes are stored flags of the two rows, not a shared fire.

## Agreement with the monthly EDA

All-row FRP medians, the 0.500 FRP quantile, day/night counts, and zero-FRP counts were compared with `reports/monthly_eda_2024_07.json`.

## Limits

- Non-positive FRP stays in every distribution that claims to describe all rows.
- Positive-only quantiles are labeled separately.
- `bright_t31` was not renamed and was not entered into a coefficient.
- NOAA-20 and NOAA-21 processing level stays unresolved.
- XGBoost was not trained.
