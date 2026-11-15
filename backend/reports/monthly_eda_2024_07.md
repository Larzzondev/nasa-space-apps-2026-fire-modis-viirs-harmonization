# July 2024 monthly exploratory summary

Statistics describe rows in the four FIRMS CSVs for 1–31 July 2024. They are not unique-fire counts, and sensor totals are not a ranking of detection sensitivity.

## Detection counts

| Satellite | Sensor archive | Delivered rows |
| --- | --- | ---: |
| Terra | modis | 195,316 |
| Aqua | modis | 481,320 |
| N20 | viirs_noaa20 | 2,902,597 |
| N21 | viirs_noaa21 | 2,771,214 |
| SNPP | viirs_snpp | 1,635,020 |

## FRP

FRP is the stored fire radiative power. The summaries keep every parsed finite value, including extremes.

- Terra: median 19.1, mean 45.551, p05 5.7, p95 147.2, p99 462, maximum 6002.5. Zero-FRP rows: 393.
  Maximum stored FRP text 6002.5 appears on 1 row(s). Example line 563805: 2024-07-26 1854 UTC, latitude 40.026, longitude -121.7044, confidence 100, brightness 500.
- Aqua: median 21.6, mean 51.4279, p05 6.6, p95 165.9, p99 521.6, maximum 10950. Zero-FRP rows: 155.
  Maximum stored FRP text 10950 appears on 1 row(s). Example line 174408: 2024-07-09 2218 UTC, latitude 59.7083, longitude -118.327, confidence 100, brightness 504.9.
- N20: median 5.14, mean 10.6352, p05 0.91, p95 35.4, p99 104.77, maximum 2825.18. Zero-FRP rows: 809.
  Maximum stored FRP text 2825.18 appears on 1 row(s). Example line 362255: 2024-07-05 2204 UTC, latitude -25.50855, longitude 30.79288, confidence h, brightness 367.
- N21: median 6.09, mean 12.6347, p05 1.05, p95 40.96, p99 129.72, maximum 2858.66. Zero-FRP rows: 1,710.
  Maximum stored FRP text 2858.66 appears on 1 row(s). Example line 2103472: 2024-07-25 1110 UTC, latitude 40.00805, longitude -121.84074, confidence h, brightness 367.
- SNPP: median 5.06, mean 10.6144, p05 0.89, p95 36.27, p99 103.89, maximum 2824.71. Zero-FRP rows: 373.
  Maximum stored FRP text 2824.71 appears on 1 row(s). Example line 1427359: 2024-07-23 2159 UTC, latitude 52.71067, longitude -117.89853, confidence l, brightness 367.

## Day and night

The day/night value is the archive flag.

- Terra: day 104,032, night 91,284.
- Aqua: day 448,221, night 33,099.
- N20: day 2,018,537, night 884,060.
- N21: day 1,907,205, night 864,009.
- SNPP: day 1,125,000, night 510,020.

## Confidence

MODIS confidence remains an integer from 0 through 100. VIIRS confidence remains the stored flag l, n, or h. The two summaries are separate.

- Terra (modis_0_100): median 69, confidence 0 on 2,414 rows, confidence 100 on 30,113 rows. Every integer from 0 through 100 is stored in the JSON and in confidence_modis.png.
- Aqua (modis_0_100): median 69, confidence 0 on 4,240 rows, confidence 100 on 29,197 rows. Every integer from 0 through 100 is stored in the JSON and in confidence_modis.png.
- N20 (viirs_lnh): l 265,829, n 2,479,081, h 157,687.
- N21 (viirs_lnh): l 257,640, n 2,324,309, h 189,265.
- SNPP (viirs_lnh): l 133,710, n 1,401,558, h 99,752.

## Brightness

- Terra: median 316.7, mean 321.8791, p05 302.6, p95 358.2, p99 400.2, maximum 500.
- Aqua: median 322.3, mean 327.3533, p05 309.2, p95 362.2, p99 402.681, maximum 510.
- N20: median 336.21, mean 333.4209, p05 300.17, p95 367, p99 367, maximum 367.
- N21: median 335.88, mean 333.167, p05 299.99, p95 367, p99 367, maximum 367.
- SNPP: median 336.1, mean 333.402, p05 300.05, p95 367, p99 367, maximum 367.

VIIRS rows whose brightness text is exactly `367`:

- viirs_snpp: h 99,752, l 9,011. Rows above 367 K: 0. Rows in [360 K, 367 K): 0.
  Every stored h flag in this archive is on brightness text 367. No n flag is on that value.
