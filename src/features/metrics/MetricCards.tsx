import { Activity, Flame, History, type LucideIcon } from 'lucide-react'
import { Card } from '../../components/ui/Card.tsx'

interface EmptyMetric {
  id: string
  title: string
  value: string
  detail: string
  icon: LucideIcon
}

const EMPTY_METRICS: readonly EmptyMetric[] = [
  {
    id: 'detections',
    title: 'Total hotspot detections',
    value: '—',
    detail: 'No dataset loaded',
    icon: Flame,
  },
  {
    id: 'median',
    title: 'Historical median',
    value: '—',
    detail: 'No baseline loaded',
    icon: History,
  },
  {
    id: 'anomaly',
    title: 'Anomaly status',
    value: 'Unavailable',
    detail: 'Not evaluated',
    icon: Activity,
  },
]

export function MetricCards() {
  return (
    <section aria-label="Detection summary" className="space-y-3">
      <ul className="grid gap-3 sm:grid-cols-3">
        {EMPTY_METRICS.map((metric) => (
          <li key={metric.id}>
            <Card title={metric.title} icon={metric.icon} className="h-full">
              <p className="text-2xl font-semibold tracking-tight text-paper tabular-nums">
                {metric.value}
              </p>
              <p className="mt-1 text-xs text-mist">{metric.detail}</p>
            </Card>
          </li>
        ))}
      </ul>
      <p className="text-xs text-mist">
        Counts stay empty until a verified detection dataset is connected. Filters do not create
        numbers.
      </p>
    </section>
  )
}
