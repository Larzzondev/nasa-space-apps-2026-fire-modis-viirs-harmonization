# Spatial-temporal candidate pairs, July 2024

This is an exploratory proximity analysis of archived MODIS and VIIRS detections. A candidate pair is not a confirmed common fire, and the pair count is not a fire count.

## Method

Each sensor is kept separate. MODIS in a cross-sensor pair means Terra and Aqua together, with each row keeping its own satellite name. Terra versus Aqua is a separate pair.

Coordinates are converted to Earth-centered Cartesian positions on a sphere of radius 6371008.8 m, the same sphere used by the one-day proximity count. A `cKDTree` returns neighbors inside the chord length that corresponds to a 5 km great circle. The reported separation is the great-circle length recovered from that chord. The search is partitioned into 20-degree tiles so the full distance matrix is not built. Pairs are then kept for 375 m, 750 m, 1 km, 2 km, and 5 km, and for 5, 15, 30, and 60 minutes.

The date of the reference sensor owns the pair. The other sensor may fall up to 60 minutes earlier or later, including across UTC midnight. One detection can enter many pairs. Thresholds are search radii, not sensor footprints. VIIRS I-band pixels are about 375 m at nadir and grow with scan angle. MODIS pixels are about 1 km at nadir. Those sizes are not applied as a match rule.

A date is compared only when both sides have at least one row that UTC date. A date with no rows is excluded. It is not stored as zero candidate pairs and it is not a measurement of zero fire activity. S-NPP dates that do contain rows are compared only for those rows. The coverage investigation found incomplete S-NPP delivery on 16, 24, and 29 July; this analysis does not fill those intervals.

NOAA-20 and NOAA-21 processing level is unresolved. The local filenames use fire_archive, while the FIRMS download readme says standard-quality data are not yet available for those sensors. The version column is not used as a processing stream.

No MODIS-to-VIIRS scaling factor is calculated. XGBoost is not trained. H3 is not applied. `same_fire` remains `not_assessed`.

## Sensors

| Satellite | Rows | Absent UTC dates | Scan median (km) | FRP median (MW) |
| --- | --- | --- | --- | --- |
| Terra | 195316 | none | 1.200 | 19.100 |
| Aqua | 481320 | none | 1.300 | 21.600 |
| S-NPP | 1635020 | 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28 | 0.440 | 5.060 |
| NOAA-20 | 2902597 | none | 0.440 | 5.140 |
| NOAA-21 | 2771214 | none | 0.440 | 6.090 |

MODIS confidence remains the stored 0–100 value. VIIRS confidence remains `l`, `n`, or `h`. Those scales are not converted into one score.

Geographic concentration in the JSON is the 1-degree cells with the most detection rows. Equal-degree cells are not equal-area cells. The row count is not a fire count.

## Candidate pairs at 1 km and 30 minutes

| Pair | Compared dates | Excluded dates | Candidate pairs | Reference rows with a candidate | Other rows on the date with a candidate |
| --- | --- | --- | --- | --- | --- |
| Terra and Aqua | 31 | 0 | 5976 | 3987 | 4172 |
| MODIS (Terra and Aqua) and S-NPP | 21 | 10 | 293942 | 76889 | 192821 |
| MODIS (Terra and Aqua) and NOAA-20 | 31 | 0 | 565132 | 159844 | 371697 |
| MODIS (Terra and Aqua) and NOAA-21 | 31 | 0 | 548204 | 151724 | 356745 |
| S-NPP and NOAA-20 | 21 | 10 | 5138443 | 1093114 | 1081750 |
| S-NPP and NOAA-21 | 21 | 10 | 4705012 | 1044632 | 958416 |
| NOAA-20 and NOAA-21 | 31 | 0 | 0 | 0 | 0 |

## Patterns

Terra and Aqua: 5976 candidate pairs at 1 km and 30 minutes across 31 compared dates, and 41362 at 5 km and 60 minutes. 3987 reference rows on compared dates have at least one candidate, out of 195316 reference rows. Among pairs inside 5 km and 60 minutes, the median separation falls in 2250–2500 m and the median time difference falls in 17–18 minutes. Excluded dates: none.

MODIS (Terra and Aqua) and S-NPP: 293942 candidate pairs at 1 km and 30 minutes across 21 compared dates, and 2995557 at 5 km and 60 minutes. 76889 reference rows on compared dates have at least one candidate, out of 438825 reference rows. Among pairs inside 5 km and 60 minutes, the median separation falls in 2250–2500 m and the median time difference falls in 28–29 minutes. Excluded dates: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28.

