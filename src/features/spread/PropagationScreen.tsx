import { useEffect, useRef, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import { Button } from '../../components/ui/Button.tsx'
import {
  compassLabel,
  INITIAL_SPREAD,
  spreadScales,
  type SpreadConditions,
} from './spreadModel.ts'
import { drawSpread, syncParticles, type WindParticle } from './spreadDraw.ts'

const PRESETS: readonly { id: string; label: string; conditions: Omit<SpreadConditions, 'hours'> }[] = [
  { id: 'calm', label: 'Calm', conditions: { windTowardDeg: 90, windSpeedKmh: 6, temperatureC: 22, humidityPct: 58 } },
  { id: 'dry', label: 'Dry wind', conditions: { windTowardDeg: 48, windSpeedKmh: 38, temperatureC: 36, humidityPct: 16 } },
  { id: 'humid', label: 'Humid', conditions: { windTowardDeg: 210, windSpeedKmh: 12, temperatureC: 27, humidityPct: 82 } },
]

export default function PropagationScreen({ active }: { active: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<WindParticle[]>([])
  const sizeKey = useRef('')
  const simRef = useRef({ ...INITIAL_SPREAD, playing: false })
  const [conditions, setConditions] = useState<SpreadConditions>(INITIAL_SPREAD)
  const [playing, setPlaying] = useState(false)

  function commit(next: SpreadConditions, nextPlaying = false) {
    simRef.current = { ...next, playing: nextPlaying }
    setConditions(next)
    setPlaying(nextPlaying)
  }

  function patch(partial: Partial<SpreadConditions>, nextPlaying = playing) {
    commit({ ...simRef.current, ...partial }, nextPlaying)
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !active) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let frame = 0
    let last = performance.now()
    let elapsed = 0

    const loop = (now: number) => {
      const current = canvasRef.current
      if (!current) return
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      const rect = current.getBoundingClientRect()
      const width = Math.max(1, Math.floor(rect.width))
      const height = Math.max(1, Math.floor(rect.height))
      if (current.width !== width || current.height !== height) {
        current.width = width
        current.height = height
      }
      const key = `${width}x${height}`
      if (sizeKey.current !== key) {
        syncParticles(particlesRef.current, width, height)
        sizeKey.current = key
      }

      const sim = simRef.current
      if (sim.playing && sim.hours < 72) {
        sim.hours = Math.min(72, sim.hours + dt * 3)
        elapsed += dt
        if (sim.hours >= 72) {
          sim.playing = false
          setPlaying(false)
          setConditions({ ...sim })
          elapsed = 0
        } else if (elapsed > 0.12) {
          elapsed = 0
          setConditions({ ...sim })
        }
      }

      const context = current.getContext('2d')
      if (context) {
        drawSpread(
          context,
          width,
          height,
          sim,
          particlesRef.current,
          dt,
          !reduceMotion,
        )
      }
      frame = requestAnimationFrame(loop)
    }

    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [active])

  const scales = spreadScales(conditions)

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto lg:overflow-hidden">
      <div role="note" className="sticky top-0 z-20 shrink-0 border-b border-hot/50 bg-[#3a1218] px-4 py-2.5">
        <p className="text-center text-xs font-semibold tracking-[0.14em] text-[#ffe4e6] sm:text-[13px]">
          DEMONSTRATION SIMULATION — NOT A VALIDATED FIRE FORECAST
        </p>
        <p className="mt-1 text-center text-[11px] text-[#ffc4ca]">
          Conceptual sketch only. No forecast model has been trained, validated, or deployed. This is not an operational prediction.
        </p>
      </div>

      <div className="grid lg:min-h-0 lg:flex-1 lg:grid-cols-[320px_minmax(0,1fr)] lg:overflow-hidden">
        <div className="space-y-4 overflow-y-auto border-line p-4 lg:border-r">
          <div>
            <h2 className="text-base font-semibold text-paper">Propagation preview</h2>
            <p className="mt-1 text-xs leading-relaxed text-mist">
              Wind stretches the field. Heat and low humidity increase the illustrated growth. The distances are relative units, not a mapped forecast.
            </p>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => patch(preset.conditions, false)}
                className="rounded-md border border-line bg-ink px-2 py-1 text-xs text-paper hover:border-mist/40"
              >
                {preset.label}
              </button>
            ))}
          </div>

          <Slider
            label={`Wind toward ${compassLabel(conditions.windTowardDeg)} · ${Math.round(conditions.windTowardDeg)}°`}
            min={0}
            max={360}
            step={1}
            value={conditions.windTowardDeg}
            onChange={(value) => patch({ windTowardDeg: value }, false)}
          />
          <div className="grid grid-cols-4 gap-1.5">
            {[
              ['N', 0],
              ['E', 90],
              ['S', 180],
              ['W', 270],
            ].map(([label, degrees]) => (
              <button
                key={label}
                type="button"
                onClick={() => patch({ windTowardDeg: Number(degrees) }, false)}
                className="rounded-md border border-line bg-ink py-1.5 text-xs text-paper hover:bg-panel-2"
              >
                {label}
              </button>
            ))}
          </div>

          <Slider
            label={`Wind speed · ${Math.round(conditions.windSpeedKmh)} km/h`}
            min={0}
            max={60}
            step={1}
            value={conditions.windSpeedKmh}
            onChange={(value) => patch({ windSpeedKmh: value }, playing)}
          />
          <Slider
            label={`Temperature · ${Math.round(conditions.temperatureC)}°C`}
            min={0}
            max={45}
            step={1}
            value={conditions.temperatureC}
            onChange={(value) => patch({ temperatureC: value }, playing)}
          />
          <Slider
            label={`Humidity · ${Math.round(conditions.humidityPct)}%`}
            min={5}
            max={95}
            step={1}
            value={conditions.humidityPct}
            onChange={(value) => patch({ humidityPct: value }, playing)}
          />
          <Slider
            label={`Time · ${conditions.hours.toFixed(1)} h`}
            min={0}
            max={72}
            step={0.5}
            value={conditions.hours}
            onChange={(value) => patch({ hours: value }, false)}
          />

          <div className="flex flex-wrap gap-2">
            <Button icon={playing ? Pause : Play} onClick={() => patch({}, !playing)}>
              {playing ? 'Pause' : 'Play'}
            </Button>
            {[-6, -1, 1, 6].map((step) => (
              <button
                key={step}
                type="button"
                onClick={() => patch({ hours: Math.min(72, Math.max(0, conditions.hours + step)) }, false)}
                className="rounded-md border border-line bg-ink px-2 py-2 text-xs text-paper hover:bg-panel-2"
              >
                {step > 0 ? `+${step}h` : `${step}h`}
              </button>
            ))}
          </div>
          <Button onClick={() => commit(INITIAL_SPREAD, false)}>Reset</Button>

          <dl className="grid grid-cols-3 gap-2 rounded-md border border-line bg-ink p-2 text-center">
            <Metric label="Along" value={scales.along.toFixed(0)} />
            <Metric label="Across" value={scales.cross.toFixed(0)} />
            <Metric label="Core" value={scales.core.toFixed(0)} />
          </dl>
          <p className="text-[11px] leading-relaxed text-muted">
            Relative units from a teaching sketch: growth rises with temperature and wind, and falls as humidity rises. This is not a physics model and not a trained forecast.
          </p>
          <p className="text-[11px] font-semibold tracking-[0.08em] text-[#ffc4ca]">
            DEMONSTRATION SIMULATION — NOT A VALIDATED FIRE FORECAST
          </p>
        </div>

        <div className="relative h-[460px] min-h-[360px] lg:h-auto">
          <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden="true" />
          <div className="pointer-events-none absolute top-3 left-3 max-w-xs rounded-md border border-hot/40 bg-[#2a1014]/90 px-3 py-2">
            <p className="text-[10px] font-semibold tracking-[0.12em] text-[#ffe4e6]">
              DEMONSTRATION SIMULATION — NOT A VALIDATED FIRE FORECAST
            </p>
            <p className="mt-1 text-sm font-medium text-paper tabular-nums">T+{conditions.hours.toFixed(1)} h</p>
            <p className="text-[11px] text-mist">
              Wind toward {compassLabel(conditions.windTowardDeg)} at {Math.round(conditions.windSpeedKmh)} km/h
            </p>
          </div>
          <div className="pointer-events-none absolute right-3 bottom-3 rounded-md border border-line bg-panel/90 px-3 py-2 text-[11px] text-mist">
            <p className="text-paper">Relative intensity</p>
            <div className="mt-1 h-1.5 w-36 rounded-full bg-gradient-to-r from-[#5a2414] via-[#ff7a3c] to-[#ffe8c8]" />
            <p className="mt-1">Cyan streaks show wind direction.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function Slider({
  label,
  min,
  max,
  step,
  value,
  onChange,
}: {
  label: string
  min: number
  max: number
  step: number
  value: number
  onChange: (value: number) => void
}) {
  return (
    <label className="block text-xs text-mist">
      {label}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-1 w-full accent-ember"
      />
    </label>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] tracking-wide text-muted uppercase">{label}</dt>
      <dd className="text-sm font-semibold text-paper tabular-nums">{value}</dd>
    </div>
  )
}
