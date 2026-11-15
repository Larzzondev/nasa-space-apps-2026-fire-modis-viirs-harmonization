import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { DayNightToggle, SensorToggles } from '../../components/filters/SensorToggles.tsx'
import { AUDIT_DATE, JULY7_PORTRAITS } from '../../data/archiveJuly2024.ts'
import { DEMO_HOTSPOTS, DEMO_SAMPLE_END, DEMO_SAMPLE_START } from '../../data/demoHotspots.ts'
import { formatAcqTime, formatConfidence, formatCount, formatLatitude, formatLongitude, formatMw } from '../../data/format.ts'
import { FRP_BINS } from '../../data/hotspotStyle.ts'
import { archiveDay, filterHotspots, summarizeHotspots } from '../../data/queries.ts'
import { ALL_SENSORS_ON, SATELLITE_COLOR, selectedSatellites, sensorMeta } from '../../data/sensors.ts'
import { parseIsoDate, toLocalIsoDate } from '../filters/dateRange.ts'
import type { DayNight, SensorSelection } from '../../types/domain.ts'
import { globeBasemapLabel } from '../../config/cesium.ts'
import { CesiumGlobe } from './CesiumGlobe.tsx'

function shiftJulyDay(date: string, delta: number): string {
  const parsed = parseIsoDate(date)
  if (!parsed) return AUDIT_DATE
  const next = new Date(parsed.year, parsed.month - 1, parsed.day + delta)
  const iso = toLocalIsoDate(next)
  if (iso < '2024-07-01' || iso > '2024-07-31') return date
  return iso
}

