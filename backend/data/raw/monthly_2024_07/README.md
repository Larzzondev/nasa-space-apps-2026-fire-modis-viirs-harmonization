# July 2024 monthly extracts

This directory is the destination for CSVs extracted from the four ZIP archives in `backend/data/incoming/2024-07/`. It is empty until ingestion runs.

| Subdirectory | Sensor |
| --- | --- |
| `modis/` | MODIS Collection 6.1, Terra and Aqua |
| `viirs_snpp/` | VIIRS Suomi-NPP |
| `viirs_noaa20/` | VIIRS NOAA-20 |
| `viirs_noaa21/` | VIIRS NOAA-21 |

The 7 July 2024 sample remains in `backend/data/raw/modis/`, `viirs_snpp/`, `viirs_noaa20/`, and `viirs_noaa21/`. Ingestion does not write into those directories.

Extracted CSVs are gitignored. A date that does not appear in a CSV is absent from that file. It is not a measured count of zero detections.
