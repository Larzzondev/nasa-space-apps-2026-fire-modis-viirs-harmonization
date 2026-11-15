export interface SpreadConditions {
  windTowardDeg: number
  windSpeedKmh: number
  temperatureC: number
  humidityPct: number
  hours: number
}

export interface SpreadScales {
  along: number
  cross: number
  core: number
}

export const INITIAL_SPREAD: SpreadConditions = {
  windTowardDeg: 48,
  windSpeedKmh: 28,
  temperatureC: 33,
  humidityPct: 24,
  hours: 18,
}

const COMPASS = [
  'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
] as const

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

export function compassLabel(degrees: number): string {
  const wrapped = ((degrees % 360) + 360) % 360
  const index = Math.round(wrapped / 22.5) % 16
  return COMPASS[index] ?? 'N'
}

export function spreadScales(conditions: SpreadConditions): SpreadScales {
  const wind = clamp(conditions.windSpeedKmh, 0, 80)
  const temperature = clamp(conditions.temperatureC, 0, 50)
  const humidity = clamp(conditions.humidityPct, 0, 100)
  const hours = clamp(conditions.hours, 0, 72)
  const growth = 0.42
    * (0.62 + temperature / 55)
    * (1.2 - humidity / 125)
    * (1 + wind / 28)
  return {
    along: 10 + growth * hours * 3.4,
    cross: 10 + growth * hours * (0.7 + 6 / (wind + 8)),
    core: 12 + growth * Math.min(hours, 10),
  }
}

export function windVector(degrees: number): { x: number; y: number } {
  const radians = ((degrees - 90) * Math.PI) / 180
  return { x: Math.cos(radians), y: Math.sin(radians) }
}
