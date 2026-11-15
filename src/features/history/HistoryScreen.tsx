import { useMemo, useState } from 'react'
import { Download } from 'lucide-react'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Card } from '../../components/ui/Card.tsx'
import { TrendChart } from '../../components/charts/TrendChart.tsx'
import { SensorToggles } from '../../components/filters/SensorToggles.tsx'
import { ARCHIVE_CITATION, MONTH_PORTRAITS } from '../../data/archiveJuly2024.ts'
import { buildArchiveCsv, downloadTextFile } from '../../data/csv.ts'
import { formatCount, formatMw } from '../../data/format.ts'
import {
  calendarMonth,
  coverageNotes,
  portraitsFor,
  rollupSatellite,
  trendSeries,
} from '../../data/queries.ts'
import { ALL_SENSORS_ON, SATELLITE_COLOR, selectedSatellites } from '../../data/sensors.ts'
import type { DateRange, SensorSelection } from '../../types/domain.ts'
import {
  eachIsoDate,
  isOrderedDateRange,
  monthBounds,
  MONTH_NAMES,
  shiftMonth,
} from '../filters/dateRange.ts'
import { ActivityCalendar } from './ActivityCalendar.tsx'

const FULL_JULY: DateRange = { start: '2024-07-01', end: '2024-07-31' }
const EARLY_JULY: DateRange = { start: '2024-07-01', end: '2024-07-15' }
const LATE_JULY: DateRange = { start: '2024-07-16', end: '2024-07-31' }

