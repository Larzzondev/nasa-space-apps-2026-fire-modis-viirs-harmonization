import type { ArchiveSatellite, SensorId, SensorSelection } from '../types/domain.ts'

export interface SensorMeta {
  id: SensorId
  label: string
  short: string
  resolution: string
  satellites: readonly ArchiveSatellite[]
  ring: string
}

export const SENSORS: readonly SensorMeta[] = [
  {
    id: 'modis',
    label: 'MODIS',
    short: 'MODIS',
    resolution: '~1 km',
    satellites: ['Terra', 'Aqua'],
    ring: '#f5b942',
  },
  {
    id: 'viirs-n20',
    label: 'VIIRS NOAA-20',
    short: 'NOAA-20',
    resolution: '375 m',
    satellites: ['NOAA-20'],
    ring: '#5ee0ff',
  },
  {
    id: 'viirs-n21',
    label: 'VIIRS NOAA-21',
    short: 'NOAA-21',
    resolution: '375 m',
    satellites: ['NOAA-21'],
    ring: '#7aa2ff',
  },
  {
    id: 'viirs-snpp',
    label: 'VIIRS S-NPP',
    short: 'S-NPP',
    resolution: '375 m',
    satellites: ['S-NPP'],
    ring: '#d4c4ff',
  },
]

export const ALL_SENSORS_ON: SensorSelection = {
  modis: true,
  'viirs-n20': true,
  'viirs-n21': true,
  'viirs-snpp': true,
}

export const SATELLITE_COLOR: Record<ArchiveSatellite, string> = {
  Terra: '#f5b942',
  Aqua: '#ff7a3c',
  'NOAA-20': '#5ee0ff',
  'NOAA-21': '#7aa2ff',
  'S-NPP': '#d4c4ff',
}

export const ARCHIVE_SATELLITES: readonly ArchiveSatellite[] = [
  'Terra',
  'Aqua',
  'NOAA-20',
  'NOAA-21',
  'S-NPP',
]

export function sensorMeta(id: SensorId): SensorMeta {
  const found = SENSORS.find((sensor) => sensor.id === id)
  if (!found) throw new Error(`Unknown sensor ${id}`)
  return found
}

export function selectedSatellites(selection: SensorSelection): ArchiveSatellite[] {
  return SENSORS.filter((sensor) => selection[sensor.id]).flatMap((sensor) => [...sensor.satellites])
}

export function sensorForSatellite(satellite: ArchiveSatellite): SensorId {
  if (satellite === 'Terra' || satellite === 'Aqua') return 'modis'
  if (satellite === 'NOAA-20') return 'viirs-n20'
  if (satellite === 'NOAA-21') return 'viirs-n21'
  return 'viirs-snpp'
}
