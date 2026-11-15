# Investigation of two anomalies on 2024-07-07

**Scope:** one-day global observations. This note is separate from `eda_report.md` and does not replace it.

Two patterns from the exploratory summary are examined here: VIIRS brightness stored at exactly 367 K, and two Aqua FRP rows stored as 7956.3 and 7328.1. The raw CSV files are read and are not rewritten.

## How the statements are separated

Verified facts are measurements from these files or statements quoted from the cited product documents. Hypotheses are interpretations that the files and documents make plausible and do not prove row by row. Unresolved questions are left open on purpose.

## Documents consulted

FIRMS download readme, file-code definitions for M-C61, J1V-C2, J2V-C2, and SV-C2: https://firms.modaps.eosdis.nasa.gov/download/Readme.txt

FIRMS active-fire attributes for MODIS and VIIRS: https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs

Schroeder, Giglio, and Hall, Collection 2 VIIRS 375 m Active Fire Product User's Guide, version 1.2, June 2025, FAQ on I4 saturation: https://www.earthdata.nasa.gov/s3fs-public/2025-06/VIIRS_C2_AF-375m_User_Guide_1.2.pdf

## VIIRS brightness

The frequency tables count original brightness strings. Numerically equal texts such as `367` and `367.0` stay distinct in the text column and are combined only in the numeric total.

| Satellite | Rows equal to 367 | Share | l | n | h | h below 367 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NOAA-20 | 3,190 | 3.87% | 482 | 0 | 2,708 | 0 |
| NOAA-21 | 7,305 | 8.34% | 426 | 0 | 6,879 | 0 |
| S-NPP | 5,600 | 6.45% | 433 | 0 | 5,167 | 0 |

### NOAA-20

Rows numerically equal to 367: 3,190 (3.87%). Rows above 367: 0. Rows in [366, 367): 0. Highest stored brightness below 367: 357.03 (1 row).

Day/night among the 367 K rows: D 2,994, N 196.

Where brightness is numerically 367, stored bright_t31 has minimum 273.26, median 306.26, and maximum 378.91. Stored FRP has minimum 0.00, median 17.37, and maximum 1,168.99. The largest FRP in the archive is 1,168.99 MW and its brightness text is 367.

Original CSV brightness text from 366 K through 367 K:

| Stored brightness text | Parsed value (K) | Rows |
| --- | ---: | ---: |
| 367 | 367 | 3,190 |

### NOAA-21

Rows numerically equal to 367: 7,305 (8.34%). Rows above 367: 0. Rows in [366, 367): 0. Highest stored brightness below 367: 356.5 (1 row).

Day/night among the 367 K rows: D 6,384, N 921.

Where brightness is numerically 367, stored bright_t31 has minimum 275.75, median 304.35, and maximum 374.48. Stored FRP has minimum 0.00, median 18.96, and maximum 1,058.92. The largest FRP in the archive is 1,740.42 MW and its brightness text is 334.74.

Original CSV brightness text from 366 K through 367 K:

| Stored brightness text | Parsed value (K) | Rows |
| --- | ---: | ---: |
| 367 | 367 | 7,305 |

### S-NPP

Rows numerically equal to 367: 5,600 (6.45%). Rows above 367: 0. Rows in [366, 367): 0. Highest stored brightness below 367: 358.31 (1 row).

Day/night among the 367 K rows: D 5,300, N 300.

Where brightness is numerically 367, stored bright_t31 has minimum 272.19, median 306.27, and maximum 384.53. Stored FRP has minimum 0.00, median 17.66, and maximum 974.25. The largest FRP in the archive is 974.25 MW and its brightness text is 367.

Original CSV brightness text from 366 K through 367 K:

| Stored brightness text | Parsed value (K) | Rows |
| --- | ---: | ---: |
| 367 | 367 | 5,600 |

The empty interval from the mid-350s to 367 K is a property of the stored numbers. A filled tail rounded onto a 0.01 K grid would leave occupied bins immediately below 367; those bins are empty. Values above 367 are also absent. Decimal-place counts describe storage precision separately: most brightness texts have two decimal places, and a two-decimal text does not by itself produce a spike at one value. The cross-tab shows that every high-confidence flag in these files sits on 367, while some 367 rows carry the low flag. The user's guide statement is quoted under verified facts. Whether each 367 row is the guide's typical saturation assignment is a hypothesis, because these CSVs do not carry an I4 saturation bit.

## Extreme Aqua FRP

The rows below are the original CSV fields for the FRP texts 7956.3 and 7328.1. Confidence remains the stored MODIS integer.

