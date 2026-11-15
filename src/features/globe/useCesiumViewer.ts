import { useEffect, useRef, useState, type RefObject } from 'react'
import { Color, Rectangle, type Viewer } from 'cesium'
import type { AreaOfInterest } from '../../types/domain.ts'
import { createGlobeViewer } from './createGlobeViewer.ts'

const EXTENT_ID = 'demo-area-extent'

function clearExtent(viewer: Viewer) {
  const existing = viewer.entities.getById(EXTENT_ID)
  if (existing) viewer.entities.remove(existing)
}

function showExtent(viewer: Viewer, area: AreaOfInterest) {
  clearExtent(viewer)
  const { bounds } = area
  viewer.entities.add({
    id: EXTENT_ID,
    name: `${area.name} (DEMO)`,
    rectangle: {
      coordinates: Rectangle.fromDegrees(bounds.west, bounds.south, bounds.east, bounds.north),
      fill: true,
      material: Color.fromCssColorString('#e07a3d').withAlpha(0.16),
      outline: true,
      outlineColor: Color.fromCssColorString('#f0a36a'),
    },
  })
}

function flyToArea(viewer: Viewer, area: AreaOfInterest) {
  const { bounds } = area
  const latitudePad = (bounds.north - bounds.south) * 0.12
  const longitudePad = (bounds.east - bounds.west) * 0.12
  viewer.camera.flyTo({
    destination: Rectangle.fromDegrees(
      Math.max(-180, bounds.west - longitudePad),
      Math.max(-90, bounds.south - latitudePad),
      Math.min(180, bounds.east + longitudePad),
      Math.min(90, bounds.north + latitudePad),
    ),
    duration: 1.15,
  })
  viewer.scene.requestRender()
}

export function useCesiumViewer(
  hostRef: RefObject<HTMLDivElement | null>,
  area: AreaOfInterest | null,
) {
  const viewerRef = useRef<Viewer | null>(null)
  const hadAreaRef = useRef(false)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return

    const container = document.createElement('div')
    container.className = 'h-full w-full'
    host.replaceChildren(container)

    let active = true
    const publish = (nextStatus: 'ready' | 'error', message: string | null) => {
      queueMicrotask(() => {
        if (!active) return
        setStatus(nextStatus)
        setErrorMessage(message)
      })
    }

    let viewer: Viewer
    try {
      viewer = createGlobeViewer(container)
    } catch (error) {
      container.remove()
      publish('error', error instanceof Error ? error.message : 'The globe could not be created.')
      return () => {
        active = false
      }
    }

    viewerRef.current = viewer
    publish('ready', null)

    return () => {
      active = false
      viewerRef.current = null
      try {
        if (!viewer.isDestroyed()) viewer.destroy()
      } catch {
        // The widget is already leaving the page.
      }
      container.remove()
    }
  }, [hostRef])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed() || status !== 'ready') return

    if (!area) {
      clearExtent(viewer)
      if (hadAreaRef.current) viewer.camera.flyHome(1.1)
      hadAreaRef.current = false
      viewer.scene.requestRender()
      return
    }

    hadAreaRef.current = true
    showExtent(viewer, area)
    flyToArea(viewer, area)
  }, [area, status])

  return { status, errorMessage }
}
