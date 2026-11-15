import type { DateRange } from '../../types/domain.ts'

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/

export function toLocalIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function createDefaultDateRange(today = new Date()): DateRange {
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  start.setDate(start.getDate() - 6)
  return {
    start: toLocalIsoDate(start),
    end: toLocalIsoDate(today),
  }
}

export function isOrderedDateRange(range: DateRange): boolean {
  return range.start.length > 0 && range.end.length > 0 && range.start <= range.end
}

export function parseIsoDate(value: string): { year: number; month: number; day: number } | null {
  const match = ISO_DATE.exec(value)
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  if (!Number.isInteger(year) || month < 1 || month > 12) return null
  const lastDay = new Date(year, month, 0).getDate()
  if (day < 1 || day > lastDay) return null
  return { year, month, day }
}

export function formatIsoDate(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

export const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const

export const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const

export function shiftMonth(
  year: number,
  month: number,
  delta: number,
): { year: number; month: number } {
  const date = new Date(year, month - 1 + delta, 1)
  return { year: date.getFullYear(), month: date.getMonth() + 1 }
}

export function monthBounds(year: number, month: number): DateRange {
  const last = new Date(year, month, 0).getDate()
  return {
    start: formatIsoDate(year, month, 1),
    end: formatIsoDate(year, month, last),
  }
}

export function eachIsoDate(
  range: DateRange,
  limit = 120,
): { dates: string[]; truncated: boolean } {
  if (!isOrderedDateRange(range)) return { dates: [], truncated: false }
  const start = parseIsoDate(range.start)
  const end = parseIsoDate(range.end)
  if (!start || !end) return { dates: [], truncated: false }

  const dates: string[] = []
  const cursor = new Date(start.year, start.month - 1, start.day)
  const last = new Date(end.year, end.month - 1, end.day)
  let truncated = false
  while (cursor <= last) {
    if (dates.length >= limit) {
      truncated = true
      break
    }
    dates.push(toLocalIsoDate(cursor))
    cursor.setDate(cursor.getDate() + 1)
  }
  return { dates, truncated }
}

export function buildMonthWeeks(year: number, month: number): Array<Array<number | null>> {
  const firstWeekday = new Date(year, month - 1, 1).getDay()
  const leadingBlanks = (firstWeekday + 6) % 7
  const daysInMonth = new Date(year, month, 0).getDate()
  const cells: Array<number | null> = []

  for (let index = 0; index < leadingBlanks; index += 1) cells.push(null)
  for (let day = 1; day <= daysInMonth; day += 1) cells.push(day)
  while (cells.length % 7 !== 0) cells.push(null)

  const weeks: Array<Array<number | null>> = []
  for (let index = 0; index < cells.length; index += 7) {
    weeks.push(cells.slice(index, index + 7))
  }
  return weeks
}
