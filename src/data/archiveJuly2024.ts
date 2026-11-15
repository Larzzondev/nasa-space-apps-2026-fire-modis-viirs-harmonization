/**
 * Verified July 2024 aggregate statistics transcribed from tracked reports.
 *
 * Daily delivered-row counts: backend/reports/temporal_coverage_2024_07.md
 * Monthly FRP, confidence, and day/night: backend/reports/monthly_eda_2024_07.md
 * 7 July audit: backend/reports/eda_report.md
 * S-NPP coverage notes: backend/reports/coverage_investigation_2024_07.md
 *
 * A null daily count means the CSV delivered no rows. It is not zero fire activity.
 * These figures are archive rows, not unique fires.
 */

import { sensorForSatellite } from './sensors.ts'
import type {
  ArchiveSatellite,
  DailyDelivery,
  SensorId,
  ViirsFlag,
} from '../types/domain.ts'

export const ARCHIVE_MONTH = { year: 2024, month: 7 } as const
export const AUDIT_DATE = '2024-07-07'
export const ARCHIVE_CITATION =
  'July 2024 delivered-row counts from the tracked FIRMS extracts in temporal_coverage_2024_07.md. FRP, confidence, and day/night from monthly_eda_2024_07.md. The 7 July figures are from eda_report.md.'

const TERRA = [
  5335, 7052, 5110, 4711, 4643, 4779, 7044, 8180, 8022, 8117, 7689, 6162, 5141, 4926, 4099,
  6040, 6218, 7150, 7306, 6354, 5977, 6148, 5431, 7950, 7950, 8823, 7204, 7225, 4641, 4390,
  5499,
] as const

const AQUA = [
  11085, 11553, 13003, 10524, 15312, 12137, 13366, 16290, 16528, 21073, 15009, 17356, 12133,
  12176, 15315, 14254, 16512, 16467, 15517, 17112, 12686, 15779, 18065, 20325, 20836, 19693,
  20762, 16122, 16865, 15461, 12004,
] as const

const NOAA20 = [
  75912, 76448, 70183, 73754, 73331, 77793, 82372, 107599, 112171, 124687, 111556, 98679,
  75315, 63519, 77359, 86129, 88818, 104021, 101200, 94486, 82654, 93738, 101915, 123134,
  127817, 125100, 120098, 97028, 92596, 78611, 84574,
] as const

const NOAA21 = [
  70842, 75850, 69114, 70625, 72047, 74903, 87637, 101659, 108575, 121607, 109401, 101150,
  78327, 60072, 72728, 85741, 83675, 101410, 97945, 33039, 75528, 90257, 104530, 119286,
  125747, 114781, 117758, 93261, 94972, 77275, 81472,
] as const

const SNPP: readonly (number | null)[] = [
  76090, 77742, 71875, 74140, 74121, 78437, 86840, 106502, 103164, null, null, null, null, null,
  null, 15643, 89521, 105489, 102434, 94011, 79398, 90260, 107101, 14621, null, null, null, null,
  17802, 82443, 87386,
]

const SERIES: Record<ArchiveSatellite, readonly (number | null)[]> = {
  Terra: TERRA,
  Aqua: AQUA,
  'NOAA-20': NOAA20,
  'NOAA-21': NOAA21,
  'S-NPP': SNPP,
}

const SNPP_NOTES: Record<string, { partial: boolean; note: string }> = {
  '2024-07-10': {
    partial: false,
    note: 'No rows delivered. This date is inside the LP DAAC Suomi-NPP geolocation gap. Not zero fire activity.',
  },
  '2024-07-11': {
    partial: false,
    note: 'No rows delivered. This date is inside the LP DAAC Suomi-NPP geolocation gap. Not zero fire activity.',
  },
  '2024-07-12': {
    partial: false,
    note: 'No rows delivered. This date is inside the LP DAAC Suomi-NPP geolocation gap. Not zero fire activity.',
  },
  '2024-07-13': {
    partial: false,
    note: 'No rows delivered. This date is inside the LP DAAC Suomi-NPP geolocation gap. Not zero fire activity.',
  },
  '2024-07-14': {
    partial: false,
    note: 'No rows delivered. This date is inside the LP DAAC Suomi-NPP geolocation gap. Not zero fire activity.',
  },
  '2024-07-15': {
    partial: false,
    note: 'No rows delivered. This date is inside the LP DAAC Suomi-NPP geolocation gap. Not zero fire activity.',
  },
  '2024-07-16': {
    partial: true,
    note: '15,643 rows delivered after 17:42 UTC. Earlier that day is inside the stated geolocation gap.',
  },
  '2024-07-24': {
    partial: true,
    note: '14,621 rows delivered before 05:28 UTC. LP DAAC describes an outage from 05:28 to 18:22 UTC.',
  },
  '2024-07-25': {
    partial: false,
    note: 'No rows delivered. The coverage note does not class this date as a confirmed outage. Not zero fire activity.',
  },
  '2024-07-26': {
    partial: false,
    note: 'No rows delivered. The coverage note does not class this date as a confirmed outage. Not zero fire activity.',
  },
  '2024-07-27': {
    partial: false,
    note: 'No rows delivered. The coverage note does not class this date as a confirmed outage. Not zero fire activity.',
  },
  '2024-07-28': {
    partial: false,
    note: 'No rows delivered. The coverage note does not class this date as a confirmed outage. Not zero fire activity.',
  },
  '2024-07-29': {
    partial: true,
    note: '17,802 rows delivered after 15:24 UTC.',
  },
}

