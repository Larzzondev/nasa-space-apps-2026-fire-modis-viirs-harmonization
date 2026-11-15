import { SENSORS } from '../../data/sensors.ts'
import type { DayNight, SensorSelection } from '../../types/domain.ts'

interface SensorTogglesProps {
  value: SensorSelection
  onChange: (next: SensorSelection) => void
}

export function SensorToggles({ value, onChange }: SensorTogglesProps) {
  return (
    <div className="grid grid-cols-2 gap-1.5">
      {SENSORS.map((sensor) => {
        const pressed = value[sensor.id]
        return (
          <button
            key={sensor.id}
            type="button"
            aria-pressed={pressed}
            onClick={() => onChange({ ...value, [sensor.id]: !pressed })}
            className={`flex items-center gap-2 rounded-md border px-2 py-1.5 text-left text-xs transition ${
              pressed
                ? 'border-line bg-ink text-paper'
                : 'border-transparent bg-transparent text-muted hover:bg-ink/70'
            }`}
          >
            <span
              className="size-2 shrink-0 rounded-full"
              style={{ background: pressed ? sensor.ring : '#3a4a5c' }}
            />
            {sensor.short}
          </button>
        )
      })}
    </div>
  )
}

interface DayNightToggleProps {
  value: 'all' | DayNight
  onChange: (next: 'all' | DayNight) => void
}

const DAY_NIGHT: readonly { id: 'all' | DayNight; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'D', label: 'Day' },
  { id: 'N', label: 'Night' },
]

export function DayNightToggle({ value, onChange }: DayNightToggleProps) {
  return (
    <div className="grid grid-cols-3 rounded-md border border-line bg-ink p-0.5" role="group" aria-label="Day or night">
      {DAY_NIGHT.map((option) => {
        const pressed = value === option.id
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={pressed}
            onClick={() => onChange(option.id)}
            className={`rounded px-2 py-1.5 text-xs font-medium ${
              pressed ? 'bg-panel-2 text-paper' : 'text-mist hover:text-paper'
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
