# Milestone 9 summary

Within-sensor spatial-temporal structure of the July 2024 FIRMS archives. Five satellites, 7,985,467 delivered rows. Neighbors and DBSCAN components are not confirmed fires. `same_fire` is `not_assessed`.

## What was measured

- Exact extra copies on the loaded analysis fields, without removing any row.
- Repeated coordinates at the same acquisition minute, and repeated coordinates at different minutes.
- The nearest other row on the same UTC date, at any distance.
- Neighborhood counts at 375 m, 1 km, 2 km, and 5 km, and at 0, 30, and 180 minutes.
- The closest row on the next UTC date, capped at 5 km, with empty next dates left null.
- FRP, brightness, scan, track, day/night, and native confidence for all rows, for rows with a 1 km / 30 min neighbor, and for rows without one.
- Spatial occupancy on all delivered dates and on dates when all five sensors have rows.
- DBSCAN noise share for seven settings on every delivered row, plus a 27-cell factorial on one representative date per sensor.

## What was not done

- No harmonization coefficient.
- No XGBoost model.
- No repaired S-NPP dates and no zeros substituted for dates without rows.
- No cluster was named as a physical fire.

## Where the numbers are

- `backend/reports/within_sensor_analysis_2024_07.md`
- `backend/reports/within_sensor_analysis_2024_07.json`
- `backend/reports/figures/within_sensor_2024_07/`

Reproduce from `backend` with `.venv\Scripts\python -m fire_data.within_sensor_analysis`.
