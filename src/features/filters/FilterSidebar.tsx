import { useId, type ReactNode } from 'react'
import type { AreaOfInterest, DashboardFilters } from '../../types/domain.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { isOrderedDateRange } from './dateRange.ts'

interface FilterSidebarProps {
  areas: readonly AreaOfInterest[]
  areasAreDemo: boolean
  filters: DashboardFilters
  onFiltersChange: (next: DashboardFilters) => void
  children?: ReactNode
}

export function FilterSidebar({
  areas,
  areasAreDemo,
  filters,
  onFiltersChange,
  children,
}: FilterSidebarProps) {
  const startId = useId()
  const endId = useId()
  const rangeIsOrdered = isOrderedDateRange(filters.dateRange)

  function selectArea(areaOfInterestId: string | null) {
    onFiltersChange({ ...filters, areaOfInterestId })
  }

  function updateDate(key: keyof DashboardFilters['dateRange'], value: string) {
    onFiltersChange({
      ...filters,
      dateRange: { ...filters.dateRange, [key]: value },
    })
  }

  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-line bg-panel/90 lg:w-80 lg:overflow-y-auto lg:border-r lg:border-b-0">
      <div className="space-y-6 px-4 py-4">
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-paper">Area of interest</legend>
          <p className="text-xs text-mist">Choose a frame for the globe. Nothing is queried yet.</p>
          <div className="space-y-1 pt-1">
            <AreaOption
              name="Full globe"
              description="Default camera. No extent is drawn."
              checked={filters.areaOfInterestId === null}
              onSelect={() => selectArea(null)}
            />
            {areas.map((area) => (
              <AreaOption
                key={area.id}
                name={area.name}
                description="Sample camera frame."
                demo={areasAreDemo}
                checked={filters.areaOfInterestId === area.id}
                onSelect={() => selectArea(area.id)}
              />
            ))}
          </div>
          {areasAreDemo ? (
            <p className="text-xs text-mist">
              DEMO extents are for camera framing. They are not fire perimeters.
            </p>
          ) : null}
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-sm font-medium text-paper">Date range</legend>
          <p className="text-xs text-mist">Local calendar dates. Stored in the page only.</p>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs text-mist" htmlFor={startId}>
              Start
              <input
                id={startId}
                type="date"
                value={filters.dateRange.start}
                onChange={(event) => updateDate('start', event.target.value)}
                className="mt-1 w-full rounded-md border border-line bg-ink px-2 py-2 text-sm text-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
              />
            </label>
            <label className="block text-xs text-mist" htmlFor={endId}>
              End
              <input
                id={endId}
                type="date"
                value={filters.dateRange.end}
                onChange={(event) => updateDate('end', event.target.value)}
                className="mt-1 w-full rounded-md border border-line bg-ink px-2 py-2 text-sm text-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
              />
            </label>
          </div>
          {rangeIsOrdered ? null : (
            <p role="alert" className="text-xs text-[#f3c7a4]">
              End date must be on or after the start date.
            </p>
          )}
        </fieldset>
      </div>
      {children ? <div className="mt-auto border-t border-line px-4 py-4">{children}</div> : null}
    </aside>
  )
}

interface AreaOptionProps {
  name: string
  description: string
  checked: boolean
  demo?: boolean
  onSelect: () => void
}

function AreaOption({ name, description, checked, demo = false, onSelect }: AreaOptionProps) {
  return (
    <label
      className={`flex cursor-pointer items-start gap-3 rounded-md border px-2 py-2 ${
        checked ? 'border-line bg-ink' : 'border-transparent hover:bg-ink/60'
      }`}
    >
      <input
        type="radio"
        name="area-of-interest"
        checked={checked}
        onChange={onSelect}
        className="mt-1 accent-ember"
      />
      <span className="min-w-0">
        <span className="flex flex-wrap items-center gap-2 text-sm text-paper">
          {name}
          {demo ? <Badge tone="demo">DEMO</Badge> : null}
        </span>
        <span className="mt-0.5 block text-xs text-mist">{description}</span>
      </span>
    </label>
  )
}
