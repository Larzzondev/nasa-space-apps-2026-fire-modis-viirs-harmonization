/**
 * Dashboard contracts for Fire Activity Harmonization.
 *
 * Fields marked PROVISIONAL are application placeholders.
 * They are not a verified mapping of MODIS or VIIRS CSV columns.
 * Do not parse a NASA file into these types until that schema is confirmed.
 */

export interface AreaOfInterest {
  id: string
  name: string
  /** PROVISIONAL WGS84 extent in degrees. Not a fire perimeter. */
  bounds: {
    /** PROVISIONAL western longitude. */
    west: number
    /** PROVISIONAL southern latitude. */
    south: number
    /** PROVISIONAL eastern longitude. */
    east: number
    /** PROVISIONAL northern latitude. */
    north: number
  }
}

export interface DateRange {
  /** PROVISIONAL inclusive start, ISO calendar date YYYY-MM-DD. */
  start: string
  /** PROVISIONAL inclusive end, ISO calendar date YYYY-MM-DD. */
  end: string
}

export interface FireHotspot {
  id: string
  /** PROVISIONAL. Not confirmed as a NASA CSV column name. */
  latitude: number
  /** PROVISIONAL. Not confirmed as a NASA CSV column name. */
  longitude: number
  /** PROVISIONAL ISO calendar date YYYY-MM-DD. */
  observedOn: string
  /** PROVISIONAL display family. Not a raw satellite identifier. */
  sensorFamily: 'MODIS' | 'VIIRS' | 'UNSPECIFIED'
}

export interface DashboardFilters {
  areaOfInterestId: string | null
  dateRange: DateRange
}
