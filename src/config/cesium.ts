export function readCesiumIonToken(): string | undefined {
  const value = import.meta.env.VITE_CESIUM_ION_TOKEN
  if (typeof value !== 'string') return undefined
  const token = value.trim()
  return token.length > 0 ? token : undefined
}

export function globeBasemapLabel(): string {
  return readCesiumIonToken() ? 'Basemap: Cesium ion' : 'Basemap: OpenStreetMap'
}
