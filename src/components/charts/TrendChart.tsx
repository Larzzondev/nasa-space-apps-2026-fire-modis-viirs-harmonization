import type { TrendSeries } from '../../data/queries.ts'

interface TrendChartProps {
  dates: readonly string[]
  series: readonly TrendSeries[]
}

const WIDTH = 680
const HEIGHT = 248
const PAD = { left: 52, right: 12, top: 16, bottom: 32 }

export function TrendChart({ dates, series }: TrendChartProps) {
  const values = series.flatMap((item) =>
    item.points.flatMap((point) => (point.kind === 'rows' && point.value !== null ? [point.value] : [])),
  )
  if (dates.length === 0 || values.length === 0) {
    return (
      <p className="text-sm text-mist">
        No delivered rows in this range. Empty dates stay off the line instead of being drawn as zero.
      </p>
    )
  }

  const max = Math.max(...values)
  const plotWidth = WIDTH - PAD.left - PAD.right
  const plotHeight = HEIGHT - PAD.top - PAD.bottom
  const xAt = (index: number) =>
    PAD.left + (dates.length === 1 ? plotWidth / 2 : (index / (dates.length - 1)) * plotWidth)
  const yAt = (value: number) => PAD.top + (1 - value / max) * plotHeight

  const ticks = [0, 0.5, 1].map((fraction) => Math.round(max * fraction))
  const labelStep = dates.length > 16 ? 5 : dates.length > 8 ? 2 : 1

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label="Daily delivered-row counts. Breaks are dates with no rows or no loaded archive, not zero detections."
      className="h-auto w-full"
    >
      {ticks.map((tick) => {
        const y = yAt(tick)
        return (
          <g key={tick}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y} y2={y} stroke="#243140" />
            <text x={PAD.left - 8} y={y + 4} textAnchor="end" fill="#93a4b8" fontSize="11">
              {tick >= 1000 ? `${Math.round(tick / 1000)}k` : tick}
            </text>
          </g>
        )
      })}
      {series.map((item) => {
        const paths: string[] = []
        let current = ''
        item.points.forEach((point, index) => {
          if (point.kind !== 'rows' || point.value === null) {
            if (current) paths.push(current)
            current = ''
            return
          }
          const command = current ? 'L' : 'M'
          current += `${command}${xAt(index).toFixed(1)},${yAt(point.value).toFixed(1)} `
        })
        if (current) paths.push(current)
        return (
          <g key={item.id}>
            {paths.map((path) => (
              <path key={path} d={path} fill="none" stroke={item.color} strokeWidth="2" />
            ))}
            {item.points.map((point, index) => {
              if (point.kind === 'rows' && point.value !== null && dates.length < 40) {
                return (
                  <circle
                    key={`${item.id}-${dates[index]}`}
                    cx={xAt(index)}
                    cy={yAt(point.value)}
                    r="2.4"
                    fill={item.color}
                  />
                )
              }
              if (point.kind === 'no-rows') {
                return (
                  <circle
                    key={`${item.id}-gap-${dates[index]}`}
                    cx={xAt(index)}
                    cy={HEIGHT - PAD.bottom}
                    r="3"
                    fill="none"
                    stroke="#f5b942"
                    strokeWidth="1.4"
                  />
                )
              }
              return null
            })}
          </g>
        )
      })}
      {dates.map((date, index) => {
        if (index % labelStep !== 0 && index !== dates.length - 1) return null
        return (
          <text
            key={date}
            x={xAt(index)}
            y={HEIGHT - 8}
            textAnchor="middle"
            fill="#93a4b8"
            fontSize="11"
          >
            {date.slice(5)}
          </text>
        )
      })}
    </svg>
  )
}
