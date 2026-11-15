# Milestone 9 execution log

Auditable decisions for the within-sensor analysis. This is not a private reasoning trace.

## Initial approach

Inspect the July candidate-pair and nearest-neighbor modules before any full scan. Reuse `ObservationTable`, the ECEF `cKDTree`, and the great-circle chord conversion. Keep Terra and Aqua separate. Keep native confidence. Leave `same_fire` as `not_assessed`. Do not calculate a harmonization coefficient and do not train XGBoost.

The planned products were duplicate and same-coordinate inventories, within-sensor nearest neighbors, neighborhood density at several radii and time windows, temporally separated detections, and DBSCAN on spatial-temporal partitions with a sensitivity grid.

## Problems encountered

A single in-memory pair list for a month is too large. The bounded probe on NOAA-20 2024-07-25 (127,817 rows) produced 6,065,137 directed pairs inside 5 km, including the zero-distance diagonal, in 0.146 seconds and 145,563,288 bytes.

The same probe showed a same-day nearest-neighbor median of 379.64 m and a median time gap of 0.0 minutes. About 7.9% of those nearest neighbors were beyond 5 km, so a 5 km graph alone would have hidden that tail.

S-NPP has dates with no delivered rows. Those dates had to stay out of denominators. DBSCAN cluster counts on UTC-date partitions are not additive, because a component can touch the midnight margin.

The first full run aborted on S-NPP. `query(k=2)` returned the same row in the second slot for at least one detection, which happens when another row has the same coordinate and the tree lists that other row first. No partial sensor result was written. The nearest-other rule was corrected and the full run was repeated. Rows were not dropped.

After that run, the same-coordinate inventory was checked against a direct pass over the NOAA-20 CSV. The text key and the float64 key both had 1 extra NOAA-20 row, while the report had 2. The grouping had failed to start a new epoch when a coordinate's first minute matched the previous coordinate's last minute, so some different-minute coordinates were counted as same-minute copies. Neighborhood, nearest-neighbor, and DBSCAN results do not use that grouping. Only the coordinate inventory was recomputed after the fix.

scikit-learn is not installed. A Euclidean DBSCAN would also be the wrong neighborhood, because the relation is a spatial radius combined with a time window.

## Commands or experiments cancelled and why

- The temporary probe script `_probe_nn.py` was deleted after the timing and degree sample were recorded. It was not a deliverable and it did not change the CSVs.
- The first `python -m fire_data.within_sensor_analysis` process aborted on S-NPP and was then stopped. It had written no report. The corrected run is the one recorded below.
- A month-global pair graph was not built. The busiest sampled date already held about 146 MB of 5 km pairs. Stacking that graph across the month would have been a memory spike without labeling any additional rows.
- The probe was allowed to finish. The corrected full run was allowed to finish. The only process stopped was the already-aborted first full run.

## Parameter changes and why

| Item | Original | Changed to | Reason |
| --- | --- | --- | --- |
| Distance index | Candidate-pair tiles at 20° | One UTC date, optional 180-minute midnight margin | The probe showed a date of 127,817 rows builds a tree in 0.02 s and a 5 km pair list in 0.15 s. A date partition covers every row. |
| Unrestricted nearest neighbor | Take it from the 5 km pair list | Separate nearest-other query on the same date | 7.9% of the probe's nearest neighbors were outside 5 km. The cap would have censored them. |
| Nearest-other query | Assume `k=2` column 0 is the row and column 1 is the neighbor | Keep the nearest returned index that is not the row. Widen `k` only for rows whose first hits are all themselves | The first full S-NPP pass aborted because column 1 was the row itself when a coincident row occupied column 0. |
| DBSCAN grid | Full factorial on every date | Seven one-factor settings on every delivered row, and the 3×3×3 factorial on the representative date | The seven settings label every row. The factorial answers the interaction question without a second full-month graph per cell. Coverage of the primary question was not reduced. |
| Representative date | Unspecified | Earliest date closest to the median row count among dates with rows | A fixed rule, chosen before looking at cluster output. |
| Empty S-NPP dates | Could have been stored as zero | `rows: null`, `zero_detections: false` | A missing delivered date is not zero fire activity. |
| Same-coordinate epochs | A minute change was measured against the previous row, including the previous coordinate | The first row of each coordinate starts a new epoch | A direct NOAA-20 recount found 1 text extra and 1 float extra, not the 2 extras in the first report. The inventory was recomputed. Other results were left as calculated. |

## Alternative approaches evaluated

- scikit-learn DBSCAN: rejected. The package is not a project dependency, and the neighborhood is not a single Euclidean ball in scaled latitude, longitude, and time.
- H3 aggregation: not used. Earlier reports left it unused, and this milestone does not ask for a grid index.
- Dropping the 5 km radius after the probe mean degree of about 45: rejected. The date partition made 5 km affordable, so dropping it would have reduced coverage to save time that the probe showed was unnecessary.
- Treating S-NPP empty dates as zeros in the five-sensor spatial comparison: rejected. A separate common-date profile uses only dates on which all five sensors have rows.

## Final successful approach

Load the four July CSVs through the existing reader. Check each sensor's row count against the ingestion manifest before interpreting anything. For each satellite and each UTC date with rows, compute the unrestricted same-day nearest neighbor, the 5 km pair list, the windowed neighborhood counts, the next-date neighbor when the next date has rows, and the DBSCAN labels. Write JSON, Markdown, and figures from that report.

Load time: 176.2 s. Analysis time: 661.2 s. Peak Python allocations traced: 1,900,924,045 bytes.

Internal consistency checks all passed.

After the coordinate-inventory correction, `.venv\Scripts\python -m pytest -q --tb=line` from `backend` reported 112 passed in 44.28s.

## Remaining uncertainties

- NOAA-20 and NOAA-21 processing level is still unresolved. The version column was not used as a processing stream.
- DBSCAN components that cross midnight are split by the date partition. Owned-row noise shares are complete. Partition cluster counts are not a global inventory.
- Same-coordinate counts use float64 bits. On these July files they matched a direct text-key recount after the epoch-boundary fix (NOAA-20 extra 1, NOAA-21 extra 4, others 0). A future file could still collide if two different coordinate strings parse to one float. The full-line scan remains the authority for exact CSV duplicates, which were 0.
- A next-date neighbor farther than 5 km is uncounted. The cap is stated. It is not evidence that the next date has no nearby land feature.
- Neighborhoods and components are not validated against burned area, imagery, or any fire inventory.
