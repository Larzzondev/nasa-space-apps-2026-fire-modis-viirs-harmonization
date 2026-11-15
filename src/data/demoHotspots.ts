/**
 * Deterministic synthetic hotspot sample for the globe.
 *
 * These records are not FIRMS observations. Every record has source: 'demo'.
 * Replace this export with parsed FIRMS rows later, and set source: 'firms'
 * on those rows. Do not append real rows onto this array without that label.
 *
 * The sample covers 1–7 July 2024 so the date control changes the map.
 * Positions are illustrative clusters, not the archived coordinates.
 */

import type { ArchiveSatellite, DayNight, DemoHotspot, SensorId, ViirsFlag } from '../types/domain.ts'

export const DEMO_SAMPLE_START = '2024-07-01'
export const DEMO_SAMPLE_END = '2024-07-07'

interface Region {
  name: string
  lat: number
  lon: number
  spreadLat: number
  spreadLon: number
  weight: number
}

const REGIONS: readonly Region[] = [
  { name: 'Boreal Canada', lat: 58.4, lon: -116.5, spreadLat: 3.8, spreadLon: 7.5, weight: 26 },
  { name: 'Northern California', lat: 40.3, lon: -121.6, spreadLat: 1.4, spreadLon: 1.8, weight: 12 },
  { name: 'Pacific Northwest', lat: 45.8, lon: -121.2, spreadLat: 2.2, spreadLon: 2.6, weight: 7 },
  { name: 'Amazon Basin', lat: -6.2, lon: -60.4, spreadLat: 5.5, spreadLon: 7.2, weight: 11 },
  { name: 'Central Africa', lat: -3.5, lon: 22.4, spreadLat: 5.2, spreadLon: 7.4, weight: 16 },
  { name: 'Southern Africa', lat: -17.6, lon: 25.8, spreadLat: 4.4, spreadLon: 5.5, weight: 9 },
  { name: 'Siberia', lat: 62.2, lon: 108.5, spreadLat: 4.2, spreadLon: 12, weight: 13 },
  { name: 'Mediterranean', lat: 39.4, lon: 22.5, spreadLat: 2.4, spreadLon: 5.2, weight: 5 },
  { name: 'Mainland Southeast Asia', lat: 16.2, lon: 103.4, spreadLat: 3.4, spreadLon: 4.6, weight: 6 },
  { name: 'Southeast Australia', lat: -35.4, lon: 147.2, spreadLat: 2.2, spreadLon: 2.8, weight: 3 },
]

const REGION_WEIGHT = REGIONS.reduce((sum, region) => sum + region.weight, 0)

const BASE_COUNT: Record<SensorId, number> = {
  modis: 42,
  'viirs-n20': 58,
  'viirs-n21': 58,
  'viirs-snpp': 52,
}

function mulberry32(seed: number): () => number {
  let state = seed
  return () => {
    state = (state + 0x6d2b79f5) | 0
    let next = Math.imul(state ^ (state >>> 15), 1 | state)
    next = (next + Math.imul(next ^ (next >>> 7), 61 | next)) ^ next
    return ((next ^ (next >>> 14)) >>> 0) / 4294967296
  }
}

function gauss(rng: () => number): number {
  const u = Math.max(rng(), 1e-9)
  const v = rng()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function pickRegion(rng: () => number): Region {
  let ticket = rng() * REGION_WEIGHT
  for (const region of REGIONS) {
    ticket -= region.weight
    if (ticket <= 0) return region
  }
  const fallback = REGIONS[REGIONS.length - 1]
  if (!fallback) throw new Error('Demo regions are empty.')
  return fallback
}

function sampleFrp(sensor: SensorId, rng: () => number): number {
  const roll = rng()
  if (sensor === 'modis') {
    if (roll > 0.97) return Math.round((180 + rng() * 1400) * 10) / 10
    if (roll > 0.8) return Math.round((40 + rng() * 140) * 10) / 10
    return Math.round((4 + rng() * 34) * 10) / 10
  }
  if (roll > 0.97) return Math.round((40 + rng() * 220) * 100) / 100
  if (roll > 0.78) return Math.round((8 + rng() * 28) * 100) / 100
  return Math.round((0.6 + rng() * 7.4) * 100) / 100
}

function dayNightFor(longitude: number, hhmm: number): DayNight {
  const hour = Math.floor(hhmm / 100) + (hhmm % 100) / 60
  const local = (hour + longitude / 15 + 48) % 24
  return local >= 6 && local < 18 ? 'D' : 'N'
}

function buildSample(): DemoHotspot[] {
  const rng = mulberry32(20240707)
  const points: DemoHotspot[] = []

  for (let day = 1; day <= 7; day += 1) {
    const date = `2024-07-${String(day).padStart(2, '0')}`
    const sensors = Object.keys(BASE_COUNT) as SensorId[]
    for (const sensor of sensors) {
      const count = Math.round(BASE_COUNT[sensor] * (0.88 + rng() * 0.24))
      for (let index = 0; index < count; index += 1) {
        const region = pickRegion(rng)
        const latitude = clamp(
          region.lat + gauss(rng) * region.spreadLat * 0.42,
          -55,
          72,
        )
        const longitude = clamp(
          region.lon + gauss(rng) * region.spreadLon * 0.42,
          -179.5,
          179.5,
        )
        const minutes = Math.floor(rng() * 24 * 60)
        const hhmm = Math.floor(minutes / 60) * 100 + (minutes % 60)
        const acqTime = String(hhmm).padStart(4, '0')
        const frpMw = sampleFrp(sensor, rng)
        const platform: ArchiveSatellite = sensor === 'modis'
          ? (rng() < 0.29 ? 'Terra' : 'Aqua')
          : sensor === 'viirs-n20'
            ? 'NOAA-20'
            : sensor === 'viirs-n21'
              ? 'NOAA-21'
              : 'S-NPP'

        let brightnessK: number
        let confidence: number | ViirsFlag
        if (sensor === 'modis') {
          brightnessK = Math.round(Math.min(500, 304 + Math.sqrt(frpMw) * 3.1 + rng() * 10) * 10) / 10
          const roll = rng()
          confidence = roll < 0.04 ? Math.floor(rng() * 35) : Math.floor(50 + rng() * 51)
        } else {
          const saturated = rng() > 0.93
          brightnessK = saturated
            ? 367
            : Math.round(Math.min(359.5, 300 + Math.sqrt(frpMw) * 4.2 + rng() * 8) * 100) / 100
          if (brightnessK === 367 && rng() > 0.22) confidence = 'h'
          else if (rng() < 0.12) confidence = 'l'
          else confidence = 'n'
        }

        points.push({
          id: `demo-${date}-${sensor}-${index}`,
          source: 'demo',
          latitude: Math.round(latitude * 10000) / 10000,
          longitude: Math.round(longitude * 10000) / 10000,
          date,
          acqTime,
          sensor,
          platform,
          dayNight: dayNightFor(longitude, hhmm),
          brightnessK,
          frpMw,
          confidence,
          cluster: region.name,
        })
      }
    }
  }

  return points
}

export const DEMO_HOTSPOTS: readonly DemoHotspot[] = buildSample()

if (DEMO_HOTSPOTS.length < 1100 || DEMO_HOTSPOTS.length > 1800) {
  throw new Error(`Demo sample size ${DEMO_HOTSPOTS.length} is outside the render bound.`)
}
