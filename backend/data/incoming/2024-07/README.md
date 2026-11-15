# Incoming FIRMS archives for July 2024

Place exactly four unmodified ZIP archives in this folder, one for each sensor family. The ingestion tool identifies the sensor from the FIRMS product code in the filename. It does not infer near-real-time or standard processing from `fire_nrt`, `fire_archive`, or the version field.

| Place this download here | Product code in the ZIP name | Sensor directory after ingestion |
| --- | --- | --- |
| MODIS Collection 6.1, Terra and Aqua together | `M-C61` | `backend/data/raw/monthly_2024_07/modis/` |
| VIIRS 375 m Suomi-NPP | `SV-C2` | `backend/data/raw/monthly_2024_07/viirs_snpp/` |
| VIIRS 375 m NOAA-20 (JPSS-1) | `J1V-C2` | `backend/data/raw/monthly_2024_07/viirs_noaa20/` |
| VIIRS 375 m NOAA-21 (JPSS-2) | `J2V-C2` | `backend/data/raw/monthly_2024_07/viirs_noaa21/` |

A FIRMS download name looks like `DL_FIRE_M-C61_123456.zip`. The request number at the end may differ. Two ZIPs for the same product code are rejected instead of choosing one. A ZIP whose name contains more than one product code is rejected.

Leave the ZIP bytes unchanged. Do not unzip them by hand into this folder. Do not put the existing 7 July 2024 sample files here.

These ZIP files are gitignored.
