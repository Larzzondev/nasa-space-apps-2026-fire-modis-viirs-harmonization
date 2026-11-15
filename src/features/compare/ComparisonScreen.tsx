import { useMemo, useState } from 'react'
import { Badge } from '../../components/ui/Badge.tsx'
import { SensorToggles } from '../../components/filters/SensorToggles.tsx'
import {
  ARCHIVE_CITATION,
  SCAN_NOTE,
  type SatellitePortrait,
} from '../../data/archiveJuly2024.ts'
import { formatCount, formatMw } from '../../data/format.ts'
import { portraitsFor } from '../../data/queries.ts'
import { ALL_SENSORS_ON, SATELLITE_COLOR, selectedSatellites } from '../../data/sensors.ts'
import type { SensorSelection } from '../../types/domain.ts'

const PLATFORMS = [
  {
    name: 'Terra',
    sensor: 'MODIS',
    resolution: '~1 km',
    confidence: 'Integer 0–100',
    note: 'Morning and night observations in this archive.',
  },
  {
    name: 'Aqua',
    sensor: 'MODIS',
    resolution: '~1 km',
    confidence: 'Integer 0–100',
    note: 'Early-afternoon and night observations. Same confidence scale as Terra.',
  },
  {
    name: 'Suomi-NPP',
    sensor: 'VIIRS',
    resolution: '375 m',
    confidence: 'low, nominal, high',
    note: '375 m product. July 2024 includes documented gaps in the local extract.',
  },
  {
    name: 'NOAA-20',
    sensor: 'VIIRS',
    resolution: '375 m',
    confidence: 'low, nominal, high',
    note: '375 m product. Samples the same regions at a different time from S-NPP.',
  },
  {
    name: 'NOAA-21',
    sensor: 'VIIRS',
    resolution: '375 m',
    confidence: 'low, nominal, high',
    note: '375 m product. A different overpass from NOAA-20 and S-NPP.',
  },
] as const

function logPosition(value: number): number {
  const min = Math.log10(0.5)
  const max = Math.log10(12000)
  return Math.min(1, Math.max(0, (Math.log10(value) - min) / (max - min)))
}