| Line | Latitude | Longitude | UTC | FRP | Confidence | Brightness | bright_t31 | Scan | Track | Day/night | Type | Version |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| 19915 | 48.1499 | -120.4706 | 2232 | 7956.3 | 75 | 475.9 | 334 | 3.9 | 1.8 | D | 0 | 61.03 |
| 19920 | 48.1577 | -120.4744 | 2232 | 7328.1 | 0 | 470.9 | 331.5 | 3.9 | 1.8 | D | 0 | 61.03 |

Separation between these two stored rows: 912.0 m and 0 minutes.

Great-circle distance on a sphere of radius 6371008.8 m, the radius used in the exploratory overlap summary. Time separation is the absolute difference of UTC minutes from acq_time on 2024-07-07.

### Neighbors of Aqua line 19915 (FRP 7956.3)

A neighbor is another archived detection inside the search radius. The same acquisition minute is temporal coincidence to the stored minute, not a fire identity.

| Radius | Time window | Neighbors | By satellite |
| ---: | --- | ---: | --- |
| 1,000 m | ≤ 0 min | 1 | Aqua 1 |
| 1,000 m | ≤ 30 min | 1 | Aqua 1 |
| 1,000 m | ≤ 180 min | 21 | Aqua 1, N20 2, N21 4, SNPP 14 |
| 1,000 m | any time on this date | 93 | Aqua 2, N20 28, N21 22, SNPP 37, Terra 4 |
| 5,000 m | ≤ 0 min | 8 | Aqua 8 |
| 5,000 m | ≤ 30 min | 8 | Aqua 8 |
| 5,000 m | ≤ 180 min | 81 | Aqua 10, N20 5, N21 25, SNPP 41 |
| 5,000 m | any time on this date | 288 | Aqua 13, N20 85, N21 71, SNPP 107, Terra 12 |
| 10,000 m | ≤ 0 min | 9 | Aqua 9 |
| 10,000 m | ≤ 30 min | 9 | Aqua 9 |
| 10,000 m | ≤ 180 min | 98 | Aqua 11, N20 8, N21 31, SNPP 48 |
| 10,000 m | any time on this date | 338 | Aqua 15, N20 98, N21 85, SNPP 123, Terra 17 |

Same UTC minute and within 5,000 m:

| Satellite | Line | Distance (m) | Δt (min) | UTC | Latitude | Longitude | FRP | Confidence | Scan | Track | Brightness | Day/night |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| Aqua | 19920 | 912.0 | 0 | 2232 | 48.1577 | -120.4744 | 7328.1 | 0 | 3.9 | 1.8 | 470.9 | D |
| Aqua | 19916 | 1,829.6 | 0 | 2232 | 48.1663 | -120.4726 | 338.9 | 71 | 3.9 | 1.8 | 346.5 | D |
| Aqua | 19913 | 1,836.9 | 0 | 2232 | 48.1334 | -120.4694 | 304.8 | 70 | 3.9 | 1.8 | 344.8 | D |
| Aqua | 19917 | 2,191.9 | 0 | 2232 | 48.1419 | -120.4436 | 200.6 | 69 | 3.9 | 1.8 | 334.9 | D |
| Aqua | 19914 | 2,538.8 | 0 | 2232 | 48.1507 | -120.4364 | 1536.2 | 100 | 3.9 | 1.8 | 393.8 | D |
| Aqua | 19918 | 2,669.6 | 0 | 2232 | 48.1585 | -120.437 | 2727 | 94 | 3.9 | 1.8 | 418.2 | D |
| Aqua | 19922 | 2,858.2 | 0 | 2232 | 48.1739 | -120.4844 | 197.6 | 65 | 3.9 | 1.8 | 335.1 | D |
| Aqua | 19921 | 3,726.9 | 0 | 2232 | 48.175 | -120.4373 | 77.8 | 15 | 3.9 | 1.8 | 319.8 | D |

Nearest 12 rows within 5,000 m at any time on this date. A short distance with a large time gap is still only a spatial neighbor:

