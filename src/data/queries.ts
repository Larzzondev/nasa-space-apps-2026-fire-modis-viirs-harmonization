import {
  deliveryOn,
  isJulyArchiveDate,
  JULY7_PORTRAITS,
  MONTH_PORTRAITS,
  type SatellitePortrait,
} from './archiveJuly2024.ts'
import { median } from './format.ts'
import { SATELLITE_COLOR } from './sensors.ts'
import type {
  ArchiveSatellite,
  DailyDelivery,
  DayNight,
  DemoHotspot,
  SensorSelection,
} from '../types/domain.ts'

export interface HotspotQuery {
  date: string
  sensors: SensorSelection
  dayNight: 'all' | DayNight
}

export function filterHotspots(
  hotspots: readonly DemoHotspot[],
  query: HotspotQuery,
): DemoHotspot[] {
  return hotspots.filter((hotspot) => {
    if (hotspot.date !== query.date) return false
    if (!query.sensors[hotspot.sensor]) return false
    if (query.dayNight !== 'all' && hotspot.dayNight !== query.dayNight) return false
    return true
  })
}

export interface HotspotSummary {
  count: number
  medianFrp: number | null
  maxFrp: number | null
  day: number
  night: number
  byPlatform: { platform: ArchiveSatellite; count: number }[]
}

export function summarizeHotspots(hotspots: readonly DemoHotspot[]): HotspotSummary {
  const frp = hotspots.map((hotspot) => hotspot.frpMw)
  const maxFrp = frp.length > 0 ? Math.max(...frp) : null
  const platforms: ArchiveSatellite[] = ['Terra', 'Aqua', 'NOAA-20', 'NOAA-21', 'S-NPP']
  return {
    count: hotspots.length,
    medianFrp: median(frp),
    maxFrp,
    day: hotspots.filter((hotspot) => hotspot.dayNight === 'D').length,
    night: hotspots.filter((hotspot) => hotspot.dayNight === 'N').length,
    byPlatform: platforms
      .map((platform) => ({
        platform,
        count: hotspots.filter((hotspot) => hotspot.platform === platform).length,
      }))
      .filter((entry) => entry.count > 0),
  }
}

export interface ArchiveDayView {
  kind: 'invalid-date' | 'outside-archive' | 'archive'
  date: string
  rows: DailyDelivery[]
  /** Sum of satellites that delivered rows. Null when none did, so a gap is not shown as zero. */
  deliveredTotal: number | null
  gapSatellites: ArchiveSatellite[]
  partialSatellites: ArchiveSatellite[]
}

export function archiveDay(date: string, satellites: readonly ArchiveSatellite[]): ArchiveDayView {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return {
      kind: 'invalid-date',
      date,
      rows: [],
      deliveredTotal: null,
      gapSatellites: [],
      partialSatellites: [],
    }
  }
  if (!isJulyArchiveDate(date)) {
    return {
      kind: 'outside-archive',
      date,
      rows: [],
      deliveredTotal: null,
      gapSatellites: [],
      partialSatellites: [],
    }
  }

  const rows = satellites
    .map((satellite) => deliveryOn(date, satellite))
    .filter((row): row is DailyDelivery => row !== null)
  const delivered = rows.filter((row) => row.deliveredRows !== null)
  return {
    kind: 'archive',
    date,
    rows,
    deliveredTotal: delivered.length > 0
      ? delivered.reduce((sum, row) => sum + (row.deliveredRows ?? 0), 0)
      : null,
    gapSatellites: rows
      .filter((row) => row.status === 'zero_rows_delivered')
      .map((row) => row.satellite),
    partialSatellites: rows.filter((row) => row.partial).map((row) => row.satellite),
  }
}

export type TrendKind = 'rows' | 'no-rows' | 'not-loaded'

export interface TrendPoint {
  kind: TrendKind
  value: number | null
}

export interface TrendSeries {
  id: ArchiveSatellite
  label: string
  color: string
  points: TrendPoint[]
}

export function trendSeries(
  dates: readonly string[],
  satellites: readonly ArchiveSatellite[],
): TrendSeries[] {
  return satellites.map((satellite) => ({
    id: satellite,
    label: satellite,
    color: SATELLITE_COLOR[satellite],
    points: dates.map((date) => {
      const row = deliveryOn(date, satellite)
      if (!row) return { kind: 'not-loaded', value: null }
      if (row.deliveredRows === null) return { kind: 'no-rows', value: null }
      return { kind: 'rows', value: row.deliveredRows }
    }),
  }))
}

export interface RangeRollup {
  delivered: number
  gapDays: number
  outsideDays: number
  partialDays: number
  coveredDays: number
}

export function rollupSatellite(
  dates: readonly string[],
  satellite: ArchiveSatellite,
): RangeRollup {
  const rollup: RangeRollup = {
    delivered: 0,
    gapDays: 0,
    outsideDays: 0,
    partialDays: 0,
    coveredDays: 0,
  }
  for (const date of dates) {
    const row = deliveryOn(date, satellite)
    if (!row) {
      rollup.outsideDays += 1
      continue
    }
    if (row.deliveredRows === null) {
      rollup.gapDays += 1
      continue
    }
    rollup.delivered += row.deliveredRows
    rollup.coveredDays += 1
    if (row.partial) rollup.partialDays += 1
  }
  return rollup
}

export interface CalendarCell {
  date: string
  day: number
  inRange: boolean
  outside: boolean
  delivered: number | null
  gaps: ArchiveSatellite[]
  partial: boolean
}

export function calendarMonth(
  year: number,
  month: number,
  satellites: readonly ArchiveSatellite[],
  rangeStart: string,
  rangeEnd: string,
): CalendarCell[] {
  const days = new Date(year, month, 0).getDate()
  const cells: CalendarCell[] = []
  for (let day = 1; day <= days; day += 1) {
    const date = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    const inRange = date >= rangeStart && date <= rangeEnd
    if (!isJulyArchiveDate(date) || satellites.length === 0) {
      cells.push({
        date,
        day,
        inRange,
        outside: !isJulyArchiveDate(date),
        delivered: null,
        gaps: [],
        partial: false,
      })
      continue
    }
    const rows = satellites
      .map((satellite) => deliveryOn(date, satellite))
      .filter((row): row is DailyDelivery => row !== null)
    const gaps = rows
      .filter((row) => row.status === 'zero_rows_delivered')
      .map((row) => row.satellite)
    const deliveredRows = rows.filter((row) => row.deliveredRows !== null)
    cells.push({
      date,
      day,
      inRange,
      outside: false,
      delivered: deliveredRows.length > 0
        ? deliveredRows.reduce((sum, row) => sum + (row.deliveredRows ?? 0), 0)
        : null,
      gaps,
      partial: rows.some((row) => row.partial),
    })
  }
  return cells
}

export function portraitsFor(
  period: 'month' | 'july7',
  satellites: readonly ArchiveSatellite[],
): SatellitePortrait[] {
  const source = period === 'month' ? MONTH_PORTRAITS : JULY7_PORTRAITS
  const allowed = new Set(satellites)
  return source.filter((portrait) => allowed.has(portrait.satellite))
}

export function coverageNotes(
  dates: readonly string[],
  satellites: readonly ArchiveSatellite[],
): DailyDelivery[] {
  const allowed = new Set(satellites)
  const notes: DailyDelivery[] = []
  for (const date of dates) {
    for (const satellite of allowed) {
      const row = deliveryOn(date, satellite)
      if (row?.note) notes.push(row)
    }
  }
  return notes
}
