/**
 * Application contracts for the FireLens demo.
 *
 * Archive types describe delivered FIRMS rows transcribed from tracked reports.
 * Demo hotspot types are synthetic records for interaction. They are not a CSV schema.
 */

export interface DateRange {
  /** Inclusive start, ISO calendar date YYYY-MM-DD. */
  start: string
  /** Inclusive end, ISO calendar date YYYY-MM-DD. */
  end: string
}

export type SensorId = 'modis' | 'viirs-n20' | 'viirs-n21' | 'viirs-snpp'

export type ArchiveSatellite = 'Terra' | 'Aqua' | 'NOAA-20' | 'NOAA-21' | 'S-NPP'

export type DayNight = 'D' | 'N'

export type ViirsFlag = 'l' | 'n' | 'h'

export type HotspotSource = 'demo' | 'firms'

export type DeliveryStatus = 'rows_delivered' | 'zero_rows_delivered'

export interface DemoHotspot {
  id: string
  source: HotspotSource
  latitude: number
  longitude: number
  /** ISO calendar date YYYY-MM-DD. */
  date: string
  /** UTC HHMM, matching the FIRMS acq_time shape. Demo values are synthetic. */
  acqTime: string
  sensor: SensorId
  platform: ArchiveSatellite
  dayNight: DayNight
  /** Stored brightness in kelvin. Demo values are synthetic. */
  brightnessK: number
  /** Fire radiative power in megawatts. Demo values are synthetic. */
  frpMw: number
  /** MODIS uses a number from 0 to 100. VIIRS uses l, n, or h. */
  confidence: number | ViirsFlag
  /** Illustrative cluster name. Not an administrative boundary. */
  cluster: string
}

export interface DailyDelivery {
  date: string
  satellite: ArchiveSatellite
  sensor: SensorId
  /** Null when the CSV delivered no rows. That is not a measurement of zero fires. */
  deliveredRows: number | null
  status: DeliveryStatus
  /** True when the local coverage note says the delivered rows cover only part of the UTC day. */
  partial: boolean
  note: string | null
}

export interface SensorSelection {
  modis: boolean
  'viirs-n20': boolean
  'viirs-n21': boolean
  'viirs-snpp': boolean
}
