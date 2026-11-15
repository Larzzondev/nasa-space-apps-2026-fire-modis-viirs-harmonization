import { useRef } from 'react'
import type { AreaOfInterest } from '../../types/domain.ts'
import { globeBasemapLabel } from '../../config/cesium.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { useCesiumViewer } from './useCesiumViewer.ts'

interface CesiumViewerProps {
  area: AreaOfInterest | null
  extentIsDemo: boolean
}

export function CesiumViewer({ area, extentIsDemo }: CesiumViewerProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const { status, errorMessage } = useCesiumViewer(hostRef, area)
  const basemapLabel = globeBasemapLabel()

  return (
    <section
      aria-label="Interactive 3D globe"
      className="relative h-[68vh] min-h-[360px] bg-ink lg:h-auto lg:min-h-0 lg:flex-1"
    >
      <div ref={hostRef} className="absolute inset-0" />
      <div className="pointer-events-none absolute top-3 left-3 z-10 max-w-xs rounded-md border border-line bg-ink/85 px-3 py-2 text-xs shadow-lg backdrop-blur-sm">
        {status === 'loading' ? <p className="text-paper">Opening the globe…</p> : null}
        {status === 'error' ? (
          <p className="text-[#f3c7a4]">{errorMessage ?? 'The globe could not be created.'}</p>
        ) : null}
        {status === 'ready' && area && extentIsDemo ? (
          <>
            <Badge tone="demo">DEMO</Badge>
            <p className="mt-1 font-medium text-paper">{area.name}</p>
            <p className="mt-1 text-mist">Camera extent only. Not a fire perimeter.</p>
          </>
        ) : null}
        {status === 'ready' && !area ? <p className="text-paper">No hotspot layer loaded.</p> : null}
        {status === 'ready' ? <p className="mt-1 text-mist">{basemapLabel}</p> : null}
      </div>
    </section>
  )
}
