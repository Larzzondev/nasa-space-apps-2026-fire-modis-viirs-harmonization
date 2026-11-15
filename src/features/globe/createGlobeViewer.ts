import {
  EllipsoidTerrainProvider,
  ImageryLayer,
  Ion,
  OpenStreetMapImageryProvider,
  Terrain,
  Viewer,
} from 'cesium'
import { readCesiumIonToken } from '../../config/cesium.ts'

const sharedOptions = {
  animation: false,
  timeline: false,
  baseLayerPicker: false,
  geocoder: false,
  navigationHelpButton: false,
  infoBox: false,
  selectionIndicator: false,
  homeButton: true,
  sceneModePicker: true,
  fullscreenButton: true,
  shouldAnimate: false,
  requestRenderMode: true,
} satisfies Viewer.ConstructorOptions

export function createGlobeViewer(container: HTMLElement): Viewer {
  const token = readCesiumIonToken()

  if (token) {
    Ion.defaultAccessToken = token
    return new Viewer(container, {
      ...sharedOptions,
      terrain: Terrain.fromWorldTerrain(),
    })
  }

  return new Viewer(container, {
    ...sharedOptions,
    baseLayer: new ImageryLayer(
      new OpenStreetMapImageryProvider({
        url: 'https://tile.openstreetmap.org/',
        fileExtension: 'png',
        credit: '© OpenStreetMap contributors',
      }),
    ),
    terrainProvider: new EllipsoidTerrainProvider(),
  })
}
