import type { AreaOfInterest } from '../types/domain.ts'

/**
 * DEMO ONLY.
 * Coarse camera frames for the sidebar and globe.
 * These are not fire perimeters, administrative boundaries, or NASA products.
 * Sample hotspot rows are intentionally absent.
 */
export const DEMO_AREAS: readonly AreaOfInterest[] = [
  {
    id: 'demo-western-us',
    name: 'Western United States',
    bounds: { west: -125, south: 32, east: -102, north: 49 },
  },
  {
    id: 'demo-amazon',
    name: 'Amazon Basin',
    bounds: { west: -75, south: -15, east: -48, north: 5 },
  },
  {
    id: 'demo-mediterranean',
    name: 'Mediterranean Basin',
    bounds: { west: -10, south: 30, east: 36, north: 46 },
  },
  {
    id: 'demo-southeast-australia',
    name: 'Southeast Australia',
    bounds: { west: 140, south: -44, east: 154, north: -28 },
  },
]