MODIS (Terra and Aqua) and NOAA-20: 565132 candidate pairs at 1 km and 30 minutes across 31 compared dates, and 5161059 at 5 km and 60 minutes. 159844 reference rows on compared dates have at least one candidate, out of 676636 reference rows. Among pairs inside 5 km and 60 minutes, the median separation falls in 2250–2500 m and the median time difference falls in 28–29 minutes. Excluded dates: none.

MODIS (Terra and Aqua) and NOAA-21: 548204 candidate pairs at 1 km and 30 minutes across 31 compared dates, and 5248283 at 5 km and 60 minutes. 151724 reference rows on compared dates have at least one candidate, out of 676636 reference rows. Among pairs inside 5 km and 60 minutes, the median separation falls in 2250–2500 m and the median time difference falls in 28–29 minutes. Excluded dates: none.

S-NPP and NOAA-20: 5138443 candidate pairs at 1 km and 30 minutes across 21 compared dates, and 27216791 at 5 km and 60 minutes. 1093114 reference rows on compared dates have at least one candidate, out of 1635020 reference rows. Among pairs inside 5 km and 60 minutes, the median separation falls in 2250–2500 m and the median time difference falls in 24–25 minutes. Excluded dates: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28.

S-NPP and NOAA-21: 4705012 candidate pairs at 1 km and 30 minutes across 21 compared dates, and 24272835 at 5 km and 60 minutes. 1044632 reference rows on compared dates have at least one candidate, out of 1635020 reference rows. Among pairs inside 5 km and 60 minutes, the median separation falls in 2250–2500 m and the median time difference falls in 25–26 minutes. Excluded dates: 2024-07-10, 2024-07-11, 2024-07-12, 2024-07-13, 2024-07-14, 2024-07-15, 2024-07-25, 2024-07-26, 2024-07-27, 2024-07-28.

NOAA-20 and NOAA-21: 0 candidate pairs at 1 km and 30 minutes across 31 compared dates, and 65082849 at 5 km and 60 minutes. 0 reference rows on compared dates have at least one candidate, out of 2902597 reference rows. Among pairs inside 5 km and 60 minutes, the median separation falls in 2250–2500 m and the median time difference falls in 50–51 minutes. Excluded dates: none.

The median separation inside the 5 km window falls in 2250–2500 m for every pair. A 5 km disk contains more ground toward its outer edge, so that shared bin is not evidence of a preferred separation.

NOAA-20 and NOAA-21 have no candidate pairs inside 30 minutes. Inside 5 km and 60 minutes, their median time difference falls in 50–51 minutes. The shorter windows are empty because those acquisitions are farther apart than 30 minutes, not because the rows are far apart on the ground.

Day/night labels on a pair are the stored flags of the two rows. They describe the observations, not a shared fire.

FRP histograms count candidate pairs, so a row in several pairs is counted more than once. FRP is not fire size. Non-positive FRP values are left out of the log histogram and counted separately.

## Performance

Load time: 181.9 s. Match and summary time: 111.3 s. Peak Python allocations traced: 1119952034 bytes. The Windows working-set counter was not returned. The traced allocation peak is the memory figure for this run. Tracing allocations slows the CSV load.

## Reproducibility

From `backend/`, with the July CSVs already extracted:

```bash
.venv\Scripts\python -m fire_data.spatiotemporal_analysis
```

The command reads the four monthly archives, writes this report, and writes the figures under `backend/reports/figures/spatiotemporal_2024_07/`. It does not modify the CSVs.

## Limitations

- A candidate pair does not prove that the two rows observe the same fire.
- Pair counts are not unique fires. One detection can belong to many pairs.
- Raw detection totals are not a measure of which sensor performs better. The sensors differ in pixel size, scan growth, and overpass time.
- Missing S-NPP dates are excluded. They are not zeros.
- Incomplete S-NPP intervals on 16, 24, and 29 July are not repaired.
- NOAA-20 and NOAA-21 processing level is unresolved. The local filenames use fire_archive, while the FIRMS download readme says standard-quality data are not yet available for those sensors. The version column is not used as a processing stream.
- No global scaling factor, XGBoost model, or H3 aggregation is produced.