- viirs_noaa20: h 157,687, l 16,553. Rows above 367 K: 0. Rows in [360 K, 367 K): 0.
  Every stored h flag in this archive is on brightness text 367. No n flag is on that value.
- viirs_noaa21: h 189,265, l 17,239. Rows above 367 K: 0. Rows in [360 K, 367 K): 0.
  Every stored h flag in this archive is on brightness text 367. No n flag is on that value.

The CSV has no Level-1 saturation flag, so a stored value of 367 K is not marked as confirmed saturation.

## Weekly delivered rows

Weekly totals add the rows whose acquisition dates fall in that Monday-start span. Dates with zero delivered rows are listed and are not filled in.

- Terra: 2024-07-01 to 2024-07-07 38,674; 2024-07-08 to 2024-07-14 48,237; 2024-07-15 to 2024-07-21 43,144; 2024-07-22 to 2024-07-28 50,731; 2024-07-29 to 2024-07-31 14,530. Dates with zero delivered rows: none.
- Aqua: 2024-07-01 to 2024-07-07 86,980; 2024-07-08 to 2024-07-14 110,565; 2024-07-15 to 2024-07-21 107,863; 2024-07-22 to 2024-07-28 131,582; 2024-07-29 to 2024-07-31 44,330. Dates with zero delivered rows: none.
- N20: 2024-07-01 to 2024-07-07 529,793; 2024-07-08 to 2024-07-14 693,526; 2024-07-15 to 2024-07-21 634,667; 2024-07-22 to 2024-07-28 788,830; 2024-07-29 to 2024-07-31 255,781. Dates with zero delivered rows: none.
- N21: 2024-07-01 to 2024-07-07 521,018; 2024-07-08 to 2024-07-14 680,791; 2024-07-15 to 2024-07-21 550,066; 2024-07-22 to 2024-07-28 765,620; 2024-07-29 to 2024-07-31 253,719. Dates with zero delivered rows: none.
- SNPP: 2024-07-01 to 2024-07-07 539,245; 2024-07-08 to 2024-07-14 209,666; 2024-07-15 to 2024-07-21 486,496; 2024-07-22 to 2024-07-28 211,982; 2024-07-29 to 2024-07-31 187,631. Dates with zero delivered rows: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28.

## Geographic concentration

Cells are 1 degree of latitude and longitude, identified by the floor of each coordinate. A dense cell is a concentration of archive rows, not one fire.

- Terra: 5,424 occupied cells. Densest cell floor (58, -115) has 1,977 rows, 1.01% of located rows.
- Aqua: 5,880 occupied cells. Densest cell floor (-11, 15) has 2,912 rows, 0.61% of located rows.
- N20: 8,777 occupied cells. Densest cell floor (58, -115) has 20,092 rows, 0.69% of located rows.
- N21: 8,669 occupied cells. Densest cell floor (59, -122) has 19,185 rows, 0.69% of located rows.
- SNPP: 7,934 occupied cells. Densest cell floor (59, -122) has 15,124 rows, 0.93% of located rows.

## July 7 cross-check

- Terra: monthly file delivered 7,044 rows on 2024-07-07; the separate one-day sample has 7,044 rows; difference 0.
- Aqua: monthly file delivered 13,366 rows on 2024-07-07; the separate one-day sample has 13,366 rows; difference 0.
- N20: monthly file delivered 82,372 rows on 2024-07-07; the separate one-day sample has 82,372 rows; difference 0.
- N21: monthly file delivered 87,637 rows on 2024-07-07; the separate one-day sample has 87,637 rows; difference 0.
- SNPP: monthly file delivered 86,840 rows on 2024-07-07; the separate one-day sample has 86,840 rows; difference 0.

## Limitations

- MODIS and VIIRS have different spatial resolutions and detection characteristics. Row counts are not a comparison of sensitivity.
- Repeat detections are not necessarily unique fires. Exact duplicate rows and repeated location-time keys are retained.
- A date with zero delivered rows, and a date whose source file is missing, are not zero fire detections.
- MODIS confidence is an integer from 0 through 100. VIIRS confidence is the flag l, n, or h. The scales are not interchangeable.
- Processing-level provenance stays unresolved. The ZIP name, the fire_archive prefix, and the version field are not treated as a processing stream.
- One month cannot establish a globally valid harmonization factor. No coefficient is calculated.
- Spatial proximity is not assessed here and cannot, by itself, prove that two observations are the same fire.
- FRP is the stored fire radiative power value. It is not fire size and it is not total fire energy.