function isoDate(day: number): string {
  return `2024-07-${String(day).padStart(2, '0')}`
}

function buildDeliveries(): DailyDelivery[] {
  const rows: DailyDelivery[] = []
  for (const satellite of Object.keys(SERIES) as ArchiveSatellite[]) {
    const series = SERIES[satellite]
    series.forEach((value, index) => {
      const date = isoDate(index + 1)
      const coverage = satellite === 'S-NPP' ? SNPP_NOTES[date] : undefined
      const lowNoaa21 = satellite === 'NOAA-21' && date === '2024-07-20'
      rows.push({
        date,
        satellite,
        sensor: sensorForSatellite(satellite),
        deliveredRows: value,
        status: value === null ? 'zero_rows_delivered' : 'rows_delivered',
        partial: coverage?.partial ?? false,
        note: coverage?.note ?? (lowNoaa21
          ? '33,039 rows delivered. No rows in UTC hours 08–13. Not an empty day.'
          : null),
      })
    })
  }
  return rows
}

export const JULY_DELIVERIES: readonly DailyDelivery[] = buildDeliveries()

const DELIVERY_INDEX = new Map<string, DailyDelivery>(
  JULY_DELIVERIES.map((row) => [`${row.date}|${row.satellite}`, row]),
)

export function isJulyArchiveDate(date: string): boolean {
  return DELIVERY_INDEX.has(`${date}|Terra`)
}

export function deliveryOn(date: string, satellite: ArchiveSatellite): DailyDelivery | null {
  return DELIVERY_INDEX.get(`${date}|${satellite}`) ?? null
}

export interface FrpMarkers {
  mean: number
  median: number
  p95: number
  p99: number
  max: number
}

export interface ModisConfidence {
  kind: 'modis'
  median: number
  zeros: number | null
  hundreds: number | null
}

export interface ViirsConfidenceBreakdown {
  kind: 'viirs'
  low: number
  nominal: number
  high: number
}

export interface SatellitePortrait {
  satellite: ArchiveSatellite
  sensor: SensorId
  deliveredRows: number
  day: number
  night: number
  frp: FrpMarkers
  confidence: ModisConfidence | ViirsConfidenceBreakdown
}

export const MONTH_PORTRAITS: readonly SatellitePortrait[] = [
  {
    satellite: 'Terra',
    sensor: 'modis',
    deliveredRows: 195316,
    day: 104032,
    night: 91284,
    frp: { mean: 45.551, median: 19.1, p95: 147.2, p99: 462, max: 6002.5 },
    confidence: { kind: 'modis', median: 69, zeros: 2414, hundreds: 30113 },
  },
  {
    satellite: 'Aqua',
    sensor: 'modis',
    deliveredRows: 481320,
    day: 448221,
    night: 33099,
    frp: { mean: 51.4279, median: 21.6, p95: 165.9, p99: 521.6, max: 10950 },
    confidence: { kind: 'modis', median: 69, zeros: 4240, hundreds: 29197 },
  },
  {
    satellite: 'NOAA-20',
    sensor: 'viirs-n20',
    deliveredRows: 2902597,
    day: 2018537,
    night: 884060,
    frp: { mean: 10.6352, median: 5.14, p95: 35.4, p99: 104.77, max: 2825.18 },
    confidence: { kind: 'viirs', low: 265829, nominal: 2479081, high: 157687 },
  },
  {
    satellite: 'NOAA-21',
    sensor: 'viirs-n21',
    deliveredRows: 2771214,
    day: 1907205,
    night: 864009,
    frp: { mean: 12.6347, median: 6.09, p95: 40.96, p99: 129.72, max: 2858.66 },
    confidence: { kind: 'viirs', low: 257640, nominal: 2324309, high: 189265 },
  },
  {
    satellite: 'S-NPP',
    sensor: 'viirs-snpp',
    deliveredRows: 1635020,
    day: 1125000,
    night: 510020,
    frp: { mean: 10.6144, median: 5.06, p95: 36.27, p99: 103.89, max: 2824.71 },
    confidence: { kind: 'viirs', low: 133710, nominal: 1401558, high: 99752 },
  },
]

