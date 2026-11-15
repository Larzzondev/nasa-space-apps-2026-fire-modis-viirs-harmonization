# Experiment D: spatial resolution and aggregation candidates

Question: how large are the stored MODIS and VIIRS sizes in this month, how uneven is the geographic sample, and which aggregations are only candidates?

scan and track are stored lengths in kilometres. Their product treats those lengths as the sides of a rectangle. The archive does not include the pixel polygon, the scan angle, or the ground orientation. Adjacent-scan overlap and Earth curvature inside the pixel are not corrected. scan multiplied by track is a stored-size proxy, not an exact physical pixel area.

The product of the medians is reported beside the median of the products. Those two numbers are not treated as the same quantity. Search radii are not footprints. Equal-degree cells are not equal-area cells. No H3 resolution is selected. A cell is not an analytical cluster and not a fire.

Cell area uses the spherical zone on a sphere of radius 6371008.8 m, through the existing `cell_area_km2` calculation. A count in a cell is a count of archived rows.

## Stored scan, track, and their product

| Satellite | Scan p50 (km) | Track p50 (km) | Median of products (km²) | Product of medians (km²) | Product p90 (km²) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Terra | 1.200 | 1.100 | 1.320 | 1.320 | 4.320 |
| Aqua | 1.300 | 1.100 | 1.430 | 1.430 | 4.480 |
| S-NPP | 0.440 | 0.440 | 0.198 | 0.194 | 0.340 |
| NOAA-20 | 0.440 | 0.440 | 0.198 | 0.194 | 0.340 |
| NOAA-21 | 0.440 | 0.450 | 0.199 | 0.198 | 0.348 |

The growth table in `results.json` bins each satellite's own scan distribution. Median `scan × track` is larger in the upper scan bins. The file contains no scan angle, so none is inferred.

## One-degree and two-degree cells

| Satellite | 1° occupied | 1° count cell equals rate cell | 1° row share at |lat| ≥ 60° | 1° area share at |lat| ≥ 60° | 2° occupied |
| --- | ---: | --- | ---: | ---: | ---: |
| Terra | 5424 | True | 0.145 | 0.134 | 2364 |
| Aqua | 5880 | False | 0.052 | 0.134 | 2489 |
| S-NPP | 7934 | True | 0.072 | 0.134 | 3032 |
| NOAA-20 | 8777 | True | 0.080 | 0.134 | 3226 |
| NOAA-21 | 8669 | True | 0.081 | 0.134 | 3199 |

When the cell with the most rows is not the cell with the highest rows per 1,000 km², an equal-degree reading and an equal-area reading do not point at the same place. High-latitude bands cover less ground. A raw count there is not a density.

The published monthly 1° occupancy is cited in the JSON. This run rebuilds the grids with `count_grid` so the spherical area can be attached. A difference from the published floor count, if one appears, is recorded on the satellite and is not silently replaced.

## Candidate aggregations

None of these is selected:

- equal-degree 1° cells
- equal-degree 2° cells
- the same cells converted with the spherical zone area
- H3 cells, unselected

The h3 package is not installed. No average cell area was read from the library, and none was invented.

An aggregation cell is not one of Experiment A's components.

## Limits

- `scan × track` is not an exact physical pixel area.
- A 1 km search radius is not a MODIS pixel, and a 375 m radius is not a VIIRS pixel.
- Summing satellites would count the same ground more than once when several sensors report it. Densities stay per satellite.
- S-NPP dates with no rows are absent from that satellite's grid. They were not filled.
- No harmonization coefficient was calculated. XGBoost was not trained.