| Satellite | Line | Distance (m) | Δt (min) | UTC | Latitude | Longitude | FRP | Confidence | Scan | Track | Brightness | Day/night |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| S-NPP | 20752 | 56.7 | 722 | 1030 | 48.15041 | -120.4706 | 1.01 | n | 0.52 | 0.41 | 306.43 | N |
| NOAA-20 | 21364 | 58.4 | 697 | 1055 | 48.1503 | -120.47009 | 13.17 | n | 0.63 | 0.54 | 305.93 | N |
| NOAA-21 | 19198 | 74.2 | 747 | 1005 | 48.14957 | -120.46973 | 1.02 | n | 0.38 | 0.36 | 303.25 | N |
| NOAA-20 | 21386 | 110.8 | 697 | 1055 | 48.14892 | -120.47033 | 1.81 | n | 0.63 | 0.54 | 300.69 | N |
| NOAA-20 | 15311 | 140.5 | 798 | 0914 | 48.14865 | -120.47088 | 1.37 | n | 0.34 | 0.56 | 304.81 | N |
| S-NPP | 76175 | 169.3 | 34 | 2158 | 48.14941 | -120.46844 | 5.44 | n | 0.57 | 0.69 | 339.83 | D |
| S-NPP | 76176 | 190.8 | 34 | 2158 | 48.1494 | -120.47306 | 5.44 | l | 0.57 | 0.69 | 336.56 | D |
| S-NPP | 20734 | 305.6 | 722 | 1030 | 48.15255 | -120.46951 | 9.64 | n | 0.52 | 0.41 | 313.39 | N |
| NOAA-21 | 19197 | 316.3 | 747 | 1005 | 48.15035 | -120.47481 | 1.02 | n | 0.38 | 0.36 | 314.77 | N |
| NOAA-20 | 21385 | 336.7 | 697 | 1055 | 48.15024 | -120.47511 | 4.75 | n | 0.63 | 0.54 | 311.71 | N |
| NOAA-21 | 19190 | 354.3 | 747 | 1005 | 48.1528 | -120.46862 | 12.86 | n | 0.38 | 0.36 | 321.15 | N |
| Aqua | 5724 | 362.1 | 669 | 1123 | 48.1529 | -120.4687 | 23.2 | 46 | 1.9 | 1.3 | 309.9 | N |

The JSON file contains all 288 rows within 5,000 m and every row within 10,000 m.

### Neighbors of Aqua line 19920 (FRP 7328.1)

A neighbor is another archived detection inside the search radius. The same acquisition minute is temporal coincidence to the stored minute, not a fire identity.

| Radius | Time window | Neighbors | By satellite |
| ---: | --- | ---: | --- |
| 1,000 m | ≤ 0 min | 2 | Aqua 2 |
| 1,000 m | ≤ 30 min | 2 | Aqua 2 |
| 1,000 m | ≤ 180 min | 23 | Aqua 2, N20 2, N21 8, SNPP 11 |
| 1,000 m | any time on this date | 87 | Aqua 3, N20 25, N21 20, SNPP 35, Terra 4 |
| 5,000 m | ≤ 0 min | 8 | Aqua 8 |
| 5,000 m | ≤ 30 min | 8 | Aqua 8 |
| 5,000 m | ≤ 180 min | 76 | Aqua 10, N20 5, N21 22, SNPP 39 |
| 5,000 m | any time on this date | 266 | Aqua 13, N20 78, N21 65, SNPP 98, Terra 12 |
| 10,000 m | ≤ 0 min | 10 | Aqua 10 |
| 10,000 m | ≤ 30 min | 10 | Aqua 10 |
| 10,000 m | ≤ 180 min | 103 | Aqua 13, N20 8, N21 33, SNPP 49 |
| 10,000 m | any time on this date | 346 | Aqua 18, N20 99, N21 87, SNPP 124, Terra 18 |

Same UTC minute and within 5,000 m:

| Satellite | Line | Distance (m) | Δt (min) | UTC | Latitude | Longitude | FRP | Confidence | Scan | Track | Brightness | Day/night |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| Aqua | 19915 | 912.0 | 0 | 2232 | 48.1499 | -120.4706 | 7956.3 | 75 | 3.9 | 1.8 | 475.9 | D |
| Aqua | 19916 | 965.6 | 0 | 2232 | 48.1663 | -120.4726 | 338.9 | 71 | 3.9 | 1.8 | 346.5 | D |
| Aqua | 19922 | 1,948.1 | 0 | 2232 | 48.1739 | -120.4844 | 197.6 | 65 | 3.9 | 1.8 | 335.1 | D |
| Aqua | 19913 | 2,727.4 | 0 | 2232 | 48.1334 | -120.4694 | 304.8 | 70 | 3.9 | 1.8 | 344.8 | D |
| Aqua | 19918 | 2,775.6 | 0 | 2232 | 48.1585 | -120.437 | 2727 | 94 | 3.9 | 1.8 | 418.2 | D |
| Aqua | 19917 | 2,882.3 | 0 | 2232 | 48.1419 | -120.4436 | 200.6 | 69 | 3.9 | 1.8 | 334.9 | D |
| Aqua | 19914 | 2,924.4 | 0 | 2232 | 48.1507 | -120.4364 | 1536.2 | 100 | 3.9 | 1.8 | 393.8 | D |
| Aqua | 19921 | 3,357.3 | 0 | 2232 | 48.175 | -120.4373 | 77.8 | 15 | 3.9 | 1.8 | 319.8 | D |