export default function HistoryScreen() {
  const [sensors, setSensors] = useState<SensorSelection>(ALL_SENSORS_ON)
  const [range, setRange] = useState<DateRange>(FULL_JULY)
  const [cursor, setCursor] = useState({ year: 2024, month: 7 })
  const satellites = useMemo(() => selectedSatellites(sensors), [sensors])
  const ordered = isOrderedDateRange(range)
  const span = ordered ? eachIsoDate(range) : { dates: [], truncated: false }
  const series = useMemo(() => trendSeries(span.dates, satellites), [span.dates, satellites])
  const cells = useMemo(
    () => calendarMonth(cursor.year, cursor.month, satellites, range.start, range.end),
    [cursor, satellites, range],
  )
  const notes = useMemo(() => coverageNotes(span.dates, satellites), [span.dates, satellites])
  const rollups = satellites.map((satellite) => ({
    satellite,
    ...rollupSatellite(span.dates, satellite),
  }))
  const delivered = rollups.reduce((sum, row) => sum + row.delivered, 0)
  const gapDays = rollups.reduce((sum, row) => sum + row.gapDays, 0)
  const outsideDays = rollups.reduce((sum, row) => sum + row.outsideDays, 0)
  const earlyDates = eachIsoDate(EARLY_JULY).dates
  const lateDates = eachIsoDate(LATE_JULY).dates
  const frp = portraitsFor('month', satellites)

  function updateRange(key: keyof DateRange, value: string) {
    setRange((current) => ({ ...current, [key]: value }))
  }

  function exportCsv() {
    if (!ordered || span.dates.length === 0) return
    downloadTextFile(
      'firelens-july2024-delivered-rows.csv',
      buildArchiveCsv(span.dates, satellites),
      'text/csv;charset=utf-8',
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex max-w-[1360px] flex-col gap-4 p-4 lg:p-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold tracking-[0.16em] text-cyan uppercase">Verified archive</p>
            <h2 className="text-xl font-semibold text-paper">Historical fire explorer</h2>
            <p className="mt-1 max-w-2xl text-sm text-mist">
              July 2024 delivered rows from the tracked FIRMS extracts. Counts are archive rows, not unique fires.
              Dates with no rows, and months with no file, stay blank.
            </p>
          </div>
          <Badge tone="archive">FIRMS July 2024</Badge>
        </header>

        <section className="grid gap-4 rounded-lg border border-line bg-panel p-4 lg:grid-cols-[1fr_280px]">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-mist">
              Start
              <input
                type="date"
                value={range.start}
                onChange={(event) => updateRange('start', event.target.value)}
                className="mt-1 w-full rounded-md border border-line bg-ink px-2 py-2 text-sm text-paper"
              />
            </label>
            <label className="text-xs text-mist">
              End
              <input
                type="date"
                value={range.end}
                onChange={(event) => updateRange('end', event.target.value)}
                className="mt-1 w-full rounded-md border border-line bg-ink px-2 py-2 text-sm text-paper"
              />
            </label>
            {ordered ? null : (
              <p role="alert" className="text-xs text-[#ffc4ca] sm:col-span-2">
                End date must be on or after the start date.
              </p>
            )}
            {span.truncated ? (
              <p className="text-xs text-amber sm:col-span-2">
                The chart keeps the first 120 days of this range.
              </p>
            ) : null}
          </div>
          <div>
            <p className="mb-1.5 text-xs font-medium text-paper">Sensors</p>
            <SensorToggles value={sensors} onChange={setSensors} />
            <p className="mt-2 text-[11px] text-muted">MODIS stays split into Terra and Aqua.</p>
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <ActivityCalendar
            year={cursor.year}
            month={cursor.month}
            cells={cells}
            onPrevious={() => setCursor((current) => shiftMonth(current.year, current.month, -1))}
            onNext={() => setCursor((current) => shiftMonth(current.year, current.month, 1))}
            onSelectDay={(date) => setRange({ start: date, end: date })}
            onUseMonth={() => setRange(monthBounds(cursor.year, cursor.month))}
          />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <Card title="Delivered rows in range">
              <p className="text-3xl font-semibold text-paper tabular-nums">{formatCount(delivered)}</p>
              <p className="mt-1 text-xs text-mist">Sum of rows the selected satellites actually delivered. Not a fire count.</p>
            </Card>
            <Card title="Missing observations">
              <p className="text-sm text-paper">{gapDays} satellite-days with no rows delivered</p>
              <p className="mt-1 text-sm text-paper">{outsideDays} satellite-days with no archive loaded</p>
              <p className="mt-2 text-xs text-amber">Neither figure is drawn as zero detections.</p>
            </Card>
          </div>
        </div>

        <Card title="Delivered-row trend">
          <div className="mb-3 flex flex-wrap gap-3">
            {series.map((item) => (
              <span key={item.id} className="flex items-center gap-1.5 text-xs text-mist">
                <span className="h-0.5 w-4" style={{ background: item.color }} />
                {item.label}
              </span>
            ))}
            <span className="flex items-center gap-1.5 text-xs text-mist">
              <span className="size-2 rounded-full border border-amber" />
              No rows delivered
            </span>
          </div>
          {satellites.length === 0 ? (
            <p className="text-sm text-mist">Turn on a sensor to draw the trend.</p>
          ) : (
            <TrendChart dates={span.dates} series={series} />
          )}
          <p className="mt-2 text-xs text-muted">
            Hollow marks sit on dates the file covered with zero delivered rows. Stretches outside July 2024 are omitted rather than plotted at zero.
          </p>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Early July vs late July">
            <p className="mb-3 text-xs text-mist">
              1–15 July against 16–31 July. S-NPP gaps in the second half are incomplete delivery, not a fall to zero fires.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-muted">
                  <tr>
                    <th className="pb-2 font-medium">Satellite</th>
                    <th className="pb-2 font-medium">1–15 Jul</th>
                    <th className="pb-2 font-medium">16–31 Jul</th>
                    <th className="pb-2 font-medium">Gap days</th>
                  </tr>
                </thead>
                <tbody>
                  {satellites.map((satellite) => {
                    const early = rollupSatellite(earlyDates, satellite)
                    const late = rollupSatellite(lateDates, satellite)
                    return (
                      <tr key={satellite} className="border-t border-line">
                        <td className="py-1.5" style={{ color: SATELLITE_COLOR[satellite] }}>{satellite}</td>
                        <td className="py-1.5 tabular-nums text-paper">{formatCount(early.delivered)}</td>
                        <td className="py-1.5 tabular-nums text-paper">{formatCount(late.delivered)}</td>
                        <td className="py-1.5 tabular-nums text-mist">{early.gapDays + late.gapDays}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="FRP for the full month">
            <p className="mb-3 text-xs text-mist">
              Medians and maxima from the July archive. They do not change with the date range, because daily FRP was not published in the tracked reports.
            </p>
            <ul className="space-y-2">
              {frp.map((portrait) => (
                <li key={portrait.satellite} className="flex items-baseline justify-between gap-3 text-sm">
                  <span style={{ color: SATELLITE_COLOR[portrait.satellite] }}>{portrait.satellite}</span>
                  <span className="text-paper tabular-nums">
                    median {formatMw(portrait.frp.median)} MW
                    <span className="ml-2 text-xs text-mist">max {formatMw(portrait.frp.max)}</span>
                  </span>
                </li>
              ))}
            </ul>
            {MONTH_PORTRAITS.length > frp.length ? null : (
              <p className="mt-3 text-[11px] text-muted">All five satellites are included.</p>
            )}
          </Card>
        </div>

        <Card title="Coverage notes">
          {notes.length === 0 ? (
            <p className="text-sm text-mist">No coverage notes for the selected satellites and dates.</p>
          ) : (
            <ul className="max-h-56 space-y-2 overflow-y-auto pr-1">
              {notes.map((note) => (
                <li key={`${note.date}-${note.satellite}`} className="text-xs leading-relaxed text-mist">
                  <span className="text-paper">{note.date} · {note.satellite}. </span>
                  {note.note}
                </li>
              ))}
            </ul>
          )}
          {cursor.year !== 2024 || cursor.month !== 7 ? (
            <p className="mt-3 text-xs text-amber">
              {MONTH_NAMES[cursor.month - 1]} {cursor.year} has no loaded archive. The calendar does not fill those days with zeros.
            </p>
          ) : null}
        </Card>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-panel px-4 py-3">
          <p className="max-w-3xl text-[11px] leading-relaxed text-muted">{ARCHIVE_CITATION}</p>
          <Button icon={Download} disabled={!ordered || span.dates.length === 0 || satellites.length === 0} onClick={exportCsv}>
            Export CSV
          </Button>
        </div>
      </div>
    </div>
  )
}
