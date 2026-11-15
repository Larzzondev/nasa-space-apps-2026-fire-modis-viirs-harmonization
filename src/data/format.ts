import type { ViirsFlag } from '../types/domain.ts'

export function formatCount(value: number): string {
  return value.toLocaleString('en-US')
}

export function formatCompact(value: number): string {
  if (value >= 100_000) return `${Math.round(value / 1000)}k`
  if (value >= 10_000) return `${(value / 1000).toFixed(1)}k`
  return formatCount(value)
}

export function formatMw(value: number): string {
  return value.toLocaleString('en-US', {
    maximumFractionDigits: value >= 100 ? 1 : 2,
  })
}

export function formatLatitude(value: number): string {
  return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? 'N' : 'S'}`
}

export function formatLongitude(value: number): string {
  return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? 'E' : 'W'}`
}

export function formatAcqTime(hhmm: string): string {
  if (!/^\d{4}$/.test(hhmm)) return hhmm
  return `${hhmm.slice(0, 2)}:${hhmm.slice(2)} UTC`
}

export function formatConfidence(value: number | ViirsFlag): { value: string; scale: string } {
  if (typeof value === 'number') {
    return { value: String(value), scale: 'MODIS numeric confidence, 0–100' }
  }
  const names: Record<ViirsFlag, string> = { l: 'Low', n: 'Nominal', h: 'High' }
  return { value: `${names[value]} (${value})`, scale: 'VIIRS categorical confidence' }
}

export function median(values: readonly number[]): number | null {
  if (values.length === 0) return null
  const sorted = [...values].sort((left, right) => left - right)
  const mid = Math.floor(sorted.length / 2)
  if (sorted.length % 2 === 0) {
    return ((sorted[mid - 1] ?? 0) + (sorted[mid] ?? 0)) / 2
  }
  return sorted[mid] ?? null
}