Nearest 12 rows within 5,000 m at any time on this date. A short distance with a large time gap is still only a spatial neighbor:

| Satellite | Line | Distance (m) | Δt (min) | UTC | Latitude | Longitude | FRP | Confidence | Scan | Track | Brightness | Day/night |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| S-NPP | 20726 | 79.9 | 722 | 1030 | 48.15745 | -120.47339 | 10.41 | h | 0.52 | 0.41 | 367 | N |
| NOAA-21 | 19185 | 166.7 | 747 | 1005 | 48.15684 | -120.47256 | 12.86 | n | 0.38 | 0.36 | 355.9 | N |
| NOAA-20 | 68887 | 175.3 | 111 | 2041 | 48.15686 | -120.4724 | 64.58 | h | 0.39 | 0.36 | 367 | D |
| NOAA-20 | 15337 | 187.5 | 798 | 0914 | 48.15924 | -120.47543 | 1.5 | n | 0.34 | 0.56 | 305.09 | N |
| NOAA-21 | 71078 | 204.2 | 60 | 2132 | 48.15894 | -120.47643 | 226.1 | l | 0.59 | 0.53 | 367 | D |
| S-NPP | 20739 | 209.7 | 722 | 1030 | 48.15885 | -120.47216 | 15.1 | n | 0.52 | 0.41 | 351.92 | N |
| NOAA-21 | 19184 | 239.0 | 747 | 1005 | 48.15763 | -120.47762 | 3.55 | n | 0.38 | 0.36 | 332.17 | N |
| NOAA-20 | 21379 | 266.3 | 697 | 1055 | 48.15627 | -120.47728 | 13.26 | n | 0.63 | 0.54 | 348.11 | N |
| NOAA-20 | 21358 | 279.6 | 697 | 1055 | 48.15611 | -120.47148 | 13.17 | h | 0.63 | 0.54 | 367 | N |
| S-NPP | 20746 | 292.1 | 722 | 1030 | 48.15512 | -120.47366 | 15.1 | n | 0.52 | 0.41 | 344.18 | N |
| NOAA-20 | 15335 | 311.1 | 798 | 0914 | 48.15903 | -120.47071 | 6.74 | n | 0.34 | 0.56 | 350.92 | N |
| S-NPP | 73480 | 319.1 | 135 | 2017 | 48.15762 | -120.4701 | 50.2 | l | 0.39 | 0.44 | 315.19 | D |

The JSON file contains all 266 rows within 5,000 m and every row within 10,000 m.

The neighbor tables are the spatial and temporal evidence assembled for this pass. Nearby detections are not classified as the same fire.

## Verified facts

