# July 2024 temporal coverage

The counts below are rows delivered in the extracted FIRMS CSVs for 1–31 July 2024. A delivered-row count of zero means the CSV is present and has no row with that acquisition date. It is not a measurement of zero fire activity. A missing source file is a separate status and has no delivered-row count.

## Integrity

Ingestion manifest passed: True.

| Dataset | Expected rows | Delivered rows | Difference | CSV SHA-256 |
| --- | ---: | ---: | ---: | --- |
| modis | 676,636 | 676,636 | 0 | `97e1a4312fbe488e63fd06461865b21dd5d01c419f2e80fa6e178c0015f10c81` |
| viirs_snpp | 1,635,020 | 1,635,020 | 0 | `bc5ff311c2df9113baf4eedaf4247d55954e8f4fa2ca052f940a943365314f21` |
| viirs_noaa20 | 2,902,597 | 2,902,597 | 0 | `9a192db30e307c257955047ca1177e3f2f463b8c8cdfda7b28ceac6b3aa92bd5` |
| viirs_noaa21 | 2,771,214 | 2,771,214 | 0 | `c86e46d4ca730eea6db448ff928126ddc6b44ba4c4d11dfbc3a2d999f4937007` |

Total delivered rows: 7,985,467. Reference total: 7,985,467. Difference: 0.

Exact duplicate rows retained: 0. Extra location-time keys retained: 5. Duplicate detection uses 128-bit BLAKE2b digests of the stored fields. No row was removed.

modis: exact duplicate rows 0, extra location-time keys 0.
viirs_snpp: exact duplicate rows 0, extra location-time keys 0.
viirs_noaa20: exact duplicate rows 0, extra location-time keys 1.
viirs_noaa21: exact duplicate rows 0, extra location-time keys 4.

Empty cells: {}. Malformed-field counts: {}.

Each ZIP still has the checksum recorded at ingestion, and each extracted CSV checksum matches that manifest. The 7 July sample files were hashed before and after this scan.

## Daily matrix

Terra and Aqua come from the MODIS CSV. NOAA-20, NOAA-21, and S-NPP come from their own CSVs. `zero_rows_delivered` is a property of the file. `source_file_missing` would mean the CSV itself is absent.

| Date | Terra | Aqua | NOAA-20 | NOAA-21 | S-NPP |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024-07-01 | 5,335 | 11,085 | 75,912 | 70,842 | 76,090 |
| 2024-07-02 | 7,052 | 11,553 | 76,448 | 75,850 | 77,742 |
| 2024-07-03 | 5,110 | 13,003 | 70,183 | 69,114 | 71,875 |
| 2024-07-04 | 4,711 | 10,524 | 73,754 | 70,625 | 74,140 |
| 2024-07-05 | 4,643 | 15,312 | 73,331 | 72,047 | 74,121 |
| 2024-07-06 | 4,779 | 12,137 | 77,793 | 74,903 | 78,437 |
| 2024-07-07 | 7,044 | 13,366 | 82,372 | 87,637 | 86,840 |
| 2024-07-08 | 8,180 | 16,290 | 107,599 | 101,659 | 106,502 |
| 2024-07-09 | 8,022 | 16,528 | 112,171 | 108,575 | 103,164 |
| 2024-07-10 | 8,117 | 21,073 | 124,687 | 121,607 | 0 rows delivered |
| 2024-07-11 | 7,689 | 15,009 | 111,556 | 109,401 | 0 rows delivered |
| 2024-07-12 | 6,162 | 17,356 | 98,679 | 101,150 | 0 rows delivered |
| 2024-07-13 | 5,141 | 12,133 | 75,315 | 78,327 | 0 rows delivered |
| 2024-07-14 | 4,926 | 12,176 | 63,519 | 60,072 | 0 rows delivered |
| 2024-07-15 | 4,099 | 15,315 | 77,359 | 72,728 | 0 rows delivered |
| 2024-07-16 | 6,040 | 14,254 | 86,129 | 85,741 | 15,643 |
| 2024-07-17 | 6,218 | 16,512 | 88,818 | 83,675 | 89,521 |
| 2024-07-18 | 7,150 | 16,467 | 104,021 | 101,410 | 105,489 |
| 2024-07-19 | 7,306 | 15,517 | 101,200 | 97,945 | 102,434 |
| 2024-07-20 | 6,354 | 17,112 | 94,486 | 33,039 | 94,011 |
| 2024-07-21 | 5,977 | 12,686 | 82,654 | 75,528 | 79,398 |
| 2024-07-22 | 6,148 | 15,779 | 93,738 | 90,257 | 90,260 |
| 2024-07-23 | 5,431 | 18,065 | 101,915 | 104,530 | 107,101 |
| 2024-07-24 | 7,950 | 20,325 | 123,134 | 119,286 | 14,621 |
| 2024-07-25 | 7,950 | 20,836 | 127,817 | 125,747 | 0 rows delivered |
| 2024-07-26 | 8,823 | 19,693 | 125,100 | 114,781 | 0 rows delivered |
| 2024-07-27 | 7,204 | 20,762 | 120,098 | 117,758 | 0 rows delivered |
| 2024-07-28 | 7,225 | 16,122 | 97,028 | 93,261 | 0 rows delivered |
| 2024-07-29 | 4,641 | 16,865 | 92,596 | 94,972 | 17,802 |
| 2024-07-30 | 4,390 | 15,461 | 78,611 | 77,275 | 82,443 |
| 2024-07-31 | 5,499 | 12,004 | 84,574 | 81,472 | 87,386 |

## S-NPP windows

