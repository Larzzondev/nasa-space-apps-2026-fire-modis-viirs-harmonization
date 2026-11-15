import { useEffect, useRef, useState } from 'react'
import {
  Cartesian2,
  Cartesian3,
  Color,
  Math as CesiumMath,
  NearFarScalar,
  PointPrimitiveCollection,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  type Viewer,
} from 'cesium'
import type { DemoHotspot } from '../../types/domain.ts'
import { SATELLITE_COLOR } from '../../data/sensors.ts'
import { frpColor, frpPixelSize } from '../../data/hotspotStyle.ts'
import { createGlobeViewer } from './createGlobeViewer.ts'

interface CesiumGlobeProps {
  hotspots: readonly DemoHotspot[]
  selectedId: string | null
  active: boolean
  flyHomeToken: number
  onSelect: (id: string | null) => void
}

const HOME_VIEW = {
  destination: Cartesian3.fromDegrees(-48, 18, 18_500_000),
  orientation: {
    heading: 0,
    pitch: CesiumMath.toRadians(-80),
    roll: 0,
  },
}

function frameHome(viewer: Viewer) {
  viewer.camera.flyTo({ ...HOME_VIEW, duration: 1.15 })
}

function hotspotIdFromPick(picked: unknown): string | null {
  if (!picked || typeof picked !== 'object') return null
  const record = picked as { id?: unknown; primitive?: { id?: unknown } }
  if (typeof record.id === 'string' && record.id.startsWith('demo-')) return record.id
  if (typeof record.primitive?.id === 'string' && record.primitive.id.startsWith('demo-')) {
    return record.primitive.id
  }
  return null
}