export default function ComparisonScreen() {
  const [sensors, setSensors] = useState<SensorSelection>(ALL_SENSORS_ON)
  const [period, setPeriod] = useState<'month' | 'july7'>('month')
  const satellites = useMemo(() => selectedSatellites(sensors), [sensors])
  const portraits = portraitsFor(period, satellites)
  const maxRows = portraits.reduce((peak, portrait) => Math.max(peak, portrait.deliveredRows), 0)

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex max-w-[1360px] flex-col gap-4 p-4 lg:p-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold tracking-[0.16em] text-cyan uppercase">Sensor comparison</p>
            <h2 className="text-xl font-semibold text-paper">MODIS and VIIRS</h2>
            <p className="mt-1 max-w-2xl text-sm text-mist">
              Different instruments, pixel sizes, and confidence scales. Delivered-row counts are not unique fires and are not a ranking of sensitivity.
            </p>
          </div>
          <Badge tone="archive">FIRMS July 2024</Badge>
        </header>

        <section className="grid gap-4 lg:grid-cols-[1fr_280px]">
          <div className="flex flex-wrap items-center gap-2">
            <PeriodButton pressed={period === 'month'} onClick={() => setPeriod('month')}>
              Full July 2024
            </PeriodButton>
            <PeriodButton pressed={period === 'july7'} onClick={() => setPeriod('july7')}>
              7 July audit
            </PeriodButton>
          </div>
          <SensorToggles value={sensors} onChange={setSensors} />
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <PixelFrame
            title="MODIS"
            detail="About 1 km"
            columns={3}
            cells={9}
            tone="ember"
            caption="Nine 1 km samples fill this 3 km frame."
          />
          <PixelFrame
            title="VIIRS"
            detail="About 375 m"
            columns={8}
            cells={64}
            tone="cyan"
            caption="Sixty-four 375 m samples fill the same 3 km frame. 8 × 375 m = 3 km."
          />
        </section>
        <p className="text-xs leading-relaxed text-muted">{SCAN_NOTE} The grids are a nadir schematic, not a scan-angle footprint.</p>

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {PLATFORMS.map((platform) => (
            <article key={platform.name} className="rounded-lg border border-line bg-panel p-3">
              <p className="text-sm font-semibold text-paper">{platform.name}</p>
              <p className="text-xs text-cyan">{platform.sensor} · {platform.resolution}</p>
              <p className="mt-2 text-xs leading-relaxed text-mist">{platform.note}</p>
              <p className="mt-2 text-[11px] text-amber">Confidence: {platform.confidence}</p>
            </article>
          ))}
        </section>

        <section className="rounded-lg border border-line bg-panel p-4">
          <h3 className="text-sm font-medium text-paper">Delivered rows</h3>
          <p className="mt-1 text-xs text-mist">
            {period === 'month' ? '1–31 July 2024.' : '7 July 2024 only.'} Adding sensors does not count fires. One burning area can produce many pixels and repeated overpasses.
          </p>
          {portraits.length === 0 ? (
            <p className="mt-4 text-sm text-mist">Turn on a sensor to compare archives.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {portraits.map((portrait) => (
                <li key={portrait.satellite}>
                  <div className="mb-1 flex items-baseline justify-between gap-3 text-xs">
                    <span style={{ color: SATELLITE_COLOR[portrait.satellite] }}>{portrait.satellite}</span>
                    <span className="text-paper tabular-nums">{formatCount(portrait.deliveredRows)}</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-ink">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${maxRows > 0 ? (portrait.deliveredRows / maxRows) * 100 : 0}%`,
                        background: SATELLITE_COLOR[portrait.satellite],
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-lg border border-line bg-panel p-4">
          <h3 className="text-sm font-medium text-paper">FRP markers</h3>
          <p className="mt-1 text-xs text-mist">
            Log scale from 0.5 MW to 12,000 MW. Ticks are stored-value summaries, not a histogram and not fire size.
          </p>
          <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-mist">
            <span>Median</span>
            <span>P95</span>
            <span>P99</span>
            <span>Maximum</span>
          </div>
          <ul className="mt-4 space-y-4">
            {portraits.map((portrait) => (
              <li key={portrait.satellite}>
                <div className="mb-1 flex justify-between text-xs">
                  <span style={{ color: SATELLITE_COLOR[portrait.satellite] }}>{portrait.satellite}</span>
                  <span className="text-muted tabular-nums">
                    median {formatMw(portrait.frp.median)} · max {formatMw(portrait.frp.max)} MW
                  </span>
                </div>
                <FrpTrack portrait={portrait} />
              </li>
            ))}
          </ul>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-line bg-panel p-4">
            <h3 className="text-sm font-medium text-paper">MODIS confidence</h3>
            <p className="mt-1 text-xs text-mist">An integer from 0 through 100. It is not converted into the VIIRS flags.</p>
            <ul className="mt-4 space-y-4">
              {portraits.filter((portrait) => portrait.confidence.kind === 'modis').map((portrait) => {
                const confidence = portrait.confidence
                if (confidence.kind !== 'modis') return null
                return (
                  <li key={portrait.satellite}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="text-paper">{portrait.satellite}</span>
                      <span className="text-mist">median {confidence.median}</span>
                    </div>
                    <div className="relative h-2 rounded-full bg-gradient-to-r from-[#3a4a5c] via-amber to-ember">
                      <span
                        className="absolute top-1/2 size-3 -translate-y-1/2 rounded-full border-2 border-ink bg-paper"
                        style={{ left: `${confidence.median}%` }}
                      />
                    </div>
                    <p className="mt-1 text-[11px] text-muted">
                      {confidence.zeros === null
                        ? 'The 0 and 100 counts for this single day are not repeated on this screen.'
                        : `${formatCount(confidence.zeros)} rows at 0 · ${formatCount(confidence.hundreds ?? 0)} rows at 100`}
                    </p>
                  </li>
                )
              })}
            </ul>
          </div>
          <div className="rounded-lg border border-line bg-panel p-4">
            <h3 className="text-sm font-medium text-paper">VIIRS confidence</h3>
            <p className="mt-1 text-xs text-mist">Stored flags l, n, and h: low, nominal, and high. Not a 0–100 score.</p>
            <ul className="mt-4 space-y-4">
              {portraits.filter((portrait) => portrait.confidence.kind === 'viirs').map((portrait) => {
                const confidence = portrait.confidence
                if (confidence.kind !== 'viirs') return null
                const total = confidence.low + confidence.nominal + confidence.high
                return (
                  <li key={portrait.satellite}>
                    <p className="mb-1 text-xs text-paper">{portrait.satellite}</p>
                    <div className="flex h-3 overflow-hidden rounded-full">
                      <span className="bg-[#6d7f93]" style={{ width: `${(confidence.low / total) * 100}%` }} />
                      <span className="bg-cyan" style={{ width: `${(confidence.nominal / total) * 100}%` }} />
                      <span className="bg-[#c4b5fd]" style={{ width: `${(confidence.high / total) * 100}%` }} />
                    </div>
                    <p className="mt-1 text-[11px] text-muted">
                      Low {formatCount(confidence.low)} · Nominal {formatCount(confidence.nominal)} · High {formatCount(confidence.high)}
                    </p>
                  </li>
                )
              })}
            </ul>
            <div className="mt-3 flex gap-3 text-[11px] text-mist">
              <span className="flex items-center gap-1"><span className="size-2 rounded-sm bg-[#6d7f93]" /> Low</span>
              <span className="flex items-center gap-1"><span className="size-2 rounded-sm bg-cyan" /> Nominal</span>
              <span className="flex items-center gap-1"><span className="size-2 rounded-sm bg-[#c4b5fd]" /> High</span>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-line bg-panel p-4">
          <h3 className="text-sm font-medium text-paper">Day and night flags</h3>
          <p className="mt-1 text-xs text-mist">The archive day/night flag. It is not recomputed from local solar time.</p>
          <ul className="mt-4 space-y-3">
            {portraits.map((portrait) => {
              const total = portrait.day + portrait.night
              return (
                <li key={portrait.satellite}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-paper">{portrait.satellite}</span>
                    <span className="text-muted tabular-nums">
                      Day {formatCount(portrait.day)} · Night {formatCount(portrait.night)}
                    </span>
                  </div>
                  <div className="flex h-2.5 overflow-hidden rounded-full bg-ink">
                    <span className="bg-amber" style={{ width: `${(portrait.day / total) * 100}%` }} />
                    <span className="bg-[#35506a]" style={{ width: `${(portrait.night / total) * 100}%` }} />
                  </div>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="rounded-lg border border-amber/40 bg-amber/10 p-4">
          <h3 className="text-sm font-semibold tracking-wide text-amber uppercase">Scientific limitations</h3>
          <ul className="mt-3 space-y-2 text-sm leading-relaxed text-paper">
            <li>MODIS and VIIRS have different spatial resolutions and detection characteristics. Row counts are not a comparison of sensitivity.</li>
            <li>Repeat detections are not unique fires. A pixel, a repeat overpass, and a neighboring pixel can all describe one burning area.</li>
            <li>MODIS confidence is an integer from 0 through 100. VIIRS confidence is the flag l, n, or h. The scales are not interchangeable.</li>
            <li>A date with no delivered rows, and a date whose file is missing, are not zero fire detections.</li>
            <li>FRP is stored fire radiative power in megawatts. It is not fire size and it is not total fire energy.</li>
            <li>One month cannot establish a harmonization factor. No coefficient is calculated here.</li>
            <li>Processing-stream provenance for these files remains unresolved.</li>
          </ul>
          <p className="mt-3 text-[11px] text-mist">{ARCHIVE_CITATION}</p>
        </section>
      </div>
    </div>
  )
}

function PeriodButton({
  pressed,
  onClick,
  children,
}: {
  pressed: boolean
  onClick: () => void
  children: string
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`rounded-md border px-3 py-1.5 text-sm ${
        pressed ? 'border-cyan/50 bg-cyan/10 text-paper' : 'border-line bg-ink text-mist'
      }`}
    >
      {children}
    </button>
  )
}

function PixelFrame({
  title,
  detail,
  columns,
  cells,
  tone,
  caption,
}: {
  title: string
  detail: string
  columns: number
  cells: number
  tone: 'ember' | 'cyan'
  caption: string
}) {
  const fill = tone === 'ember' ? 'bg-ember/30 border-ember/50' : 'bg-cyan/25 border-cyan/40'
  return (
    <figure className="rounded-lg border border-line bg-panel p-4">
      <div className="flex items-baseline justify-between">
        <figcaption className="text-sm font-medium text-paper">{title}</figcaption>
        <span className="text-xs text-cyan">{detail}</span>
      </div>
      <div
        className="mx-auto mt-3 grid aspect-square w-full max-w-[280px] gap-px"
        style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: cells }, (_, index) => (
          <span key={index} className={`border ${fill}`} />
        ))}
      </div>
      <p className="mt-3 text-xs text-mist">{caption}</p>
    </figure>
  )
}

function FrpTrack({ portrait }: { portrait: SatellitePortrait }) {
  const marks = [
    { label: 'median', value: portrait.frp.median },
    { label: 'p95', value: portrait.frp.p95 },
    { label: 'p99', value: portrait.frp.p99 },
    { label: 'max', value: portrait.frp.max },
  ]
  return (
    <div className="relative h-7">
      <div className="absolute top-3 right-0 left-0 h-px bg-line" />
      {marks.map((mark) => (
        <span
          key={mark.label}
          className="absolute top-1.5 flex -translate-x-1/2 flex-col items-center"
          style={{ left: `${logPosition(mark.value) * 100}%` }}
        >
          <span className="size-2.5 rounded-full" style={{ background: SATELLITE_COLOR[portrait.satellite] }} />
          <span className="sr-only">{mark.label} {formatMw(mark.value)} MW</span>
        </span>
      ))}
    </div>
  )
}
