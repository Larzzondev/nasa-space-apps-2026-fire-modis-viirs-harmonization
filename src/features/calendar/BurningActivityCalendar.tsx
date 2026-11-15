import { CalendarDays } from 'lucide-react'
import type { DateRange } from '../../types/domain.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Card } from '../../components/ui/Card.tsx'
import { formatIsoDate, isOrderedDateRange, parseIsoDate } from '../filters/dateRange.ts'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const
const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const

interface BurningActivityCalendarProps {
  dateRange: DateRange
}

export function BurningActivityCalendar({ dateRange }: BurningActivityCalendarProps) {
  const start = parseIsoDate(dateRange.start)
  const rangeIsOrdered = isOrderedDateRange(dateRange)

  return (
    <Card title="Burning activity" icon={CalendarDays}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone="placeholder">Placeholder</Badge>
        <p className="text-xs text-mist">Daily activity appears when detections are available.</p>
      </div>
      {start ? (
        <MonthGrid
          year={start.year}
          month={start.month}
          dateRange={dateRange}
          highlightRange={rangeIsOrdered}
        />
      ) : (
        <p className="text-sm text-mist">Choose a valid start date to show the month.</p>
      )}
      {rangeIsOrdered ? null : (
        <p className="mt-3 text-xs text-[#f3c7a4]">
          Days stay unmarked until the end date is on or after the start date.
        </p>
      )}
    </Card>
  )
}

interface MonthGridProps {
  year: number
  month: number
  dateRange: DateRange
  highlightRange: boolean
}

function MonthGrid({ year, month, dateRange, highlightRange }: MonthGridProps) {
  const weeks = buildMonthWeeks(year, month)
  const monthLabel = `${MONTH_NAMES[month - 1]} ${year}`

  return (
    <div>
      <p className="mb-2 text-sm text-paper">{monthLabel}</p>
      <table className="w-full border-separate border-spacing-1 text-center text-xs">
        <caption className="sr-only">
          Placeholder calendar for {monthLabel}. Highlighted days are inside the selected range. No
          burning activity is shown.
        </caption>
        <thead>
          <tr>
            {WEEKDAYS.map((weekday) => (
              <th key={weekday} scope="col" className="pb-1 font-medium text-mist">
                {weekday}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((week, weekIndex) => (
            <tr key={`${monthLabel}-week-${weekIndex}`}>
              {week.map((day, dayIndex) => {
                if (day === null) {
                  return <td key={`${weekIndex}-${dayIndex}`} className="h-8" />
                }
                const iso = formatIsoDate(year, month, day)
                const inRange =
                  highlightRange && iso >= dateRange.start && iso <= dateRange.end
                return (
                  <td
                    key={iso}
                    className={`h-8 rounded tabular-nums ${
                      inRange
                        ? 'bg-ember/15 text-paper ring-1 ring-ember/50'
                        : 'text-mist'
                    }`}
                    aria-label={`${monthLabel} ${day}, no activity recorded`}
                  >
                    {day}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-mist">
        {highlightRange
          ? 'Outlined days sit inside the selected range. The cells do not show detections.'
          : 'The cells do not show detections.'}
      </p>
    </div>
  )
}

function buildMonthWeeks(year: number, month: number): Array<Array<number | null>> {
  const firstWeekday = new Date(year, month - 1, 1).getDay()
  const leadingBlanks = (firstWeekday + 6) % 7
  const daysInMonth = new Date(year, month, 0).getDate()
  const cells: Array<number | null> = []

  for (let index = 0; index < leadingBlanks; index += 1) cells.push(null)
  for (let day = 1; day <= daysInMonth; day += 1) cells.push(day)
  while (cells.length % 7 !== 0) cells.push(null)

  const weeks: Array<Array<number | null>> = []
  for (let index = 0; index < cells.length; index += 7) {
    weeks.push(cells.slice(index, index + 7))
  }
  return weeks
}
