import {
  Credit,
  CreditDisplay,
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

  // The default widget credit is the Cesium ion logo. This path does not use ion,
  // so replace that logo with a library credit and keep the map credit on screen.
  CreditDisplay.cesiumCredit = new Credit(
    '<a href="https://cesium.com/platform/cesiumjs/">CesiumJS</a>',
    true,
  )

  return new Viewer(container, {
    ...sharedOptions,
    baseLayer: new ImageryLayer(
      new OpenStreetMapImageryProvider({
        url: 'https://tile.openstreetmap.org/',
        fileExtension: 'png',
        credit: new Credit(
          '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>',
          true,
        ),
      }),
    ),
    terrainProvider: new EllipsoidTerrainProvider(),
  })
}
