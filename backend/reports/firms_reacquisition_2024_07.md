# FIRMS S-NPP re-acquisition, 16 and 25 July 2024

The local file was not reproduced. No second CSV was downloaded, so record differences were not calculated.

The archive tool accepts a new VIIRS S-NPP 375 m order for both dates and sends a ZIP by email. That order was not submitted. The area API documents a historical date, but it requires a MAP_KEY, and no key is configured. No second CSV was saved.

## Product

Local file: `fire_archive_SV-C2_850322.csv`. SHA-256 `bc5ff311c2df9113baf4eedaf4247d55954e8f4fa2ca052f940a943365314f21`. Rows in the file: 1635020.
Download readme short name: `VNP14IMGTML`. Area API source, not requested: `VIIRS_SNPP_SP`.
The filename, the readme short name, and the API source are related FIRMS labels for S-NPP standard processing. This check does not show that an API response is the same file.

## Local rows

A date with no row is absent from this file. It is not a count of zero detections. The requested area of interest was not stored.

| UTC date | Rows in this file | Acquisition time | Absent from this file |
| --- | --- | --- | --- |
| 2024-07-16 | 15643 | 1742–2316 UTC | false |
| 2024-07-25 | 0 | none | true |

Observed latitude -82.16354 to 71.72057. Observed longitude -178.94585 to 179.58748. These are ranges of stored points, not the order form's area.

## Archive download

Page: https://firms.modaps.eosdis.nasa.gov/download/
VIIRS S-NPP 375 m coverage on that page: 20 January 2012 - 2 November 2026. Both target dates fall inside it.
Authentication is Earthdata Login or an emailed code. The processed order arrives by email. There is no documented URL that returns order 850322.

Manual steps:

1. Open https://firms.modaps.eosdis.nasa.gov/download/.
2. Authenticate with Earthdata Login or request the emailed code. The public page does not show the order form until that login succeeds.
3. Request VIIRS S-NPP 375 m, the selection whose readme filename is DL_FIRE_SV-C2 and whose standard CSV is fire_archive_SV-C2. The published coverage line is VIIRS S-NPP 375m: 20 January 2012 - 2 November 2026.
4. Choose CSV. Submit one order for 2024-07-16 and a separate order for 2024-07-25.
5. Use the same area of interest as order 850322. That area was not stored with the local ZIP. A different box is a different request, not a reproduction.
6. Wait for the email. Save the returned ZIP, unchanged, in backend/data/verification/. Do not replace DL_FIRE_SV-C2_850322.zip or fire_archive_SV-C2_850322.csv.
7. The new request id will differ from 850322. Keep the provider filename.
8. Compare that new CSV with the local file using python -m fire_data.reacquire --independent <new.csv>. Until that file exists, no record comparison is available.

## Area API

The area page documents `/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]/[DATE]` and says the date form returns that date through the following day range. `DAY_RANGE` is 1 to 5. `VIIRS_SNPP_SP` is labeled standard processing. A MAP_KEY is required.

Credential present: false. The value was not recorded.
world is the documented global extent on the area page. It is not the recovered area of order 850322.
An availability URL without a key returns HTTP 401. The availability window for these two dates was therefore not read, and the API was not called.

## FIRMS missing-data table

Retrieved 2026-11-15T04:20:13Z from https://firms.modaps.eosdis.nasa.gov/api/missing_data/?action=fetch_data.
The table has 169 rows. Suomi NPP standard dates marked missing span 2012-03-25 through 2026-07-16.
July 2024 Suomi NPP standard dates in that column: 2024-07-28, 2024-07-27, 2024-07-26, 2024-07-25, 2024-07-15, 2024-07-14, 2024-07-13, 2024-07-12, 2024-07-11, 2024-07-10.
16 July 2024 is not in the column. 25 July 2024 is in the column.
A listed day is not a fire count of zero. An unlisted day is not a complete archive and is not the CSV from order 850322.

## Comparison

Not performed. There is no independent CSV.
Exact matches, missing records, additional records, and changed values are not estimated.

## What this does not prove

- The local absence of rows on 25 July is not zero fire detections.
- A missing CMR granule is not evidence in this note.
- No harmonization coefficient is implied.
- Matching or missing rows, once a second file exists, are archive records rather than unique fires.

## Next step

Submit the two manual archive orders only after the original area of interest is known. Save them beside the current files and compare the tables. Do not fill 25 July with zeros, and do not treat either day as harmonized.
