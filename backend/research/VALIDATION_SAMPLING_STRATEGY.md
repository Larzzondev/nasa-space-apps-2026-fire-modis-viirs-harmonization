# Validation sampling strategy

The dates below were fixed from the calendar and from the coverage lines in `TEMPORAL_OVERLAP_TIMELINE.md`. They were not chosen by counting detections. No file for these dates was downloaded. July 2024 is not in the training period, the calibration period, or the validation period. `same_fire` remains `not_assessed`. No harmonization coefficient is calculated, and XGBoost is not trained.

A date enters a split only after a future order stores an explicit processing stream for every required platform. Until then the dates are a rule, not a dataset.

## Why these periods are independent

Training, calibration, and validation use different UTC years inside the conservative five-platform FIRMS window, 17 January 2024 through 13:00 UTC on 2 November 2026. No UTC day is in two splits. A coefficient, if one were ever fit, would be fit on the calibration period and judged on the validation period. The training period is reserved for describing distributions and for choosing analysis settings. It is not a second look at the validation year.

July 2024 is a locked descriptive month. It already has within-sensor, candidate-pair, nearest-neighbor, and experiment results. Putting it into any split would reuse that month as if it were new. The whole UTC month is excluded, including dates that are not on the 15th.

The five-platform window is also the MODIS drift-impact window. LDOPE reports significant sampling changes in late 2024 and says the fire-product effect is under investigation. These three splits can support a drift-era comparison among the five platforms. They cannot be pooled with 2003, 2007, or 2011 and treated as one MODIS diurnal regime. Those earlier years are a continuity sample with their own label.

## The calendar rule

Take the 15th UTC day of January, February, March, June, July, August, September, and December.

Those months are the high and low seasons of the regions below. The day of the month is constant so the rule can be rerun without looking at a fire count. A global order for that UTC date keeps both day and night. Regional windows are applied after the files exist. They are not separate orders and they are not a reason to drop the night flag.

If a date falls in an interval a retrieved NASA alert marks unavailable for a required platform, drop it and record the alert. The only replacement is 16 days later, or the last day of the month when that month has no such day. The replacement is used only when the original date is inside a stated outage. If the replacement is also inside a stated outage, the stratum is missing. It is not filled by searching for a day with more detections.

## Regions

The boxes are design windows for later stratification. They are not a claim that a fire season has been measured, and they are not a land-cover product.

| Window | Climatic role | Latitude | Longitude | Month used as the high-season marker | Month used as the low-season marker |
| --- | --- | --- | --- | --- | --- |
| Southern African savanna | Tropical savanna, Southern Hemisphere dry season | 25°S–10°S | 15°E–40°E | September | February |
| Southern Amazon | Tropical forest and savanna transition | 20°S–5°S | 70°W–50°W | September | March |
| Boreal North America | Boreal forest | 50°N–65°N | 120°W–90°W | July | January |
| Mediterranean Basin | Dry summer, wet winter | 32°N–44°N | 10°W–20°E | August | January |
| Northern Australia | Southern Hemisphere monsoonal savanna | 22°S–12°S | 125°E–145°E | December | June |
| Mainland Southeast Asia | Tropical dry-season burning | 10°N–22°N | 95°E–110°E | March | September |
| Northern Eurasian high latitude | Night geometry and a low climatological fire season | 65°N–75°N | 20°E–60°E | March is the geometry sample, not a high-fire month | March |

High-season and low-season labels follow the climatological calendar of the region. They are not a ranking of these dates by archived counts. Several windows share a day. September is a high-season marker in southern Africa and the southern Amazon and a low-season marker in mainland Southeast Asia. That is intentional: one global acquisition serves more than one climate.

Day and night are the stored `daynight` values `D` and `N` on that full UTC date. The FIRMS VIIRS page gives S-NPP nominal equator crossings of 1:30 pm and 1:30 am, and it places NOAA-21 about 50 minutes ahead of NOAA-20 with S-NPP between them. A global date therefore contains daytime and nighttime acquisitions for these orbits when the sensors are operating. A regional window can still miss one overpass. The miss stays a miss. Rows are not borrowed from the next date.

## Five-platform splits

Required platforms: Terra, Aqua, S-NPP, NOAA-20, and NOAA-21, each from one named stream. NOAA-21's conservative FIRMS start is 17 January 2024, so 15 January 2024 is outside the window. 15 December 2026 is after new S-NPP FIRMS data cease at 13:00 UTC on 2 November 2026, so it is outside the window. 15 July 2024 is inside the locked month.

### Calibration period

2024, excluding July and excluding 15 January.

| UTC date | Role on the calendar |
| --- | --- |
| 2024-02-15 | Southern African low season; boreal winter |
| 2024-03-15 | Southeast Asian high season; Amazon low season; high-latitude geometry |
| 2024-06-15 | Northern Australian low season |
| 2024-08-15 | Mediterranean high season |
| 2024-09-15 | Southern African and southern Amazon high season; Southeast Asian low season |
| 2024-12-15 | Northern Australian high season |

