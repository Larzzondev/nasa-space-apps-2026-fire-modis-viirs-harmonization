import { ChevronLeft, ChevronRight } from 'lucide-react'
import { formatCompact } from '../../data/format.ts'
import type { CalendarCell } from '../../data/queries.ts'
import {
  buildMonthWeeks,
  formatIsoDate,
  MONTH_NAMES,
  WEEKDAYS,
} from '../filters/dateRange.ts'

interface ActivityCalendarProps {
  year: number
  month: number
  cells: readonly CalendarCell[]
  onPrevious: () => void
  onNext: () => void
  onSelectDay: (date: string) => void
  onUseMonth: () => void
}

function heatColor(value: number, max: number): string {
  const t = max > 0 ? Math.sqrt(value / max) : 0
  const start = [28, 42, 58]
  const mid = [255, 138, 61]
  const end = [255, 45, 85]
  const channel = (index: number) => {
    if (t < 0.55) {
      const local = t / 0.55
      return Math.round(start[index]! + (mid[index]! - start[index]!) * local)
    }
    const local = (t - 0.55) / 0.45
    return Math.round(mid[index]! + (end[index]! - mid[index]!) * local)
  }
  return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`
}

export function ActivityCalendar({
  year,
  month,
  cells,
  onPrevious,
  onNext,
  onSelectDay,
  onUseMonth,
}: ActivityCalendarProps) {
  const weeks = buildMonthWeeks(year, month)
  const byDay = new Map(cells.map((cell) => [cell.day, cell]))
  const max = cells.reduce((peak, cell) => Math.max(peak, cell.delivered ?? 0), 0)
  const loaded = year === 2024 && month === 7

  return (
    <section className="rounded-lg border border-line bg-panel p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-medium text-paper">Monthly activity</h2>
          <p className="text-xs text-mist">
            {loaded
              ? 'Color sums satellites that delivered rows. Amber dot: a satellite has no rows. Cyan dot: a partial day. A hatch means every selected satellite is missing. None of these are zero fires.'
              : 'No FIRMS archive is loaded for this month. Blank cells are not zero detections.'}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Previous month"
            onClick={onPrevious}
            className="rounded-md border border-line bg-ink p-1.5 text-paper hover:bg-panel-2"
          >
            <ChevronLeft className="size-4" />
          </button>
          <p className="min-w-32 text-center text-sm text-paper">
            {MONTH_NAMES[month - 1]} {year}
          </p>
          <button
            type="button"
            aria-label="Next month"
            onClick={onNext}
            className="rounded-md border border-line bg-ink p-1.5 text-paper hover:bg-panel-2"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
      </div>

      <table className="mt-3 w-full border-separate border-spacing-1 text-center">
        <caption className="sr-only">
          {MONTH_NAMES[month - 1]} {year} delivered-row calendar. Missing archives are not shown as zero.
        </caption>
        <thead>
          <tr>
            {WEEKDAYS.map((weekday) => (
              <th key={weekday} scope="col" className="pb-1 text-[11px] font-medium text-muted">
                {weekday}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((week, weekIndex) => (
            <tr key={`${year}-${month}-week-${weekIndex}`}>
              {week.map((day, dayIndex) => {
                if (day === null) return <td key={`${weekIndex}-${dayIndex}`} className="h-12" />
                const cell = byDay.get(day)
                const date = formatIsoDate(year, month, day)
                const allGaps = cell ? !cell.outside && cell.delivered === null && cell.gaps.length > 0 : false
                const gapNote = cell?.gaps.length ? `, gaps: ${cell.gaps.join(', ')}` : ''
                const partialNote = cell?.partial ? ', partial day' : ''
                const label = cell?.outside
                  ? `${date}, no archive loaded`
                  : allGaps
                    ? `${date}, no rows delivered. Not zero fire activity.`
                    : `${date}, ${cell?.delivered ?? 0} delivered rows${gapNote}${partialNote}`
                const background = cell?.delivered != null && !allGaps
                  ? heatColor(cell.delivered, max)
                  : undefined
                return (
                  <td key={date} className="p-0">
                    <button
                      type="button"
                      aria-label={label}
                      onClick={() => onSelectDay(date)}
                      className={`relative flex h-12 w-full flex-col items-center justify-center rounded-md text-[11px] ${
                        allGaps || cell?.outside ? 'gap-hatch text-mist' : 'text-paper'
                      } ${cell?.inRange ? 'ring-1 ring-paper/50' : 'opacity-70'}`}
                      style={background ? { background } : undefined}
                    >
                      {cell && cell.gaps.length > 0 ? (
                        <span className="absolute top-1 right-1 size-1.5 rounded-full bg-amber" />
                      ) : null}
                      {cell?.partial ? (
                        <span className="absolute top-1 left-1 size-1.5 rounded-full bg-cyan" />
                      ) : null}
                      <span className="leading-none">{day}</span>
                      <span className="mt-0.5 leading-none tabular-nums text-[10px] opacity-90">
                        {cell?.outside ? '—' : allGaps ? 'Gap' : cell?.delivered != null ? formatCompact(cell.delivered) : '—'}
                      </span>
                    </button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] text-muted">Outlined days are inside the chart range. Select a day to focus it.</p>
        <button
          type="button"
          onClick={onUseMonth}
          className="rounded-md border border-line bg-ink px-2 py-1 text-xs text-paper hover:bg-panel-2"
        >
          Chart this month
        </button>
      </div>
    </section>
  )
}
