# Milestone 9 validation

Checks below are computed from the written report. A failed check is a failed milestone, not a scientific finding.

| Check | Passed | Detail |
| --- | --- | --- |
| same_fire | true | not_assessed |
| no_harmonization_coefficient | true | null |
| xgboost_not_trained | true | false |
| Terra_rows_removed | true | 0 |
| Terra_same_fire | true | not_assessed |
| Terra_daily_sums_to_rows | true | 195316 vs 195316 |
| Terra_isolation_partition | true | 144220+51096 |
| Terra_dbscan_375_30_4 | true | 195316 vs 195316 |
| Terra_dbscan_1000_30_4 | true | 195316 vs 195316 |
| Terra_dbscan_2000_30_4 | true | 195316 vs 195316 |
| Terra_dbscan_1000_0_4 | true | 195316 vs 195316 |
| Terra_dbscan_1000_180_4 | true | 195316 vs 195316 |
| Terra_dbscan_1000_30_2 | true | 195316 vs 195316 |
| Terra_dbscan_1000_30_8 | true | 195316 vs 195316 |
| Terra_absent_dates_are_null | true | none |
| Aqua_rows_removed | true | 0 |
| Aqua_same_fire | true | not_assessed |
| Aqua_daily_sums_to_rows | true | 481320 vs 481320 |
| Aqua_isolation_partition | true | 362386+118934 |
| Aqua_dbscan_375_30_4 | true | 481320 vs 481320 |
| Aqua_dbscan_1000_30_4 | true | 481320 vs 481320 |
| Aqua_dbscan_2000_30_4 | true | 481320 vs 481320 |
| Aqua_dbscan_1000_0_4 | true | 481320 vs 481320 |
| Aqua_dbscan_1000_180_4 | true | 481320 vs 481320 |
| Aqua_dbscan_1000_30_2 | true | 481320 vs 481320 |
| Aqua_dbscan_1000_30_8 | true | 481320 vs 481320 |
| Aqua_absent_dates_are_null | true | none |
| SNPP_rows_removed | true | 0 |
| SNPP_same_fire | true | not_assessed |
| SNPP_daily_sums_to_rows | true | 1635020 vs 1635020 |
| SNPP_isolation_partition | true | 304593+1330427 |
| SNPP_dbscan_375_30_4 | true | 1635020 vs 1635020 |
| SNPP_dbscan_1000_30_4 | true | 1635020 vs 1635020 |
| SNPP_dbscan_2000_30_4 | true | 1635020 vs 1635020 |
| SNPP_dbscan_1000_0_4 | true | 1635020 vs 1635020 |
| SNPP_dbscan_1000_180_4 | true | 1635020 vs 1635020 |
| SNPP_dbscan_1000_30_2 | true | 1635020 vs 1635020 |
| SNPP_dbscan_1000_30_8 | true | 1635020 vs 1635020 |
| SNPP_absent_dates_are_null | true | 2024-07-10,2024-07-11,2024-07-12,2024-07-13,2024-07-14,2024-07-15,2024-07-25,2024-07-26,2024-07-27,2024-07-28 |
| SNPP_matches_manifest | true | 1635020 |
| N20_rows_removed | true | 0 |
| N20_same_fire | true | not_assessed |
| N20_daily_sums_to_rows | true | 2902597 vs 2902597 |
| N20_isolation_partition | true | 585345+2317252 |
| N20_dbscan_375_30_4 | true | 2902597 vs 2902597 |
| N20_dbscan_1000_30_4 | true | 2902597 vs 2902597 |
| N20_dbscan_2000_30_4 | true | 2902597 vs 2902597 |
| N20_dbscan_1000_0_4 | true | 2902597 vs 2902597 |
| N20_dbscan_1000_180_4 | true | 2902597 vs 2902597 |
| N20_dbscan_1000_30_2 | true | 2902597 vs 2902597 |
| N20_dbscan_1000_30_8 | true | 2902597 vs 2902597 |
| N20_absent_dates_are_null | true | none |
| N20_matches_manifest | true | 2902597 |
| N21_rows_removed | true | 0 |
| N21_same_fire | true | not_assessed |
| N21_daily_sums_to_rows | true | 2771214 vs 2771214 |
| N21_isolation_partition | true | 580798+2190416 |
| N21_dbscan_375_30_4 | true | 2771214 vs 2771214 |
| N21_dbscan_1000_30_4 | true | 2771214 vs 2771214 |
| N21_dbscan_2000_30_4 | true | 2771214 vs 2771214 |
| N21_dbscan_1000_0_4 | true | 2771214 vs 2771214 |
| N21_dbscan_1000_180_4 | true | 2771214 vs 2771214 |
| N21_dbscan_1000_30_2 | true | 2771214 vs 2771214 |
| N21_dbscan_1000_30_8 | true | 2771214 vs 2771214 |
| N21_absent_dates_are_null | true | none |
| N21_matches_manifest | true | 2771214 |
| modis_matches_manifest | true | 676636 |
| snpp_known_empty_dates_stay_null | true | 10 |

## Scientific guards

- `same_fire` is `not_assessed` on the report and on every sensor.
- `harmonization_coefficient` is null. `xgboost_trained` is false.
- DBSCAN summaries set `clusters_are_confirmed_fires` to false.
- S-NPP dates 10–15 and 25–28 July have null row counts.
- Daily delivered rows sum to the manifest totals. No row was removed.
- Isolated rows plus neighborhood rows equal the sensor total at 1 km and 30 minutes.
- Each full-coverage DBSCAN setting labels every delivered row as noise or clustered.
- After the epoch-boundary fix, same-coordinate-and-time extras were recomputed and matched a direct text-key pass: Terra 0, Aqua 0, S-NPP 0, NOAA-20 1, NOAA-21 4. Those are the published counts. No row was removed.

## Tests

Command, from `backend`:

```
.venv\Scripts\python -m pytest -q --tb=line
```

Result: 112 passed in 44.28s. Exit code 0.

## Not claimed

Passing these checks does not mean a cluster is a fire. It means the counts are internally consistent with the stated definitions and the archived rows.
