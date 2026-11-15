# Within-sensor spatial-temporal analysis, July 2024

This report describes archived rows inside each satellite. A nearest neighbor is not a confirmed fire. A DBSCAN component is not a confirmed fire. `same_fire` is `not_assessed`.

## Method

The five satellites are Terra, Aqua, S-NPP, NOAA-20, and NOAA-21. Terra and Aqua stay separate. Distances are great-circle lengths on the same sphere used for the earlier candidate-pair index. The search structure is a `cKDTree` of Earth-centered coordinates.

Each UTC date is a partition. The unrestricted same-day nearest neighbor comes from a k-nearest query. The nearest returned index that is not the row itself is kept. k starts at 2 and widens only for rows whose returned indexes are all themselves. Neighborhood counts use pairs inside 5 km. A 180-minute margin from the previous and next dates is available to the windowed counts and to DBSCAN, and those margin rows are not counted a second time as reference rows.

The windows are 0, 30, and 180 minutes. Zero minutes means the same archived `acq_time`. The radii are 375 m, 1 km, 2 km, and 5 km. The characteristic split uses 1 km and 30 minutes: a row is in a neighborhood when at least one other row of the same satellite falls inside both limits.

DBSCAN uses that same neighborhood. `min_samples` includes the row. Core rows form connected components. A border row is assigned to the neighboring component whose lowest core index is smallest. The full month uses seven settings around 1 km, 30 minutes, and `min_samples` 4. The 27-cell factorial is limited to one representative date per satellite: the earliest date whose row count is closest to the median of dates that contain rows. Every delivered row is still labeled in the seven-setting pass. Empty dates are not given a cluster count of zero.

A next-date neighbor is the closest row of the same satellite on the following UTC date, capped at 5 km. If that date has no rows, the comparison is null. It is not a zero.

NOAA-20 and NOAA-21 processing level is unresolved. The local filenames use fire_archive, while the FIRMS download readme says standard-quality data are not yet available for those sensors. The version column is not used as a processing stream.

No harmonization coefficient is calculated. XGBoost is not trained. Original rows are retained.

## Coverage

Rows analyzed: 7,985,467.

Dates with at least one row in every sensor: 2024-07-01, 2024-07-02, 2024-07-03, 2024-07-04, 2024-07-05, 2024-07-06, 2024-07-07, 2024-07-08, 2024-07-09, 2024-07-16, 2024-07-17, 2024-07-18, 2024-07-19, 2024-07-20, 2024-07-21, 2024-07-22, 2024-07-23, 2024-07-24, 2024-07-29, 2024-07-30, 2024-07-31.

| Satellite | Rows | Dates with rows | Dates without rows | Exact extra rows | Same coordinate and time, extra | Multi-epoch coordinates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra | 195,316 | 31 | 0 | 0 | 0 | 8 |
| Aqua | 481,320 | 31 | 0 | 0 | 0 | 8 |
| S-NPP | 1,635,020 | 21 | 10 | 0 | 0 | 5 |
| NOAA-20 | 2,902,597 | 31 | 0 | 0 | 1 | 10 |
| NOAA-21 | 2,771,214 | 31 | 0 | 0 | 4 | 16 |

Dates without rows are omitted from rates. S-NPP dates without rows are not zero detections.

## Same-day nearest neighbor

This neighbor can fall at any distance and any time on the same UTC date. The time gap is the absolute difference of archived minutes.

| Satellite | With a neighbor | Without | Median distance (m) | Beyond 5 km | Same minute | 1–30 min | 31–180 min | More than 180 min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra | 195,316 | 0 | 1026.9 | 35,356 | 134,956 | 2,639 | 11,425 | 46,296 |
| Aqua | 481,320 | 0 | 1118.2 | 94,002 | 434,131 | 4,832 | 13,983 | 28,374 |
| S-NPP | 1,635,020 | 0 | 379.4 | 143,693 | 1,128,644 | 14,335 | 227,622 | 264,419 |
| NOAA-20 | 2,902,597 | 0 | 382.1 | 262,449 | 2,005,116 | 24,388 | 377,643 | 495,450 |
| NOAA-21 | 2,771,214 | 0 | 380.8 | 260,255 | 1,872,925 | 23,072 | 389,430 | 485,787 |