The windows below were examined because earlier notes listed 10–16 July and 25–28 July. The table uses the rows in this CSV. Other archives having rows on the same date does not establish an S-NPP outage.

### 2024-07-10 through 2024-07-16

S-NPP dates with zero delivered rows: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15.
S-NPP dates with delivered rows: 2024-07-16.

| Date | S-NPP status | S-NPP rows | NOAA-20 rows | NOAA-21 rows | Terra rows | Aqua rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2024-07-10 | zero_rows_delivered | 0 rows delivered | 124,687 | 121,607 | 8,117 | 21,073 |
| 2024-07-11 | zero_rows_delivered | 0 rows delivered | 111,556 | 109,401 | 7,689 | 15,009 |
| 2024-07-12 | zero_rows_delivered | 0 rows delivered | 98,679 | 101,150 | 6,162 | 17,356 |
| 2024-07-13 | zero_rows_delivered | 0 rows delivered | 75,315 | 78,327 | 5,141 | 12,133 |
| 2024-07-14 | zero_rows_delivered | 0 rows delivered | 63,519 | 60,072 | 4,926 | 12,176 |
| 2024-07-15 | zero_rows_delivered | 0 rows delivered | 77,359 | 72,728 | 4,099 | 15,315 |
| 2024-07-16 | rows_delivered | 15,643 | 86,129 | 85,741 | 6,040 | 14,254 |

These dates describe rows stored in the local S-NPP CSV. A date with zero delivered rows is not evidence of zero fire activity, and rows in the other archives are not evidence of an S-NPP outage.

### 2024-07-25 through 2024-07-28

S-NPP dates with zero delivered rows: 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28.
S-NPP dates with delivered rows: none.

| Date | S-NPP status | S-NPP rows | NOAA-20 rows | NOAA-21 rows | Terra rows | Aqua rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2024-07-25 | zero_rows_delivered | 0 rows delivered | 127,817 | 125,747 | 7,950 | 20,836 |
| 2024-07-26 | zero_rows_delivered | 0 rows delivered | 125,100 | 114,781 | 8,823 | 19,693 |
| 2024-07-27 | zero_rows_delivered | 0 rows delivered | 120,098 | 117,758 | 7,204 | 20,762 |
| 2024-07-28 | zero_rows_delivered | 0 rows delivered | 97,028 | 93,261 | 7,225 | 16,122 |

These dates describe rows stored in the local S-NPP CSV. A date with zero delivered rows is not evidence of zero fire activity, and rows in the other archives are not evidence of an S-NPP outage.

## Smallest delivered days

These are the three dates with the smallest positive delivered-row counts for each satellite. They are dates the file did cover. They are not zero-row dates and they are not identified as outages.

- Terra: 2024-07-15 (4,099 rows), 2024-07-30 (4,390 rows), 2024-07-29 (4,641 rows).
  2024-07-15: rows fall in 18 UTC hours, from 00 through 23, with no rows in hour(s) 01, 05, 07, 10, 21, 22.
  2024-07-30: rows fall in 23 UTC hours, from 00 through 23, with no rows in hour(s) 22.
  2024-07-29: rows fall in 22 UTC hours, from 00 through 22, with no rows in hour(s) 21.
- Aqua: 2024-07-04 (10,524 rows), 2024-07-01 (11,085 rows), 2024-07-02 (11,553 rows).
  2024-07-04: rows fall in 20 UTC hours, from 01 through 22, with no rows in hour(s) 15, 21.
  2024-07-01: rows fall in 23 UTC hours, from 00 through 23, with no rows in hour(s) 15.
  2024-07-02: rows fall in 23 UTC hours, from 00 through 23, with no rows in hour(s) 15.
- N20: 2024-07-14 (63,519 rows), 2024-07-03 (70,183 rows), 2024-07-05 (73,331 rows).
  2024-07-14: rows fall in 24 UTC hours, from 00 through 23.
  2024-07-03: rows fall in 24 UTC hours, from 00 through 23.
  2024-07-05: rows fall in 24 UTC hours, from 00 through 23.
- N21: 2024-07-20 (33,039 rows), 2024-07-14 (60,072 rows), 2024-07-03 (69,114 rows).
  2024-07-20: rows fall in 18 UTC hours, from 00 through 23, with no rows in hour(s) 08, 09, 10, 11, 12, 13.
  2024-07-14: rows fall in 24 UTC hours, from 00 through 23.
  2024-07-03: rows fall in 24 UTC hours, from 00 through 23.
- SNPP: 2024-07-24 (14,621 rows), 2024-07-16 (15,643 rows), 2024-07-29 (17,802 rows).
  2024-07-24: rows fall in 6 UTC hours, from 00 through 05.
  2024-07-16: rows fall in 7 UTC hours, from 17 through 23.
  2024-07-29: rows fall in 9 UTC hours, from 15 through 23.

## Limitations

- MODIS and VIIRS have different spatial resolutions and detection characteristics. Row counts are not a comparison of sensitivity.
- Repeat detections are not necessarily unique fires. Exact duplicate rows and repeated location-time keys are retained.
- A date with zero delivered rows, and a date whose source file is missing, are not zero fire detections.
- MODIS confidence is an integer from 0 through 100. VIIRS confidence is the flag l, n, or h. The scales are not interchangeable.
- Processing-level provenance stays unresolved. The ZIP name, the fire_archive prefix, and the version field are not treated as a processing stream.
- One month cannot establish a globally valid harmonization factor. No coefficient is calculated.
- Spatial proximity is not assessed here and cannot, by itself, prove that two observations are the same fire.
- FRP is the stored fire radiative power value. It is not fire size and it is not total fire energy.