- All counts in this investigation are one-day global observations for 2024-07-07.
- A count is a count of archived detection rows. Unique fires are not identified.
- No harmonization factor is calculated.
- The FIRMS download readme maps the file codes J1V-C2, J2V-C2, and SV-C2 to the VIIRS 375 m products for NOAA-20, NOAA-21, and S-NPP. It maps fire_archive_SV-C2 to the standard VNP14IMGTML product and fire_archive_M-C61 to MCD14ML.
- The FIRMS attribute table defines the VIIRS field Brightness as the I-4 channel brightness temperature in kelvin. These archives store that field under the column name brightness. They do not contain a column named bright_ti4.
- The Collection 2 VIIRS 375 m Active Fire User's Guide, version 1.2, says that in the typical I4 saturation case the pixel is assigned the nominal saturation temperature of 367 K. The same answer describes two other saturation situations: a digital-count fold-over that appears as an abnormally low temperature, and mixed saturated and unsaturated samples from onboard aggregation.
- The FIRMS attribute table says VIIRS high-confidence pixels are associated with day or nighttime saturated pixels. Low, nominal, and high remain the stored flags l, n, and h.
- NOAA-20: 82,372 detections; maximum stored brightness text 367; 3,190 rows (3.87%) are numerically equal to 367; 0 rows are numerically above 367; no stored value falls in [366, 367); the highest brightness text below 367 is 357.03 (1 row). Original 367 texts: 367 (3,190). Decimal-place counts: 0 decimal places: 3,974, 1 decimal places: 7,278, 2 decimal places: 71,120. Integer text 367 accounts for 3,190 of 3,974 brightness values stored with no decimal point.
- NOAA-20 confidence among rows numerically equal to 367: h 2,708, l 482. High-confidence flag h below 367: 0.
- NOAA-21: 87,637 detections; maximum stored brightness text 367; 7,305 rows (8.34%) are numerically equal to 367; 0 rows are numerically above 367; no stored value falls in [366, 367); the highest brightness text below 367 is 356.5 (1 row). Original 367 texts: 367 (7,305). Decimal-place counts: 0 decimal places: 8,159, 1 decimal places: 7,317, 2 decimal places: 72,161. Integer text 367 accounts for 7,305 of 8,159 brightness values stored with no decimal point.
- NOAA-21 confidence among rows numerically equal to 367: h 6,879, l 426. High-confidence flag h below 367: 0.
- S-NPP: 86,840 detections; maximum stored brightness text 367; 5,600 rows (6.45%) are numerically equal to 367; 0 rows are numerically above 367; no stored value falls in [366, 367); the highest brightness text below 367 is 358.31 (1 row). Original 367 texts: 367 (5,600). Decimal-place counts: 0 decimal places: 6,467, 1 decimal places: 7,316, 2 decimal places: 73,057. Integer text 367 accounts for 5,600 of 6,467 brightness values stored with no decimal point.
- S-NPP confidence among rows numerically equal to 367: h 5,167, l 433. High-confidence flag h below 367: 0.
- Aqua source row line 19915 in modis/fire_archive_M-C61_850118.csv: latitude 48.1499, longitude -120.4706, brightness 475.9, scan 3.9, track 1.8, acq_date 2024-07-07, acq_time 2232 UTC, satellite Aqua, instrument MODIS, confidence 75, version 61.03, bright_t31 334, frp 7956.3, daynight D, type 0.
- Aqua source row line 19920 in modis/fire_archive_M-C61_850118.csv: latitude 48.1577, longitude -120.4744, brightness 470.9, scan 3.9, track 1.8, acq_date 2024-07-07, acq_time 2232 UTC, satellite Aqua, instrument MODIS, confidence 0, version 61.03, bright_t31 331.5, frp 7328.1, daynight D, type 0.
- The two target Aqua rows are 912.0 m apart on a great circle and 0 minutes apart in UTC acq_time.
- Great-circle distance on a sphere of radius 6371008.8 m, the radius used in the exploratory overlap summary. Time separation is the absolute difference of UTC minutes from acq_time on 2024-07-07.

## Hypotheses

- The repeated stored value 367 is the nominal I4 saturation temperature described by the Collection 2 375 m user's guide, recorded in the FIRMS brightness column. This investigation can test the stored number and the published definition. It cannot inspect the Level-1 saturation flag for an individual CSV row.
- A brightness value well below 367 can include the guide's fold-over or aggregation cases. Those cases are not identified by the number 367, and this pass does not classify them.
- The two Aqua FRP values are large stored retrievals for their pixels. Their size, identical acquisition minute, and separation relative to the stored scan length describe the observation geometry. They do not by themselves establish a single physical fire.

## Unresolved questions

- The CSV has no I4 saturation quality bit, so row-level saturation remains unverified even where brightness is exactly 367.
- The VIIRS files name the second thermal column bright_t31. The FIRMS VIIRS attribute table names the I-5 brightness temperature Bright_ti5, also called Brightness_2 in web services. The column correspondence is not written inside these files.
- The FIRMS download readme says standard-quality data were not yet available from FIRMS for NOAA-20 and NOAA-21, while these files are named fire_archive_J1V-C2 and fire_archive_J2V-C2 and their version field is 2 with no NRT suffix. The processing stream is not fully identified by the readme entry that was current at retrieval.
- Nearby detections from Terra, NOAA-20, NOAA-21, and S-NPP are spatial and temporal neighbors under the stated search windows. They are not classified as the same fire.
- This date supplies no historical baseline for how often 367 K or these FRP values occur.

## Reproduction

From the backend directory:

```bash
.venv\Scripts\python -m fire_data.investigate
```

The command writes `reports/anomaly_investigation.md` and `reports/anomaly_summary.json`. It leaves `reports/eda_report.md`, `reports/eda_summary.json`, `reports/figures/`, and `data/raw/` unchanged.
