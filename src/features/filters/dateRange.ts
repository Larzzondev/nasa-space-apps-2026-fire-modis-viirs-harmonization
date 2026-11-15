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