export function CesiumGlobe({
  hotspots,
  selectedId,
  active,
  flyHomeToken,
  onSelect,
}: CesiumGlobeProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<Viewer | null>(null)
  const pointsRef = useRef<PointPrimitiveCollection | null>(null)
  const onSelectRef = useRef(onSelect)
  const lookupRef = useRef(hotspots)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    onSelectRef.current = onSelect
    lookupRef.current = hotspots
  }, [hotspots, onSelect])

  useEffect(() => {
    const host = hostRef.current
    if (!host) return

    const container = document.createElement('div')
    container.className = 'h-full w-full'
    host.replaceChildren(container)

    let viewer: Viewer
    try {
      viewer = createGlobeViewer(container)
    } catch (error) {
      container.remove()
      const message = error instanceof Error ? error.message : 'The globe could not be created.'
      queueMicrotask(() => {
        setStatus('error')
        setErrorMessage(message)
      })
      return
    }

    viewer.scene.backgroundColor = Color.fromCssColorString('#05070c')
    viewer.scene.globe.baseColor = Color.fromCssColorString('#121820')
    viewer.scene.screenSpaceCameraController.minimumZoomDistance = 80_000
    viewer.scene.screenSpaceCameraController.maximumZoomDistance = 42_000_000
    viewer.camera.setView(HOME_VIEW)

    const points = viewer.scene.primitives.add(new PointPrimitiveCollection())
    pointsRef.current = points
    viewerRef.current = viewer

    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
    handler.setInputAction((event: { position: Cartesian2 }) => {
      const picked = viewer.scene.pick(event.position)
      onSelectRef.current(hotspotIdFromPick(picked))
    }, ScreenSpaceEventType.LEFT_CLICK)
    handler.setInputAction((event: { endPosition: Cartesian2 }) => {
      const picked = viewer.scene.pick(event.endPosition)
      viewer.scene.canvas.style.cursor = hotspotIdFromPick(picked) ? 'pointer' : ''
    }, ScreenSpaceEventType.MOUSE_MOVE)

    const homeCommand = viewer.homeButton.viewModel.command
    const cancelHome = (event: { cancel: boolean }) => {
      event.cancel = true
      frameHome(viewer)
    }
    homeCommand.beforeExecute.addEventListener(cancelHome)

    const renderOnTiles = () => {
      if (!viewer.isDestroyed()) viewer.scene.requestRender()
    }
    viewer.scene.globe.tileLoadProgressEvent.addEventListener(renderOnTiles)

    const resizeObserver = new ResizeObserver(() => {
      if (viewer.isDestroyed()) return
      viewer.resize()
      viewer.scene.requestRender()
    })
    resizeObserver.observe(host)

    let alive = true
    queueMicrotask(() => {
      if (!alive) return
      setStatus('ready')
      setErrorMessage(null)
    })

    return () => {
      alive = false
      resizeObserver.disconnect()
      if (!handler.isDestroyed()) handler.destroy()
      homeCommand.beforeExecute.removeEventListener(cancelHome)
      viewer.scene.globe.tileLoadProgressEvent.removeEventListener(renderOnTiles)
      pointsRef.current = null
      viewerRef.current = null
      try {
        if (!viewer.isDestroyed()) viewer.destroy()
      } catch {
        // The widget is already leaving the page.
      }
      container.remove()
    }
  }, [])

  useEffect(() => {
    const viewer = viewerRef.current
    const points = pointsRef.current
    if (!viewer || viewer.isDestroyed() || !points || status !== 'ready') return

    points.removeAll()
    const scale = new NearFarScalar(2.0e6, 1.35, 1.8e7, 0.42)
    for (const hotspot of hotspots) {
      const selected = hotspot.id === selectedId
      const size = frpPixelSize(hotspot.frpMw)
      points.add({
        id: hotspot.id,
        position: Cartesian3.fromDegrees(hotspot.longitude, hotspot.latitude),
        pixelSize: selected ? size + 7 : size,
        color: Color.fromCssColorString(frpColor(hotspot.frpMw)),
        outlineColor: Color.fromCssColorString(
          selected ? '#f4fbff' : SATELLITE_COLOR[hotspot.platform],
        ),
        outlineWidth: selected ? 3 : 1.5,
        scaleByDistance: scale,
      })
    }
    viewer.scene.requestRender()
  }, [hotspots, selectedId, status])

  useEffect(() => {
    if (!selectedId || status !== 'ready') return
    const viewer = viewerRef.current
    const hotspot = lookupRef.current.find((item) => item.id === selectedId)
    if (!viewer || viewer.isDestroyed() || !hotspot) return
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(hotspot.longitude, hotspot.latitude, 1_500_000),
      orientation: {
        heading: 0,
        pitch: CesiumMath.toRadians(-90),
        roll: 0,
      },
      duration: 0.95,
    })
  }, [selectedId, status])

  useEffect(() => {
    if (!active || status !== 'ready') return
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    const frame = requestAnimationFrame(() => {
      if (viewer.isDestroyed()) return
      viewer.resize()
      viewer.scene.requestRender()
    })
    return () => cancelAnimationFrame(frame)
  }, [active, status])

  useEffect(() => {
    if (flyHomeToken === 0 || status !== 'ready') return
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    frameHome(viewer)
  }, [flyHomeToken, status])

  return (
    <div className="absolute inset-0 bg-ink" aria-label="Interactive fire globe">
      <div ref={hostRef} className="absolute inset-0" />
      {status === 'loading' ? (
        <div className="absolute inset-0 grid place-items-center bg-ink" role="status">
          <div className="text-center">
            <div className="mx-auto size-8 animate-pulse rounded-full bg-ember" />
            <p className="mt-4 text-sm text-paper">Opening the globe</p>
            <p className="mt-1 text-xs text-mist">OpenStreetMap basemap. No Cesium ion token required.</p>
          </div>
        </div>
      ) : null}
      {status === 'error' ? (
        <div className="absolute inset-0 grid place-items-center bg-ink p-6" role="alert">
          <p className="max-w-sm text-center text-sm text-[#ffc4ca]">
            {errorMessage ?? 'The globe could not be created.'}
          </p>
        </div>
      ) : null}
    </div>
  )
}
