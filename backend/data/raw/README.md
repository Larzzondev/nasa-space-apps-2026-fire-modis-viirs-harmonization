# Local FIRMS archives

The CSV extracts that feed `fire_data` stay on disk and are not part of the public Git history.

The current code looks for these paths, which match one local download:

- `modis/fire_archive_M-C61_850118.csv`
- `viirs_noaa20/fire_archive_J1V-C2_850119.csv`
- `viirs_noaa21/fire_archive_J2V-C2_850120.csv`
- `viirs_snpp/fire_archive_SV-C2_850121.csv`

A new FIRMS download uses a different request id in the filename. Place the new file at the path named in `fire_data/contract.py`, or update that contract before running the tools.

Do not commit the CSV files. Do not commit a NASA FIRMS `MAP_KEY`, a Cesium ion token, or any other credential. Acquisition steps are in the root `README.md`.