Six dates. This is the only period from which a future coefficient would be allowed to learn. This milestone does not fit one.

### Training period

All eight calendar dates in 2025.

| UTC date |
| --- |
| 2025-01-15 |
| 2025-02-15 |
| 2025-03-15 |
| 2025-06-15 |
| 2025-07-15 |
| 2025-08-15 |
| 2025-09-15 |
| 2025-12-15 |

15 August 2025 is after the 6 August 2025 NISE AMSR2 input change. The effect of that change on MOD14 and MYD14 is unresolved. The date stays in the training period, and any later write-up of MODIS counts on that date cites the LDOPE note. Training describes the year. It does not tune the coefficient and it does not score it.

### Validation period

2026 dates that fall before the S-NPP FIRMS end.

| UTC date |
| --- |
| 2026-01-15 |
| 2026-02-15 |
| 2026-03-15 |
| 2026-06-15 |
| 2026-07-15 |
| 2026-08-15 |
| 2026-09-15 |

Seven dates. 15 March 2026 is not inside the Terra MODIS gap of 26–27 March 2026 named by LDOPE `TM_MOD_26085`. If a later known-issue note covers one of these seven dates, that date is dropped under the replacement rule above. The validation period is not used to pick a coefficient. It is a partial year because S-NPP production stops. The partial year is kept. It is not extended with NOAA-20 or NOAA-21 alone and then called a five-platform validation.

Twenty-one five-platform dates in total.

## Continuity samples that are not the five-platform splits

These years use the same month-days. They are labeled continuity. They are not mixed into training, calibration, or validation.

| Sample | Years | Dates per year | Required platforms | Why these years |
| --- | --- | --- | --- | --- |
| MODIS pair before VIIRS | 2003, 2007, 2011 | 15 Jan, 15 Feb, 15 Mar, 15 Jun, 15 Jul, 15 Aug, 15 Sep, 15 Dec | Terra and Aqua, Collection 6.1 | After 4 July 2002, before the S-NPP fire record, and before the final maneuver years 2021 and 2022. |
| MODIS plus S-NPP | 2013, 2015, 2017 | the same eight days | Terra, Aqua, S-NPP Collection 2 | After 20 January 2012 and before `VJ114IMG` starts on 2018-01-01. |
| Four platforms before NOAA-21 | 2020 | the same eight days | Terra, Aqua, S-NPP, NOAA-20 | 2020 is inside every retrieved FIRMS NOAA-20 coverage line and before the final IAM/DMU years named by LDOPE. |

15 August 2007 may fall inside the readme's phrase "some missing data from mid August" of 2007. The phrase is not a closed interval. The date stays listed. The delivered file decides whether the day is complete. It is not swapped for a neighboring day because that neighbor has more rows.

The Aqua outage of 16 August–2 September 2020 does not contain 15 August 2020. It does contain dates that are not on this calendar. No continuity date is moved to sit inside that outage.

## Overlapping acquisitions

A sample date is globally ordered so that every required platform that is documented as operating that day is in the same request list. The platforms do not observe at the same minute. The July experiments already showed that a 30-minute cross-sensor window is the wrong description of NOAA-20 versus NOAA-21, whose spatially constrained pairs in that month sat near 50 minutes. The sample preserves acquisition time. It does not collapse the day to one overpass, and it does not declare a pair to be the same fire.

Within one satellite, day and night remain separate strata. They are not averaged into one daily FRP before a split is even populated.

## What would invalidate a date after the order

- The enclosed readme, or the API source code, still does not name one stream for every required platform.
- The stream is not the same value on every platform in that split. NRT and standard are not mixed inside calibration, and they are not mixed between calibration and validation.
- A required platform's file is missing. A header-only file is kept and means no delivered detections. A missing file means the date is out of the five-platform split.
- The date is inside a stated outage for a required platform.
- The collection is not 6.1 for MODIS or not 2 for VIIRS 375 m.

A date removed for one of those reasons is reported as removed. The split's remaining dates are not rebalanced by harvest of high-count days.

## Relationship to the earlier 30-date specification

`backend/reports/data_readiness.md` required a calendar rule, written before download, and refused to invent the 30 dates until a stream existed. This note is that rule. The resulting five-platform count is 21 because the conservative overlap is shorter than three full years and because July 2024 and the dates outside the NOAA-21 and S-NPP bounds are excluded. Twenty-one is the output of the rule. It is not a target chosen to match a detection quota. The 30-date count is not filled by adding days from July 2024 or from after 2 November 2026.

## Sources

Coverage bounds and outage citations are the sources in `HISTORICAL_DATA_STRATEGY.md` and `TEMPORAL_OVERLAP_TIMELINE.md`, retrieved 2026-11-15. The July exclusion also rests on the experiment record at commit `f83e525`, which already used that month. This strategy does not refit those experiments.
