# Nearest-neighbor sensitivity, July 2024

This report counts nearest archived rows inside stated distance and time limits. A nearest neighbor is not a confirmed common fire. A mutual nearest neighbor is not a confirmed common fire. A one-to-one assignment is a bookkeeping constraint, not a physical fire identity.

## Method

The search reuses the July candidate-pair index: Earth-centered coordinates on the same sphere, a `cKDTree`, and the great-circle length recovered from the chord. The reference sensor owns the UTC date. The other sensor may fall up to the pair's time window across midnight. One row is not copied into a second date.

Directed nearest neighbor: for each reference row on a compared date, the closest other-sensor row inside the radius and the window. Rows with no such partner are unmatched.

Mutual nearest neighbor: the partner's own nearest reference row is the same detection. The proportion uses the directed matches in the stated direction as the denominator.

One-to-one assignment: within each UTC date, eligible pairs are taken in order of increasing separation. A detection already used on an earlier date is left out. Dates run from 1 July through 31 July, so a later, closer pair can lose to an earlier, longer pair. On one deterministic subset of at most 80 reference rows, that greedy rule is compared with a Hungarian assignment. The Hungarian result is not expanded to the full month.

The windows are exploratory. Terra–Aqua and every MODIS–VIIRS pair use 30 minutes. S-NPP against NOAA-20 and NOAA-21 uses 30 and 60 minutes. NOAA-20 against NOAA-21 uses 60 minutes because those overpasses are about 50 minutes apart. None of these windows means the sensors observed at the same instant.

A date is compared only when both sides have at least one row that UTC date. A date with no rows is excluded. It is not stored as zero matches and it is not zero fire activity. S-NPP dates that do contain rows are used only for those rows. Incomplete S-NPP delivery on 16, 24, and 29 July is not repaired.

NOAA-20 and NOAA-21 processing level is unresolved. The local filenames use fire_archive, while the FIRMS download readme says standard-quality data are not yet available for those sensors. The version column is not used as a processing stream.

No MODIS-to-VIIRS scaling factor is calculated. FRP ratios use the other sensor divided by the reference sensor, and only when both values are positive. Zero and negative FRP rows stay in the source tables and in the match counts. They are left out of the ratio only. XGBoost is not trained. H3 is not applied. `same_fire` remains `not_assessed`.

## Directed nearest neighbors at 1 km

| Pair | Window (minutes) | Compared dates | Matched reference rows | Unmatched | Mutual | Mutual share | One-to-one | Ambiguous share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra and Aqua | 30 | 31 | 3987 | 191329 | 3023 | 75.8% | 3316 | 0.8% |
| MODIS (Terra and Aqua) and S-NPP | 30 | 21 | 76889 | 361936 | 63870 | 83.1% | 72490 | 13.0% |
| MODIS (Terra and Aqua) and NOAA-20 | 30 | 31 | 159844 | 516792 | 132306 | 82.8% | 149618 | 17.1% |
| MODIS (Terra and Aqua) and NOAA-21 | 30 | 31 | 151724 | 524912 | 125833 | 82.9% | 142183 | 16.3% |
| S-NPP and NOAA-20 | 30 | 21 | 1093114 | 541906 | 701634 | 64.2% | 836919 | 53.3% |
| S-NPP and NOAA-21 | 30 | 21 | 1044632 | 590388 | 650913 | 62.3% | 771752 | 50.0% |
| NOAA-20 and NOAA-21 | 60 | 31 | 2070714 | 831883 | 1202187 | 58.1% | 1521467 | 57.2% |

## Sensitivity

### Terra and Aqua