function Legend() {
  return (
    <div className="rounded-lg border border-line bg-panel/90 px-3 py-2 shadow-[0_16px_40px_rgba(0,0,0,0.28)] backdrop-blur-md">
      <p className="text-[10px] font-semibold tracking-[0.14em] text-mist uppercase">Legend</p>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
        {FRP_BINS.map((bin) => (
          <span key={bin.label} className="flex items-center gap-1.5 text-[11px] text-paper">
            <span className="size-2.5 rounded-full" style={{ background: bin.color }} />
            {bin.label}
          </span>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
        {Object.entries(SATELLITE_COLOR).map(([platform, color]) => (
          <span key={platform} className="flex items-center gap-1.5 text-[11px] text-mist">
            <span className="size-2.5 rounded-full border-2 bg-transparent" style={{ borderColor: color }} />
            {platform}
          </span>
        ))}
      </div>
      <p className="mt-2 text-[11px] text-muted">
        Marker color and size follow demo FRP. FRP is radiative power in megawatts, not fire size. The ring is the platform.
      </p>
      <p className="mt-1 text-[11px] text-cyan">{globeBasemapLabel()}</p>
    </div>
  )
}

export default function GlobeScreen({ active }: { active: boolean }) {
  const [date, setDate] = useState(AUDIT_DATE)
  const [sensors, setSensors] = useState<SensorSelection>(ALL_SENSORS_ON)
  const [dayNight, setDayNight] = useState<'all' | DayNight>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [flyHomeToken, setFlyHomeToken] = useState(0)

  const visible = useMemo(
    () => filterHotspots(DEMO_HOTSPOTS, { date, sensors, dayNight }),
    [date, sensors, dayNight],
  )
  const summary = useMemo(() => summarizeHotspots(visible), [visible])
  const satellites = useMemo(() => selectedSatellites(sensors), [sensors])
  const archive = useMemo(() => archiveDay(date, satellites), [date, satellites])
  const selected = visible.find((hotspot) => hotspot.id === selectedId) ?? null
  const strongest = useMemo(
    () => [...visible].sort((left, right) => right.frpMw - left.frpMw).slice(0, 6),
    [visible],
  )
  const inSample = date >= DEMO_SAMPLE_START && date <= DEMO_SAMPLE_END
  const july7Frp = date === AUDIT_DATE
    ? JULY7_PORTRAITS.filter((portrait) => satellites.includes(portrait.satellite))
    : []

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setSelectedId(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div className="flex h-full min-h-0 flex-col lg:block">
      <div className="relative h-[48vh] shrink-0 lg:absolute lg:inset-0 lg:h-auto">
        <CesiumGlobe
          hotspots={visible}
          selectedId={selected?.id ?? null}
          active={active}
          flyHomeToken={flyHomeToken}
          onSelect={setSelectedId}
        />
        {visible.length === 0 ? (
          <div className="pointer-events-none absolute inset-0 grid place-items-center p-6">
            <div className="max-w-sm rounded-lg border border-line bg-panel/95 px-4 py-3 text-center shadow-lg">
              <p className="text-sm font-medium text-paper">No demo hotspots in this view</p>
              <p className="mt-1 text-xs text-mist">
                {inSample
                  ? 'Turn a sensor back on, or set day/night to All.'
                  : `The interactive sample is ${DEMO_SAMPLE_START} through ${DEMO_SAMPLE_END}. Archive counts for this July day are still in the side panel.`}
              </p>
            </div>
          </div>
        ) : null}
        <div className="pointer-events-none absolute bottom-14 left-[22.5rem] z-10 hidden w-[19rem] xl:block">
          <Legend />
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3 lg:pointer-events-none lg:absolute lg:inset-0 lg:overflow-visible lg:p-0">
        <section className="pointer-events-auto space-y-3 rounded-lg border border-line bg-panel/92 p-3 shadow-[0_16px_40px_rgba(0,0,0,0.28)] backdrop-blur-md lg:absolute lg:top-3 lg:left-3 lg:max-h-[calc(100%-3.75rem)] lg:w-[332px] lg:overflow-y-auto">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[10px] font-semibold tracking-[0.16em] text-mist uppercase">Global fire intelligence</p>
              <h2 className="text-base font-semibold text-paper">Active hotspots</h2>
            </div>
            <Badge tone="demo">Demo data</Badge>
          </div>

          <div>
            <p className="mb-1.5 text-xs font-medium text-paper">Acquisition date</p>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                className="rounded-md border border-line bg-ink p-2 text-paper hover:bg-panel-2"
                aria-label="Previous day"
                onClick={() => setDate((current) => shiftJulyDay(current, -1))}
              >
                <ChevronLeft className="size-4" />
              </button>
              <input
                type="date"
                aria-label="Acquisition date"
                min="2024-07-01"
                max="2024-07-31"
                value={date}
                onChange={(event) => {
                  if (event.target.value) setDate(event.target.value)
                }}
                className="min-w-0 flex-1 rounded-md border border-line bg-ink px-2 py-1.5 text-sm text-paper"
              />
              <button
                type="button"
                className="rounded-md border border-line bg-ink p-2 text-paper hover:bg-panel-2"
                aria-label="Next day"
                onClick={() => setDate((current) => shiftJulyDay(current, 1))}
              >
                <ChevronRight className="size-4" />
              </button>
            </div>
            <p className="mt-1.5 text-[11px] text-muted">
              Map points exist for 1–7 July only. They are a bounded synthetic sample, not the archive.
            </p>
          </div>

          <div>
            <p className="mb-1.5 text-xs font-medium text-paper">Sensors</p>
            <SensorToggles value={sensors} onChange={setSensors} />
          </div>

          <div>
            <p className="mb-1.5 text-xs font-medium text-paper">Day / night</p>
            <DayNightToggle value={dayNight} onChange={setDayNight} />
            <p className="mt-1.5 text-[11px] text-muted">Applies to the demo sample only.</p>
          </div>

          <div className="rounded-md border border-amber/30 bg-amber/8 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-medium text-paper">Demo sample</p>
              <Badge tone="demo">Demo data</Badge>
            </div>
            <dl className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <dt className="text-muted">Sample points</dt>
                <dd className="font-semibold text-paper tabular-nums">{formatCount(summary.count)}</dd>
              </div>
              <div>
                <dt className="text-muted">Platforms</dt>
                <dd className="font-semibold text-paper tabular-nums">{summary.byPlatform.length}</dd>
              </div>
              <div>
                <dt className="text-muted">Median FRP</dt>
                <dd className="font-semibold text-paper tabular-nums">
                  {summary.medianFrp === null ? '—' : `${formatMw(summary.medianFrp)} MW`}
                </dd>
              </div>
              <div>
                <dt className="text-muted">Max FRP</dt>
                <dd className="font-semibold text-paper tabular-nums">
                  {summary.maxFrp === null ? '—' : `${formatMw(summary.maxFrp)} MW`}
                </dd>
              </div>
            </dl>
            <p className="mt-2 text-[11px] text-mist">
              Day {formatCount(summary.day)} · Night {formatCount(summary.night)}. These numbers describe the drawn sample.
            </p>
          </div>

          <div className="rounded-md border border-cyan/30 bg-cyan/8 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-medium text-paper">Verified archive</p>
              <Badge tone="archive">FIRMS</Badge>
            </div>
            {archive.kind !== 'archive' ? (
              <p className="mt-2 text-xs text-mist">No July 2024 archive row is loaded for this date.</p>
            ) : (
              <>
                <p className="mt-2 text-lg font-semibold text-paper tabular-nums">
                  {archive.deliveredTotal === null ? 'No rows delivered' : formatCount(archive.deliveredTotal)}
                </p>
                <p className="text-[11px] text-mist">
                  Delivered rows from the selected satellites. Not unique fires, and not the points on the globe.
                </p>
                <ul className="mt-2 space-y-1">
                  {archive.rows.map((row) => (
                    <li key={row.satellite} className="flex items-center justify-between gap-2 text-xs">
                      <span className="text-mist">{row.satellite}</span>
                      <span className="text-paper tabular-nums">
                        {row.deliveredRows === null ? 'No rows delivered' : formatCount(row.deliveredRows)}
                      </span>
                    </li>
                  ))}
                </ul>
                {archive.gapSatellites.length > 0 ? (
                  <p className="mt-2 text-[11px] text-amber">
                    {archive.gapSatellites.join(', ')} delivered no rows. That is not zero fire activity.
                  </p>
                ) : null}
                {july7Frp.length > 0 ? (
                  <div className="mt-2 border-t border-cyan/20 pt-2">
                    <p className="text-[11px] text-cyan">7 July FRP medians, MW</p>
                    <ul className="mt-1 space-y-0.5">
                      {july7Frp.map((portrait) => (
                        <li key={portrait.satellite} className="flex justify-between text-xs">
                          <span className="text-mist">{portrait.satellite}</span>
                          <span className="text-paper tabular-nums">{formatMw(portrait.frp.median)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="mt-2 text-[11px] text-muted">
                    Daily FRP is published in the tracked reports for 7 July. Other dates show counts only.
                  </p>
                )}
              </>
            )}
          </div>

          <Button className="w-full" onClick={() => setFlyHomeToken((token) => token + 1)}>
            World view
          </Button>
          <div className="xl:hidden">
            <Legend />
          </div>
        </section>

        <aside className="pointer-events-auto rounded-lg border border-line bg-panel/92 p-3 shadow-[0_16px_40px_rgba(0,0,0,0.28)] backdrop-blur-md lg:absolute lg:top-3 lg:right-3 lg:max-h-[calc(100%-6.5rem)] lg:w-[340px] lg:overflow-y-auto">
          {selected ? (
            <div>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <Badge tone="demo">Demo data</Badge>
                  <h2 className="mt-2 text-base font-semibold text-paper">{selected.cluster}</h2>
                  <p className="text-xs text-mist">
                    {selected.platform} · {sensorMeta(selected.sensor).label}
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-md border border-line px-2 py-1 text-xs text-mist hover:text-paper"
                  onClick={() => setSelectedId(null)}
                >
                  Close
                </button>
              </div>
              <dl className="mt-3 space-y-2 text-sm">
                <Field label="Latitude" value={formatLatitude(selected.latitude)} />
                <Field label="Longitude" value={formatLongitude(selected.longitude)} />
                <Field label="Satellite" value={selected.platform} />
                <Field label="Acquisition" value={`${selected.date} · ${formatAcqTime(selected.acqTime)}`} />
                <Field label="Brightness" value={`${formatMw(selected.brightnessK)} K`} />
                <Field label="FRP" value={`${formatMw(selected.frpMw)} MW`} />
                <Field label="Confidence" value={formatConfidence(selected.confidence).value} />
                <Field label="Confidence scale" value={formatConfidence(selected.confidence).scale} />
                <Field label="Day / night" value={selected.dayNight === 'D' ? 'Day' : 'Night'} />
              </dl>
              <p className="mt-3 text-[11px] leading-relaxed text-muted">
                Synthetic record for interaction. It is not a NASA observation and it is not one of the archive totals beside it.
              </p>
            </div>
          ) : (
            <div>
              <h2 className="text-sm font-semibold text-paper">Select a hotspot</h2>
              <p className="mt-1 text-xs leading-relaxed text-mist">
                Click a point, or choose one of the strongest demo samples. Escape clears the selection.
              </p>
              <ul className="mt-3 space-y-1.5">
                {strongest.length === 0 ? (
                  <li className="text-xs text-muted">Nothing to select with the current filters.</li>
                ) : strongest.map((hotspot) => (
                  <li key={hotspot.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(hotspot.id)}
                      className="flex w-full items-center justify-between gap-3 rounded-md border border-line bg-ink px-2.5 py-2 text-left hover:border-mist/40"
                    >
                      <span>
                        <span className="block text-xs text-paper">{hotspot.cluster}</span>
                        <span className="block text-[11px] text-mist">{hotspot.platform}</span>
                      </span>
                      <span className="text-xs font-medium text-ember tabular-nums">{formatMw(hotspot.frpMw)} MW</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line/70 pb-1.5">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-right text-xs text-paper">{value}</dd>
    </div>
  )
}
