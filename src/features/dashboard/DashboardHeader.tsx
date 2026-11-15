import { Flame } from 'lucide-react'
import { Badge } from '../../components/ui/Badge.tsx'

export function DashboardHeader() {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="flex size-9 items-center justify-center rounded-md bg-ink text-ember ring-1 ring-line">
          <Flame className="size-5" aria-hidden="true" />
        </span>
        <div>
          <p className="text-[11px] font-medium tracking-[0.16em] text-mist uppercase">
            NASA Space Apps Challenge 2026
          </p>
          <h1 className="text-base font-semibold text-paper">Fire Activity Harmonization</h1>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="demo">DEMO areas</Badge>
        <p className="text-xs text-mist">Detection dataset not connected</p>
      </div>
    </header>
  )
}