export const JULY7_PORTRAITS: readonly SatellitePortrait[] = [
  {
    satellite: 'Terra',
    sensor: 'modis',
    deliveredRows: 7044,
    day: 3177,
    night: 3867,
    frp: { mean: 42.7793, median: 18.9, p95: 131.2, p99: 460.911, max: 2901.5 },
    confidence: { kind: 'modis', median: 69, zeros: null, hundreds: null },
  },
  {
    satellite: 'Aqua',
    sensor: 'modis',
    deliveredRows: 13366,
    day: 12152,
    night: 1214,
    frp: { mean: 50.6342, median: 19.5, p95: 160.6, p99: 543.07, max: 7956.3 },
    confidence: { kind: 'modis', median: 69, zeros: null, hundreds: null },
  },
  {
    satellite: 'NOAA-20',
    sensor: 'viirs-n20',
    deliveredRows: 82372,
    day: 51168,
    night: 31204,
    frp: { mean: 9.2702, median: 4.47, p95: 30.1, p99: 92.105, max: 1168.99 },
    confidence: { kind: 'viirs', low: 6937, nominal: 72727, high: 2708 },
  },
  {
    satellite: 'NOAA-21',
    sensor: 'viirs-n21',
    deliveredRows: 87637,
    day: 49780,
    night: 37857,
    frp: { mean: 11.8105, median: 5.37, p95: 37.93, p99: 120.9864, max: 1740.42 },
    confidence: { kind: 'viirs', low: 5913, nominal: 74845, high: 6879 },
  },
  {
    satellite: 'S-NPP',
    sensor: 'viirs-snpp',
    deliveredRows: 86840,
    day: 54087,
    night: 32753,
    frp: { mean: 9.6066, median: 4.55, p95: 32.24, p99: 91.17, max: 974.25 },
    confidence: { kind: 'viirs', low: 6185, nominal: 75488, high: 5167 },
  },
]

export const SCAN_NOTE =
  'On 7 July 2024 the median stored scan was 1.2 km for Terra and Aqua, 0.42 km for NOAA-20, and 0.44 km for NOAA-21 and S-NPP. MODIS scan reached 4.8 km and VIIRS scan reached 0.8 km. Scan is the stored along-scan pixel size, not a harmonized footprint.'

export const VIIRS_FLAG_LABEL: Record<ViirsFlag, string> = {
  l: 'Low',
  n: 'Nominal',
  h: 'High',
}

const WEEKLY_EXPECTED: Record<ArchiveSatellite, readonly number[]> = {
  Terra: [38674, 48237, 43144, 50731, 14530],
  Aqua: [86980, 110565, 107863, 131582, 44330],
  'NOAA-20': [529793, 693526, 634667, 788830, 255781],
  'NOAA-21': [521018, 680791, 550066, 765620, 253719],
  'S-NPP': [539245, 209666, 486496, 211982, 187631],
}

const MONTH_EXPECTED: Record<ArchiveSatellite, number> = {
  Terra: 195316,
  Aqua: 481320,
  'NOAA-20': 2902597,
  'NOAA-21': 2771214,
  'S-NPP': 1635020,
}

function weeklySums(values: readonly (number | null)[]): number[] {
  const cuts = [
    [0, 7],
    [7, 14],
    [14, 21],
    [21, 28],
    [28, 31],
  ] as const
  return cuts.map(([start, end]) =>
    values.slice(start, end).reduce<number>((sum, value) => sum + (value ?? 0), 0),
  )
}

function assertPortrait(portrait: SatellitePortrait, label: string) {
  if (portrait.day + portrait.night !== portrait.deliveredRows) {
    throw new Error(`${label} ${portrait.satellite} day/night does not match the row count.`)
  }
  if (portrait.confidence.kind === 'viirs') {
    const { low, nominal, high } = portrait.confidence
    if (low + nominal + high !== portrait.deliveredRows) {
      throw new Error(`${label} ${portrait.satellite} confidence flags do not match the row count.`)
    }
  }
}

function verifyArchive() {
  for (const satellite of Object.keys(SERIES) as ArchiveSatellite[]) {
    const series = SERIES[satellite]
    if (series.length !== 31) throw new Error(`${satellite} does not have 31 daily values.`)
    const total = series.reduce<number>((sum, value) => sum + (value ?? 0), 0)
    if (total !== MONTH_EXPECTED[satellite]) {
      throw new Error(`${satellite} daily rows sum to ${total}, expected ${MONTH_EXPECTED[satellite]}.`)
    }
    const weeks = weeklySums(series)
    WEEKLY_EXPECTED[satellite].forEach((expected, index) => {
      if (weeks[index] !== expected) {
        throw new Error(`${satellite} week ${index + 1} is ${weeks[index]}, expected ${expected}.`)
      }
    })
  }

  const july7 = (['Terra', 'Aqua', 'NOAA-20', 'NOAA-21', 'S-NPP'] as const).reduce(
    (sum, satellite) => sum + (SERIES[satellite][6] ?? 0),
    0,
  )
  if (july7 !== 277259) throw new Error(`7 July rows sum to ${july7}, expected 277259.`)

  for (const portrait of MONTH_PORTRAITS) {
    assertPortrait(portrait, 'July')
    if (portrait.deliveredRows !== MONTH_EXPECTED[portrait.satellite]) {
      throw new Error(`${portrait.satellite} portrait does not match the daily total.`)
    }
  }
  for (const portrait of JULY7_PORTRAITS) {
    assertPortrait(portrait, '7 July')
    if (portrait.deliveredRows !== SERIES[portrait.satellite][6]) {
      throw new Error(`${portrait.satellite} 7 July portrait does not match the daily table.`)
    }
  }
}

verifyArchive()