## Neighborhoods inside a radius and a time window

A row with a neighbor is not a fire match. Counts exclude the row itself.

| Satellite | Radius (m) | Window (min) | With neighbor | Without | Share | Median nearest distance (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra | 375 | 0 | 3,216 | 192,100 | 0 | 8 |
| Terra | 375 | 30 | 3,256 | 192,060 | 0 | 8 |
| Terra | 1000 | 0 | 50,869 | 144,447 | 0 | 8 |
| Terra | 1000 | 30 | 51,096 | 144,220 | 0 | 8 |
| Terra | 5000 | 0 | 151,995 | 43,321 | 0 | 8 |
| Terra | 5000 | 30 | 152,165 | 43,151 | 0 | 8 |
| Aqua | 375 | 0 | 3,468 | 477,852 | 0 | 8 |
| Aqua | 375 | 30 | 3,522 | 477,798 | 0 | 8 |
| Aqua | 1000 | 0 | 118,458 | 362,862 | 0 | 8 |
| Aqua | 1000 | 30 | 118,934 | 362,386 | 0 | 8 |
| Aqua | 5000 | 0 | 380,864 | 100,456 | 0 | 8 |
| Aqua | 5000 | 30 | 381,341 | 99,979 | 0 | 8 |
| S-NPP | 375 | 0 | 463,244 | 1,171,776 | 0 | 5 |
| S-NPP | 375 | 30 | 472,944 | 1,162,076 | 0 | 5 |
| S-NPP | 1000 | 0 | 1,327,176 | 307,844 | 0 | 5 |
| S-NPP | 1000 | 30 | 1,330,427 | 304,593 | 0 | 5 |
| S-NPP | 5000 | 0 | 1,454,784 | 180,236 | 0 | 5 |
| S-NPP | 5000 | 30 | 1,457,288 | 177,732 | 0 | 5 |
| NOAA-20 | 375 | 0 | 843,579 | 2,059,018 | 1 | 10 |
| NOAA-20 | 375 | 30 | 859,731 | 2,042,866 | 1 | 10 |
| NOAA-20 | 1000 | 0 | 2,311,336 | 591,261 | 1 | 10 |
| NOAA-20 | 1000 | 30 | 2,317,252 | 585,345 | 1 | 10 |
| NOAA-20 | 5000 | 0 | 2,566,767 | 335,830 | 1 | 10 |
| NOAA-20 | 5000 | 30 | 2,571,160 | 331,437 | 1 | 10 |
| NOAA-21 | 375 | 0 | 801,590 | 1,969,624 | 4 | 16 |
| NOAA-21 | 375 | 30 | 816,496 | 1,954,718 | 4 | 16 |
| NOAA-21 | 1000 | 0 | 2,184,799 | 586,415 | 4 | 16 |
| NOAA-21 | 1000 | 30 | 2,190,416 | 580,798 | 4 | 16 |
| NOAA-21 | 5000 | 0 | 2,438,975 | 332,239 | 4 | 16 |
| NOAA-21 | 5000 | 30 | 2,443,114 | 328,100 | 4 | 16 |

The JSON report contains the 2 km radius and the 180-minute window as well.

## Next UTC date, capped at 5 km

July 31 is excluded because 1 August is outside this extract. That exclusion is not a zero-detection day. Other exclusions are dates whose next July date has no delivered rows.

| Satellite | Eligible rows | Next July date has no rows | Next date outside July | Within 1 km | Within 5 km |
| --- | ---: | ---: | ---: | ---: | ---: |
| Terra | 189,817 | 0 | 5,499 | 43,098 | 86,516 |
| Aqua | 469,316 | 0 | 12,004 | 38,311 | 126,553 |
| S-NPP | 1,429,849 | 117,785 | 87,386 | 507,438 | 887,254 |
| NOAA-20 | 2,818,023 | 0 | 84,574 | 987,348 | 1,835,893 |
| NOAA-21 | 2,689,742 | 0 | 81,472 | 937,202 | 1,734,374 |

## Characteristics at 1 km and 30 minutes

Quantiles include non-positive FRP. VIIRS confidence is the native flag. MODIS confidence is the native 0–100 value.

| Satellite | Group | Rows | FRP p50 | Brightness p50 | Scan p50 | Track p50 | Day | Night |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra | All delivered rows | 195,316 | 19.10 | 316.70 | 1.20 | 1.10 | 104,032 | 91,284 |
| Terra | No neighbor inside 1 km and 30 min | 144,220 | 16.40 | 315.70 | 1.20 | 1.10 | 79,134 | 65,086 |
| Terra | Neighbor inside 1 km and 30 min | 51,096 | 31.10 | 320.40 | 1.50 | 1.20 | 24,898 | 26,198 |
| Aqua | All delivered rows | 481,320 | 21.60 | 322.30 | 1.30 | 1.10 | 448,221 | 33,099 |
| Aqua | No neighbor inside 1 km and 30 min | 362,386 | 18.80 | 321.50 | 1.20 | 1.10 | 337,771 | 24,615 |
| Aqua | Neighbor inside 1 km and 30 min | 118,934 | 34.90 | 325.20 | 1.60 | 1.20 | 110,450 | 8,484 |
| S-NPP | All delivered rows | 1,635,020 | 5.06 | 336.10 | 0.44 | 0.44 | 1,125,000 | 510,020 |
| S-NPP | No neighbor inside 1 km and 30 min | 304,593 | 3.61 | 334.36 | 0.44 | 0.43 | 233,202 | 71,391 |
| S-NPP | Neighbor inside 1 km and 30 min | 1,330,427 | 5.59 | 336.79 | 0.44 | 0.45 | 891,798 | 438,629 |
| NOAA-20 | All delivered rows | 2,902,597 | 5.14 | 336.21 | 0.44 | 0.44 | 2,018,537 | 884,060 |
| NOAA-20 | No neighbor inside 1 km and 30 min | 585,345 | 3.74 | 334.57 | 0.44 | 0.43 | 451,959 | 133,386 |
| NOAA-20 | Neighbor inside 1 km and 30 min | 2,317,252 | 5.69 | 336.91 | 0.44 | 0.45 | 1,566,578 | 750,674 |
| NOAA-21 | All delivered rows | 2,771,214 | 6.09 | 335.88 | 0.44 | 0.45 | 1,907,205 | 864,009 |
| NOAA-21 | No neighbor inside 1 km and 30 min | 580,798 | 4.47 | 334.31 | 0.44 | 0.44 | 446,372 | 134,426 |
| NOAA-21 | Neighbor inside 1 km and 30 min | 2,190,416 | 6.75 | 336.58 | 0.44 | 0.45 | 1,460,833 | 729,583 |

### Native confidence

Terra (modis_0_100):
- all: 0 2,414, 1 17, 2 41, 3 86, 4 73, 5 119, 6 140, 7 162, 8 209, 9 245, 10 266, 11 290, 12 329, 13 381, 14 408, 15 425, 16 455, 17 465, 18 503, 19 586, 20 582, 21 644, 22 719, 23 778, 24 765, 25 743, 26 844, 27 876, 28 906, 29 970, 30 949, 31 1,047, 32 1,106, 33 1,119, 34 1,164, 35 1,243, 36 1,298, 37 1,338, 38 1,380, 39 1,430, 40 1,426, 41 1,547, 42 1,555, 43 1,551, 44 1,720, 45 1,683, 46 1,751, 47 1,802, 48 1,895, 49 1,950, 50 2,092, 51 2,091, 52 2,214, 53 2,323, 54 2,397, 55 2,474, 56 2,514, 57 2,662, 58 2,763, 59 2,759, 60 2,916, 61 2,925, 62 2,970, 63 2,937, 64 2,993, 65 3,026, 66 3,072, 67 2,996, 68 2,951, 69 3,021, 70 2,945, 71 2,870, 72 2,908, 73 2,837, 74 2,710, 75 2,790, 76 2,654, 77 2,502, 78 2,556, 79 2,521, 80 2,515, 81 2,544, 82 2,491, 83 2,376, 84 2,188, 85 2,050, 86 2,076, 87 2,236, 88 1,989, 89 1,976, 90 1,861, 91 1,866, 92 1,842, 93 1,753, 94 2,115, 95 1,597, 96 1,514, 97 1,547, 98 1,492, 99 1,391, 100 30,113
- isolated: 0 1,945, 1 15, 2 32, 3 67, 4 62, 5 97, 6 108, 7 134, 8 172, 9 190, 10 226, 11 232, 12 259, 13 300, 14 319, 15 347, 16 374, 17 368, 18 401, 19 471, 20 469, 21 522, 22 595, 23 626, 24 615, 25 597, 26 694, 27 694, 28 744, 29 795, 30 759, 31 829, 32 879, 33 907, 34 960, 35 1,032, 36 1,037, 37 1,068, 38 1,125, 39 1,156, 40 1,164, 41 1,256, 42 1,274, 43 1,246, 44 1,379, 45 1,357, 46 1,415, 47 1,490, 48 1,535, 49 1,544, 50 1,689, 51 1,716, 52 1,770, 53 1,888, 54 1,915, 55 1,969, 56 2,052, 57 2,154, 58 2,213, 59 2,188, 60 2,300, 61 2,340, 62 2,364, 63 2,336, 64 2,357, 65 2,375, 66 2,416, 67 2,340, 68 2,237, 69 2,323, 70 2,221, 71 2,155, 72 2,210, 73 2,107, 74 2,036, 75 2,042, 76 1,943, 77 1,813, 78 1,858, 79 1,829, 80 1,760, 81 1,769, 82 1,713, 83 1,614, 84 1,532, 85 1,408, 86 1,411, 87 1,529, 88 1,341, 89 1,302, 90 1,265, 91 1,238, 92 1,220, 93 1,159, 94 1,361, 95 1,033, 96 993, 97 1,003, 98 972, 99 930, 100 18,629
- neighborhood: 0 469, 1 2, 2 9, 3 19, 4 11, 5 22, 6 32, 7 28, 8 37, 9 55, 10 40, 11 58, 12 70, 13 81, 14 89, 15 78, 16 81, 17 97, 18 102, 19 115, 20 113, 21 122, 22 124, 23 152, 24 150, 25 146, 26 150, 27 182, 28 162, 29 175, 30 190, 31 218, 32 227, 33 212, 34 204, 35 211, 36 261, 37 270, 38 255, 39 274, 40 262, 41 291, 42 281, 43 305, 44 341, 45 326, 46 336, 47 312, 48 360, 49 406, 50 403, 51 375, 52 444, 53 435, 54 482, 55 505, 56 462, 57 508, 58 550, 59 571, 60 616, 61 585, 62 606, 63 601, 64 636, 65 651, 66 656, 67 656, 68 714, 69 698, 70 724, 71 715, 72 698, 73 730, 74 674, 75 748, 76 711, 77 689, 78 698, 79 692, 80 755, 81 775, 82 778, 83 762, 84 656, 85 642, 86 665, 87 707, 88 648, 89 674, 90 596, 91 628, 92 622, 93 594, 94 754, 95 564, 96 521, 97 544, 98 520, 99 461, 100 11,484

Aqua (modis_0_100):
- all: 0 4,240, 1 8, 2 20, 3 34, 4 51, 5 72, 6 87, 7 119, 8 150, 9 172, 10 217, 11 268, 12 317, 13 380, 14 393, 15 486, 16 522, 17 611, 18 686, 19 762, 20 909, 21 945, 22 1,028, 23 1,132, 24 1,161, 25 1,347, 26 1,436, 27 1,564, 28 1,748, 29 1,791, 30 2,017, 31 2,034, 32 2,184, 33 2,397, 34 2,462, 35 2,575, 36 2,757, 37 2,936, 38 3,051, 39 3,220, 40 3,333, 41 3,549, 42 3,647, 43 3,807, 44 4,064, 45 4,291, 46 4,566, 47 4,678, 48 4,798, 49 5,069, 50 5,295, 51 5,473, 52 5,819, 53 6,068, 54 6,489, 55 6,745, 56 7,011, 57 7,179, 58 7,571, 59 7,884, 60 8,282, 61 8,568, 62 8,775, 63 8,977, 64 9,236, 65 9,366, 66 9,802, 67 9,644, 68 9,677, 69 9,710, 70 9,748, 71 9,744, 72 9,640, 73 9,546, 74 9,343, 75 9,728, 76 9,113, 77 8,965, 78 8,480, 79 8,342, 80 7,679, 81 7,359, 82 7,136, 83 7,123, 84 6,945, 85 6,971, 86 6,890, 87 7,178, 88 6,198, 89 5,735, 90 5,486, 91 5,275, 92 4,721, 93 4,736, 94 5,531, 95 3,930, 96 3,661, 97 3,360, 98 3,049, 99 2,849, 100 29,197
- isolated: 0 3,376, 1 6, 2 20, 3 27, 4 44, 5 59, 6 73, 7 103, 8 129, 9 147, 10 174, 11 213, 12 257, 13 306, 14 325, 15 403, 16 424, 17 495, 18 566, 19 626, 20 751, 21 777, 22 855, 23 894, 24 935, 25 1,077, 26 1,181, 27 1,287, 28 1,403, 29 1,442, 30 1,648, 31 1,677, 32 1,767, 33 1,919, 34 1,982, 35 2,124, 36 2,218, 37 2,359, 38 2,464, 39 2,603, 40 2,690, 41 2,916, 42 2,957, 43 3,132, 44 3,246, 45 3,481, 46 3,700, 47 3,847, 48 3,868, 49 4,077, 50 4,330, 51 4,428, 52 4,771, 53 4,951, 54 5,245, 55 5,453, 56 5,668, 57 5,768, 58 6,099, 59 6,275, 60 6,639, 61 6,762, 62 7,104, 63 7,212, 64 7,343, 65 7,413, 66 7,643, 67 7,587, 68 7,581, 69 7,508, 70 7,474, 71 7,391, 72 7,285, 73 7,202, 74 7,003, 75 7,179, 76 6,663, 77 6,546, 78 5,983, 79 5,949, 80 5,392, 81 5,135, 82 5,022, 83 5,056, 84 4,856, 85 4,872, 86 4,812, 87 4,864, 88 4,254, 89 3,894, 90 3,759, 91 3,612, 92 3,171, 93 3,095, 94 3,607, 95 2,580, 96 2,412, 97 2,225, 98 1,988, 99 1,830, 100 18,445
- neighborhood: 0 864, 1 2, 3 7, 4 7, 5 13, 6 14, 7 16, 8 21, 9 25, 10 43, 11 55, 12 60, 13 74, 14 68, 15 83, 16 98, 17 116, 18 120, 19 136, 20 158, 21 168, 22 173, 23 238, 24 226, 25 270, 26 255, 27 277, 28 345, 29 349, 30 369, 31 357, 32 417, 33 478, 34 480, 35 451, 36 539, 37 577, 38 587, 39 617, 40 643, 41 633, 42 690, 43 675, 44 818, 45 810, 46 866, 47 831, 48 930, 49 992, 50 965, 51 1,045, 52 1,048, 53 1,117, 54 1,244, 55 1,292, 56 1,343, 57 1,411, 58 1,472, 59 1,609, 60 1,643, 61 1,806, 62 1,671, 63 1,765, 64 1,893, 65 1,953, 66 2,159, 67 2,057, 68 2,096, 69 2,202, 70 2,274, 71 2,353, 72 2,355, 73 2,344, 74 2,340, 75 2,549, 76 2,450, 77 2,419, 78 2,497, 79 2,393, 80 2,287, 81 2,224, 82 2,114, 83 2,067, 84 2,089, 85 2,099, 86 2,078, 87 2,314, 88 1,944, 89 1,841, 90 1,727, 91 1,663, 92 1,550, 93 1,641, 94 1,924, 95 1,350, 96 1,249, 97 1,135, 98 1,061, 99 1,019, 100 10,752

S-NPP (viirs_flag):
- all: l 133,710, n 1,401,558, h 99,752
- isolated: l 34,753, n 264,415, h 5,425
- neighborhood: l 98,957, n 1,137,143, h 94,327

NOAA-20 (viirs_flag):
- all: l 265,829, n 2,479,081, h 157,687
- isolated: l 70,570, n 502,908, h 11,867
- neighborhood: l 195,259, n 1,976,173, h 145,820

NOAA-21 (viirs_flag):
- all: l 257,640, n 2,324,309, h 189,265
- isolated: l 69,037, n 495,827, h 15,934
- neighborhood: l 188,603, n 1,828,482, h 173,331

## Spatial distribution

The common-date columns use only UTC dates on which Terra, Aqua, S-NPP, NOAA-20, and NOAA-21 each have at least one row. Empty S-NPP dates do not enter that comparison as zeros.

| Satellite | Occupied 2° cells, all delivered dates | Max cell | Occupied 2° cells, common dates | Common-date rows | Latitude p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Terra | 2,364 | 4,576 | 2,145 | 127,980 | 43.76 |
| Aqua | 2,489 | 9,642 | 2,274 | 310,845 | -9.68 |
| S-NPP | 3,032 | 39,042 | 3,032 | 1,635,020 | -6.81 |
| NOAA-20 | 3,226 | 47,104 | 3,091 | 1,881,439 | -7.26 |
| NOAA-21 | 3,199 | 47,887 | 3,088 | 1,776,382 | -7.05 |

Equal-degree cells are not equal-area cells. Longitude is summarized in 90° sectors in the JSON file. Those sectors are cut at ±180 and are not fire regions.

## DBSCAN

Noise share below uses every delivered row once. The sum of partition cluster counts is shown only as a partition total. It is not a count of fires and it is not additive across dates.

| Satellite | Setting | Noise rows | Noise share | Partition cluster-count sum | Median owned size | Max owned size |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Terra | 375 m, 30 min, min 4 | 195,316 | 100.0% | 0 | n/a | 0 |
| Terra | 1000 m, 30 min, min 4 | 191,853 | 98.2% | 530 | 4.0 | 74 |
| Terra | 2000 m, 30 min, min 4 | 131,984 | 67.6% | 8,636 | 5.0 | 249 |
| Terra | 1000 m, 0 min, min 4 | 191,861 | 98.2% | 529 | 4.0 | 74 |
| Terra | 1000 m, 180 min, min 4 | 185,294 | 94.9% | 1,803 | 4.0 | 74 |
| Terra | 1000 m, 30 min, min 2 | 144,220 | 73.8% | 21,143 | 2.0 | 83 |
| Terra | 1000 m, 30 min, min 8 | 195,316 | 100.0% | 0 | n/a | 0 |
| Aqua | 375 m, 30 min, min 4 | 481,320 | 100.0% | 0 | n/a | 0 |
| Aqua | 1000 m, 30 min, min 4 | 476,029 | 98.9% | 905 | 4.0 | 78 |
| Aqua | 2000 m, 30 min, min 4 | 361,677 | 75.1% | 19,734 | 5.0 | 129 |
| Aqua | 1000 m, 0 min, min 4 | 476,045 | 98.9% | 904 | 4.0 | 78 |
| Aqua | 1000 m, 180 min, min 4 | 469,105 | 97.5% | 2,225 | 4.0 | 78 |
| Aqua | 1000 m, 30 min, min 2 | 362,386 | 75.3% | 50,875 | 2.0 | 79 |
| Aqua | 1000 m, 30 min, min 8 | 481,320 | 100.0% | 0 | n/a | 0 |
| S-NPP | 375 m, 30 min, min 4 | 1,605,068 | 98.2% | 4,913 | 4.0 | 240 |
| S-NPP | 1000 m, 30 min, min 4 | 725,239 | 44.4% | 94,640 | 6.0 | 2,198 |
| S-NPP | 2000 m, 30 min, min 4 | 614,273 | 37.6% | 94,743 | 6.0 | 2,198 |
| S-NPP | 1000 m, 0 min, min 4 | 728,987 | 44.6% | 94,382 | 6.0 | 2,198 |
| S-NPP | 1000 m, 180 min, min 4 | 662,898 | 40.5% | 91,997 | 6.0 | 2,251 |
| S-NPP | 1000 m, 30 min, min 2 | 304,593 | 18.6% | 273,192 | 3.0 | 2,198 |
| S-NPP | 1000 m, 30 min, min 8 | 1,161,605 | 71.0% | 25,549 | 12.0 | 2,198 |
| NOAA-20 | 375 m, 30 min, min 4 | 2,853,224 | 98.3% | 8,172 | 4.0 | 159 |
| NOAA-20 | 1000 m, 30 min, min 4 | 1,342,965 | 46.3% | 163,168 | 6.0 | 2,539 |
| NOAA-20 | 2000 m, 30 min, min 4 | 1,135,154 | 39.1% | 165,059 | 6.0 | 2,607 |
| NOAA-20 | 1000 m, 0 min, min 4 | 1,349,582 | 46.5% | 162,701 | 6.0 | 2,539 |
| NOAA-20 | 1000 m, 180 min, min 4 | 1,234,357 | 42.5% | 159,593 | 6.0 | 2,624 |
| NOAA-20 | 1000 m, 30 min, min 2 | 585,345 | 20.2% | 484,947 | 3.0 | 2,539 |
| NOAA-20 | 1000 m, 30 min, min 8 | 2,107,755 | 72.6% | 42,648 | 12.0 | 2,538 |
| NOAA-21 | 375 m, 30 min, min 4 | 2,722,298 | 98.2% | 7,970 | 4.0 | 113 |
| NOAA-21 | 1000 m, 30 min, min 4 | 1,303,281 | 47.0% | 152,096 | 6.0 | 1,017 |
| NOAA-21 | 2000 m, 30 min, min 4 | 1,097,128 | 39.6% | 154,641 | 6.0 | 1,166 |
| NOAA-21 | 1000 m, 0 min, min 4 | 1,309,333 | 47.2% | 151,648 | 6.0 | 1,017 |
| NOAA-21 | 1000 m, 180 min, min 4 | 1,194,783 | 43.1% | 148,390 | 6.0 | 2,246 |
| NOAA-21 | 1000 m, 30 min, min 2 | 580,798 | 21.0% | 458,352 | 3.0 | 1,018 |
| NOAA-21 | 1000 m, 30 min, min 8 | 2,018,957 | 72.9% | 40,321 | 12.0 | 1,010 |

### Representative-date factorial

Each column is that sensor's own representative date. The dates are not required to match.

| eps (m) | window | min_samples | Terra | Aqua | S-NPP | NOAA-20 | NOAA-21 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 375 | 0 | 2 | 98.9% | 99.2% | 72.7% | 71.3% | 64.4% |
| 375 | 0 | 4 | 100.0% | 100.0% | 98.4% | 98.2% | 97.7% |
| 375 | 0 | 8 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 375 | 30 | 2 | 98.9% | 99.1% | 72.1% | 70.9% | 63.7% |
| 375 | 30 | 4 | 100.0% | 100.0% | 98.4% | 98.2% | 97.6% |
| 375 | 30 | 8 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 375 | 180 | 2 | 97.4% | 98.7% | 68.8% | 66.3% | 50.3% |
| 375 | 180 | 4 | 100.0% | 100.0% | 95.6% | 94.2% | 84.1% |
| 375 | 180 | 8 | 100.0% | 100.0% | 100.0% | 100.0% | 99.7% |
| 1000 | 0 | 2 | 75.3% | 75.2% | 22.8% | 24.7% | 18.0% |
| 1000 | 0 | 4 | 99.6% | 98.6% | 52.9% | 54.6% | 42.4% |
| 1000 | 0 | 8 | 100.0% | 100.0% | 79.3% | 81.4% | 69.9% |
| 1000 | 30 | 2 | 75.3% | 75.2% | 22.5% | 24.5% | 17.8% |
| 1000 | 30 | 4 | 99.6% | 98.6% | 52.7% | 54.4% | 42.2% |
| 1000 | 30 | 8 | 100.0% | 100.0% | 79.2% | 81.2% | 69.6% |
| 1000 | 180 | 2 | 71.4% | 73.7% | 21.4% | 23.3% | 15.6% |
| 1000 | 180 | 4 | 97.6% | 97.0% | 50.2% | 51.8% | 36.5% |
| 1000 | 180 | 8 | 100.0% | 100.0% | 76.5% | 77.2% | 58.3% |
| 2000 | 0 | 2 | 31.9% | 29.6% | 19.2% | 20.0% | 14.8% |
| 2000 | 0 | 4 | 73.5% | 73.0% | 45.8% | 46.2% | 35.2% |
| 2000 | 0 | 8 | 94.2% | 92.5% | 68.4% | 69.8% | 54.6% |
| 2000 | 30 | 2 | 31.9% | 29.5% | 19.0% | 19.9% | 14.6% |
| 2000 | 30 | 4 | 73.5% | 73.0% | 45.6% | 46.1% | 35.0% |
| 2000 | 30 | 8 | 94.2% | 92.5% | 68.1% | 69.6% | 54.4% |
| 2000 | 180 | 2 | 29.8% | 28.9% | 18.0% | 18.8% | 12.9% |
| 2000 | 180 | 4 | 68.5% | 71.3% | 43.4% | 43.8% | 31.0% |
| 2000 | 180 | 8 | 91.0% | 90.5% | 65.9% | 66.6% | 47.7% |

Representative dates:

- Terra: 2024-07-12 (6,162 rows)
- Aqua: 2024-07-19 (15,517 rows)
- S-NPP: 2024-07-30 (82,443 rows)
- NOAA-20: 2024-07-29 (92,596 rows)
- NOAA-21: 2024-07-07 (87,637 rows)

## Limitations

- A nearest neighbor, a neighborhood count, and a DBSCAN component describe archived rows. They are not confirmed physical fires.
- same_fire is not_assessed. No row is labeled as the same fire as another row.
- DBSCAN is fit separately on each UTC date. Rows from the adjacent date are included only when their clock falls inside the 180-minute midnight margin. Cluster counts from those partitions are not a month-long census and are not additive.
- Neighborhood counts stop at 5 km. The unrestricted same-day nearest neighbor is a separate k=2 query, so a neighbor beyond 5 km still has a distance.
- A 0-minute window is the archived acquisition minute. That is the clock resolution of these files, not proof of the same instant.
- Exact-duplicate counts in this report use the loaded analysis fields. They omit version, type, and bright_t31. The July temporal scan remains the full-line duplicate account: 0 extra full lines, and 5 extra location-time keys.
- Same coordinate means bit-identical float64 latitude and longitude after parsing the CSV. It is not a rounded cell.
- S-NPP dates with no delivered rows are left out. They are not zero detections and they are not filled from another sensor.
- Dates 16, 24, and 29 July are used only to the extent S-NPP rows are present. Partial delivery is not repaired.
- NOAA-20 and NOAA-21 processing level is unresolved. The local filenames use fire_archive, while the FIRMS download readme says standard-quality data are not yet available for those sensors. The version column is not used as a processing stream.
- No harmonization coefficient is calculated. XGBoost is not trained.
- MODIS confidence stays on 0-100. VIIRS confidence stays l, n, or h. The two scales are not converted.
- FRP quantiles keep zero and negative values. No FRP filter is applied.

## Reproduce

From `backend`, with the July CSVs already extracted under `data/raw/monthly_2024_07/`:

```bash
.venv\Scripts\python -m fire_data.within_sensor_analysis
.venv\Scripts\python -m pytest
```

The CSVs stay gitignored. This command does not modify them.