| Window | Radius | Matched | Unmatched | Eligible pairs | Unique partners | Mutual | One-to-one | Ambiguous share | Nearest-distance bin (m) | Gap bin (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 30 | 375 | 941 | 194375 | 974 | 897 | 897 | 899 | 0.0% | 250–500 | 0–250 |
| 30 | 750 | 2921 | 192395 | 3583 | 2521 | 2478 | 2574 | 0.3% | 250–500 | 0–250 |
| 30 | 1000 | 3987 | 191329 | 5976 | 3149 | 3023 | 3316 | 0.8% | 500–750 | 0–250 |
| 30 | 2000 | 6209 | 189107 | 16461 | 4074 | 3752 | 4631 | 2.2% | 750–1000 | 250–500 |
| 30 | 5000 | 7528 | 187788 | 41362 | 4340 | 3890 | 5335 | 3.2% | 750–1000 | 250–500 |

Excluded dates: none.

### MODIS (Terra and Aqua) and S-NPP

| Window | Radius | Matched | Unmatched | Eligible pairs | Unique partners | Mutual | One-to-one | Ambiguous share | Nearest-distance bin (m) | Gap bin (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 30 | 375 | 34722 | 404103 | 53257 | 34434 | 34365 | 34527 | 3.1% | 0–250 | 0–250 |
| 30 | 750 | 64388 | 374437 | 186426 | 61593 | 58333 | 62454 | 9.9% | 250–500 | 0–250 |
| 30 | 1000 | 76889 | 361936 | 293942 | 70178 | 63870 | 72490 | 13.0% | 250–500 | 0–250 |
| 30 | 2000 | 92702 | 346123 | 698671 | 77710 | 68065 | 86219 | 18.0% | 500–750 | 0–250 |
| 30 | 5000 | 99115 | 339710 | 1595670 | 80520 | 69557 | 92840 | 20.2% | 500–750 | 0–250 |

Excluded dates: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28.

### MODIS (Terra and Aqua) and NOAA-20

| Window | Radius | Matched | Unmatched | Eligible pairs | Unique partners | Mutual | One-to-one | Ambiguous share | Nearest-distance bin (m) | Gap bin (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 30 | 375 | 72215 | 604421 | 106358 | 71627 | 71521 | 71800 | 3.9% | 0–250 | 0–250 |
| 30 | 750 | 135454 | 541182 | 364942 | 128981 | 122298 | 130778 | 12.9% | 250–500 | 0–250 |
| 30 | 1000 | 159844 | 516792 | 565132 | 144895 | 132306 | 149618 | 17.1% | 250–500 | 0–250 |
| 30 | 2000 | 188705 | 487931 | 1287650 | 157890 | 139676 | 174063 | 23.3% | 250–500 | 0–250 |
| 30 | 5000 | 202556 | 474080 | 2888663 | 164185 | 143449 | 188899 | 26.6% | 500–750 | 0–250 |

Excluded dates: none.

### MODIS (Terra and Aqua) and NOAA-21

| Window | Radius | Matched | Unmatched | Eligible pairs | Unique partners | Mutual | One-to-one | Ambiguous share | Nearest-distance bin (m) | Gap bin (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 30 | 375 | 67785 | 608851 | 100901 | 67228 | 67092 | 67368 | 3.7% | 0–250 | 0–250 |
| 30 | 750 | 128024 | 548612 | 350236 | 121679 | 115348 | 123354 | 12.2% | 250–500 | 0–250 |
| 30 | 1000 | 151724 | 524912 | 548204 | 137592 | 125833 | 142183 | 16.3% | 250–500 | 0–250 |
| 30 | 2000 | 178881 | 497755 | 1276354 | 150693 | 133130 | 165535 | 22.2% | 250–500 | 0–250 |
| 30 | 5000 | 190217 | 486419 | 2900181 | 155771 | 135968 | 177692 | 25.0% | 500–750 | 0–250 |

Excluded dates: none.

### S-NPP and NOAA-20

| Window | Radius | Matched | Unmatched | Eligible pairs | Unique partners | Mutual | One-to-one | Ambiguous share | Nearest-distance bin (m) | Gap bin (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 30 | 375 | 867424 | 767596 | 1377738 | 676313 | 658469 | 700053 | 23.1% | 0–250 | 0–250 |
| 30 | 750 | 1062076 | 572944 | 3634998 | 729018 | 698328 | 809062 | 49.0% | 0–250 | 0–250 |
| 30 | 1000 | 1093114 | 541906 | 5138443 | 734290 | 701634 | 836919 | 53.3% | 0–250 | 0–250 |
| 30 | 2000 | 1145671 | 489349 | 11038443 | 745064 | 708399 | 884130 | 59.1% | 0–250 | 0–250 |
| 30 | 5000 | 1217649 | 417371 | 27216791 | 764208 | 720248 | 947349 | 65.8% | 250–500 | 0–250 |
| 60 | 375 | 867424 | 767596 | 1377738 | 676313 | 658469 | 700053 | 23.1% | 0–250 | 0–250 |
| 60 | 750 | 1062076 | 572944 | 3634998 | 729018 | 698328 | 809062 | 49.0% | 0–250 | 0–250 |
| 60 | 1000 | 1093114 | 541906 | 5138443 | 734290 | 701634 | 836919 | 53.3% | 0–250 | 0–250 |
| 60 | 2000 | 1145671 | 489349 | 11038443 | 745064 | 708399 | 884130 | 59.1% | 0–250 | 0–250 |
| 60 | 5000 | 1217649 | 417371 | 27216791 | 764208 | 720248 | 947349 | 65.8% | 250–500 | 0–250 |

Excluded dates: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28.

### S-NPP and NOAA-21

| Window | Radius | Matched | Unmatched | Eligible pairs | Unique partners | Mutual | One-to-one | Ambiguous share | Nearest-distance bin (m) | Gap bin (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 30 | 375 | 813193 | 821827 | 1276587 | 628518 | 611450 | 649249 | 21.1% | 0–250 | 0–250 |
| 30 | 750 | 1011958 | 623062 | 3338448 | 677470 | 647599 | 746627 | 45.5% | 0–250 | 0–250 |
| 30 | 1000 | 1044632 | 590388 | 4705012 | 682739 | 650913 | 771752 | 50.0% | 0–250 | 0–250 |
| 30 | 2000 | 1098912 | 536108 | 10036925 | 692984 | 657381 | 815281 | 56.0% | 0–250 | 0–250 |
| 30 | 5000 | 1172243 | 462777 | 24272835 | 710710 | 668330 | 873379 | 62.8% | 250–500 | 0–250 |
| 60 | 375 | 813193 | 821827 | 1276587 | 628518 | 611450 | 649249 | 21.1% | 0–250 | 0–250 |
| 60 | 750 | 1011958 | 623062 | 3338448 | 677470 | 647599 | 746627 | 45.5% | 0–250 | 0–250 |
| 60 | 1000 | 1044632 | 590388 | 4705012 | 682739 | 650913 | 771752 | 50.0% | 0–250 | 0–250 |
| 60 | 2000 | 1098912 | 536108 | 10036925 | 692984 | 657381 | 815281 | 56.0% | 0–250 | 0–250 |
| 60 | 5000 | 1172243 | 462777 | 24272835 | 710710 | 668330 | 873379 | 62.8% | 250–500 | 0–250 |

Excluded dates: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28.

### NOAA-20 and NOAA-21

| Window | Radius | Matched | Unmatched | Eligible pairs | Unique partners | Mutual | One-to-one | Ambiguous share | Nearest-distance bin (m) | Gap bin (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 60 | 375 | 1557319 | 1345278 | 2901179 | 1152258 | 1096972 | 1222183 | 27.3% | 0–250 | 0–250 |
| 60 | 750 | 1986332 | 916265 | 8072351 | 1278155 | 1191590 | 1459343 | 51.9% | 0–250 | 0–250 |
| 60 | 1000 | 2070714 | 831883 | 11642064 | 1294220 | 1202187 | 1521467 | 57.2% | 0–250 | 0–250 |
| 60 | 2000 | 2205566 | 697031 | 25872335 | 1323960 | 1222087 | 1632362 | 64.4% | 0–250 | 0–250 |
| 60 | 5000 | 2388678 | 513919 | 65082849 | 1376821 | 1255823 | 1782649 | 72.8% | 250–500 | 0–250 |

Excluded dates: none.

Ambiguous share is the fraction of reference rows on compared dates that have two or more eligible partners. A single eligible partner is still not proof of one fire. Eligible-pair totals count every pair, so they are larger than the number of detections.

The gap is the second-nearest distance minus the nearest distance, for reference rows that have at least two partners. A small gap means another archived row is nearly as close.

## One-to-one comparison on a subset

Terra and Aqua on 2024-07-01 at 1000 m and 30 minutes: 80 reference rows, 75 partners, 105 edges. Greedy assigned 62 pairs totaling 35654.3 m. Hungarian assigned 66 pairs totaling 39840.7 m.
MODIS (Terra and Aqua) and S-NPP on 2024-07-01 at 1000 m and 30 minutes: 80 reference rows, 120 partners, 121 edges. Greedy assigned 80 pairs totaling 3532.4 m. Hungarian assigned 80 pairs totaling 3532.4 m.
MODIS (Terra and Aqua) and NOAA-20 on 2024-07-01 at 1000 m and 30 minutes: 80 reference rows, 120 partners, 121 edges. Greedy assigned 80 pairs totaling 5077.8 m. Hungarian assigned 80 pairs totaling 5077.8 m.
MODIS (Terra and Aqua) and NOAA-21 on 2024-07-01 at 1000 m and 30 minutes: 80 reference rows, 120 partners, 122 edges. Greedy assigned 80 pairs totaling 2593.3 m. Hungarian assigned 80 pairs totaling 2593.3 m.
S-NPP and NOAA-20 on 2024-07-01 at 1000 m and 30 minutes: 80 reference rows, 120 partners, 120 edges. Greedy assigned 80 pairs totaling 591.3 m. Hungarian assigned 80 pairs totaling 591.3 m.
S-NPP and NOAA-21 on 2024-07-01 at 1000 m and 30 minutes: 80 reference rows, 120 partners, 120 edges. Greedy assigned 80 pairs totaling 595.7 m. Hungarian assigned 80 pairs totaling 595.7 m.
NOAA-20 and NOAA-21 on 2024-07-01 at 1000 m and 60 minutes: 80 reference rows, 120 partners, 120 edges. Greedy assigned 80 pairs totaling 603.0 m. Hungarian assigned 80 pairs totaling 603.0 m.

## FRP ratios

The ratio is the other sensor's FRP divided by the reference sensor's FRP. It is calculated only when both values are positive. The quantiles describe this candidate sample. The rows are clustered, so the quantiles are not a confidence interval and not a harmonization coefficient.

| Pair | Window | Radius | Positive pairs | Excluded non-positive | Median ratio | p10 | p90 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra and Aqua | 30 | 375 | 938 | 3 | 0.932 | 0.326 | 3.087 |
| Terra and Aqua | 30 | 1000 | 3970 | 17 | 1.031 | 0.338 | 3.395 |
| Terra and Aqua | 30 | 5000 | 7483 | 45 | 1.248 | 0.381 | 4.887 |
| MODIS (Terra and Aqua) and S-NPP | 30 | 375 | 34654 | 68 | 0.279 | 0.084 | 0.925 |
| MODIS (Terra and Aqua) and S-NPP | 30 | 1000 | 76808 | 81 | 0.327 | 0.094 | 1.056 |
| MODIS (Terra and Aqua) and S-NPP | 30 | 5000 | 99023 | 92 | 0.342 | 0.094 | 1.140 |
| MODIS (Terra and Aqua) and NOAA-20 | 30 | 375 | 72111 | 104 | 0.306 | 0.089 | 1.020 |
| MODIS (Terra and Aqua) and NOAA-20 | 30 | 1000 | 159710 | 134 | 0.366 | 0.101 | 1.207 |
| MODIS (Terra and Aqua) and NOAA-20 | 30 | 5000 | 202407 | 149 | 0.379 | 0.101 | 1.287 |
| MODIS (Terra and Aqua) and NOAA-21 | 30 | 375 | 67630 | 155 | 0.343 | 0.101 | 1.072 |
| MODIS (Terra and Aqua) and NOAA-21 | 30 | 1000 | 151532 | 192 | 0.422 | 0.118 | 1.314 |
| MODIS (Terra and Aqua) and NOAA-21 | 30 | 5000 | 190014 | 203 | 0.436 | 0.117 | 1.415 |
| S-NPP and NOAA-20 | 30 | 375 | 866921 | 503 | 1.007 | 0.378 | 2.595 |
| S-NPP and NOAA-20 | 30 | 1000 | 1092569 | 545 | 1.029 | 0.375 | 2.740 |
| S-NPP and NOAA-20 | 30 | 5000 | 1217089 | 560 | 1.045 | 0.375 | 2.865 |
| S-NPP and NOAA-20 | 60 | 375 | 866921 | 503 | 1.007 | 0.378 | 2.595 |
| S-NPP and NOAA-20 | 60 | 1000 | 1092569 | 545 | 1.029 | 0.375 | 2.740 |
| S-NPP and NOAA-20 | 60 | 5000 | 1217089 | 560 | 1.045 | 0.375 | 2.865 |
| S-NPP and NOAA-21 | 30 | 375 | 812164 | 1029 | 1.275 | 0.502 | 3.388 |
| S-NPP and NOAA-21 | 30 | 1000 | 1043398 | 1234 | 1.301 | 0.484 | 3.604 |
| S-NPP and NOAA-21 | 30 | 5000 | 1170967 | 1276 | 1.309 | 0.472 | 3.719 |
| S-NPP and NOAA-21 | 60 | 375 | 812164 | 1029 | 1.275 | 0.502 | 3.388 |
| S-NPP and NOAA-21 | 60 | 1000 | 1043398 | 1234 | 1.301 | 0.484 | 3.604 |
| S-NPP and NOAA-21 | 60 | 5000 | 1170967 | 1276 | 1.309 | 0.472 | 3.719 |
| NOAA-20 and NOAA-21 | 60 | 375 | 1555652 | 1667 | 1.200 | 0.432 | 3.328 |
| NOAA-20 and NOAA-21 | 60 | 1000 | 2068827 | 1887 | 1.219 | 0.410 | 3.552 |
| NOAA-20 and NOAA-21 | 60 | 5000 | 2386695 | 1983 | 1.228 | 0.398 | 3.687 |

Day/night and confidence splits below use the 1 km directed nearest neighbors and the pair's detail window. MODIS classes are the published 0–29, 30–79, and 80–100 classes. VIIRS flags stay `l`, `n`, and `h`.

### Terra and Aqua

Median FRP among directed nearest neighbors, including non-positive values in the sample count: reference 53.4 MW (n=3987), partner 56.7 MW (n=3987). Median scan 1.50 km and 1.40 km.

Day/night:

- D-D: n=3970, median ratio 1.031
- D-N: n=0, median ratio n/a
- N-D: n=0, median ratio n/a
- N-N: n=0, median ratio n/a

Reference confidence:

- low_0_29: n=260, median ratio 1.205
- nominal_30_79: n=1866, median ratio 1.142
- high_80_100: n=1844, median ratio 0.901

Partner confidence:

- low_0_29: n=236, median ratio 0.850
- nominal_30_79: n=1691, median ratio 0.903
- high_80_100: n=2043, median ratio 1.192

### MODIS (Terra and Aqua) and S-NPP

Median FRP among directed nearest neighbors, including non-positive values in the sample count: reference 25.6 MW (n=76889), partner 8.5 MW (n=76889). Median scan 1.20 km and 0.47 km.

Day/night:

- D-D: n=69079, median ratio 0.345
- D-N: n=0, median ratio n/a
- N-D: n=217, median ratio 0.359
- N-N: n=7512, median ratio 0.210

Reference confidence:

- low_0_29: n=3775, median ratio 0.374
- nominal_30_79: n=42944, median ratio 0.428
- high_80_100: n=30089, median ratio 0.208

Partner confidence:

- l: n=5502, median ratio 0.297
- n: n=62678, median ratio 0.317
- h: n=8628, median ratio 0.441

### MODIS (Terra and Aqua) and NOAA-20

Median FRP among directed nearest neighbors, including non-positive values in the sample count: reference 24.1 MW (n=159844), partner 9.0 MW (n=159844). Median scan 1.20 km and 0.47 km.

Day/night:

- D-D: n=146393, median ratio 0.384
- D-N: n=0, median ratio n/a
- N-D: n=525, median ratio 0.393
- N-N: n=12792, median ratio 0.211

Reference confidence:

- low_0_29: n=7598, median ratio 0.428
- nominal_30_79: n=92521, median ratio 0.476
- high_80_100: n=59591, median ratio 0.226

Partner confidence:

- l: n=14558, median ratio 0.332
- n: n=129775, median ratio 0.359
- h: n=15377, median ratio 0.495

### MODIS (Terra and Aqua) and NOAA-21

Median FRP among directed nearest neighbors, including non-positive values in the sample count: reference 25.7 MW (n=151724), partner 11.1 MW (n=151724). Median scan 1.20 km and 0.47 km.

Day/night:

- D-D: n=137344, median ratio 0.446
- D-N: n=0, median ratio n/a
- N-D: n=394, median ratio 0.438
- N-N: n=13794, median ratio 0.247

Reference confidence:

- low_0_29: n=7355, median ratio 0.476
- nominal_30_79: n=86890, median ratio 0.548
- high_80_100: n=57287, median ratio 0.267

Partner confidence:

- l: n=13418, median ratio 0.380
- n: n=118056, median ratio 0.404
- h: n=20058, median ratio 0.597

### S-NPP and NOAA-20

Median FRP among directed nearest neighbors, including non-positive values in the sample count: reference 5.3 MW (n=1093114), partner 5.5 MW (n=1093114). Median scan 0.43 km and 0.44 km.

Day/night:

- D-D: n=700401, median ratio 1.010
- D-N: n=0, median ratio n/a
- N-D: n=1334, median ratio 2.546
- N-N: n=390834, median ratio 1.052

Reference confidence:

- l: n=84343, median ratio 1.159
- n: n=947591, median ratio 1.036
- h: n=60635, median ratio 0.753

Partner confidence:

- l: n=89793, median ratio 0.863
- n: n=949338, median ratio 1.035
- h: n=53438, median ratio 1.239

### S-NPP and NOAA-21

Median FRP among directed nearest neighbors, including non-positive values in the sample count: reference 5.3 MW (n=1044632), partner 6.9 MW (n=1044632). Median scan 0.43 km and 0.44 km.

Day/night:

- D-D: n=673840, median ratio 1.300
- D-N: n=270, median ratio 0.732
- N-D: n=0, median ratio n/a
- N-N: n=369288, median ratio 1.303

Reference confidence:

- l: n=80911, median ratio 1.508
- n: n=903655, median ratio 1.302
- h: n=58832, median ratio 1.030

Partner confidence:

- l: n=85781, median ratio 1.189
- n: n=884700, median ratio 1.286
- h: n=72917, median ratio 1.768

### NOAA-20 and NOAA-21

Median FRP among directed nearest neighbors, including non-positive values in the sample count: reference 5.4 MW (n=2070714), partner 6.7 MW (n=2070714). Median scan 0.44 km and 0.44 km.

Day/night:

- D-D: n=1327897, median ratio 1.216
- D-N: n=1391, median ratio 0.805
- N-D: n=992, median ratio 2.055
- N-N: n=738547, median ratio 1.222

Reference confidence:

- l: n=168352, median ratio 1.469
- n: n=1778766, median ratio 1.227
- h: n=121709, median ratio 0.795

Partner confidence:

- l: n=186669, median ratio 1.026
- n: n=1737875, median ratio 1.206
- h: n=144283, median ratio 1.853

## Performance

Load time: 168.9 s. Analysis time: 1347.4 s. Peak Python allocations traced: 1684953502 bytes. Peak process working set: 1897316352 bytes. Allocation tracing slows the CSV load.

## Reproducibility

From `backend/`, with the July CSVs already extracted:

```bash
.venv\Scripts\python -m fire_data.nearest_neighbor_analysis
```

The command reads the four monthly archives, writes this report, and writes the figures under `backend/reports/figures/nearest_neighbor_2024_07/`. It does not modify the CSVs.

## Limitations

- A nearest neighbor does not prove that the two rows observe the same fire.
- A mutual nearest neighbor does not prove that the two rows observe the same fire.
- One-to-one assignment is a computational constraint. Calendar order can keep an earlier pair and drop a later, closer pair that shares a detection.
- The Hungarian comparison covers a small subset, not the 8 million rows.
- Eligible-pair totals are not unique fires. One detection can have many partners.
- Raw detection totals are not a measure of which sensor performs better.
- Missing S-NPP dates are excluded. They are not zeros. Incomplete intervals on 16, 24, and 29 July are not repaired.
- NOAA-20 and NOAA-21 processing level is unresolved. The local filenames use fire_archive, while the FIRMS download readme says standard-quality data are not yet available for those sensors. The version column is not used as a processing stream.
- FRP ratios are not a scaling coefficient. Non-positive FRP values are excluded from the ratio and retained everywhere else.
- No XGBoost model or H3 aggregation is produced.
