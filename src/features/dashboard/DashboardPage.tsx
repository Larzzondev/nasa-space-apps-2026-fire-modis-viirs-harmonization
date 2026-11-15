import { useState } from 'react'
import { DEMO_AREAS } from '../../demo/demoAreas.ts'
import type { DashboardFilters } from '../../types/domain.ts'
import { BurningActivityCalendar } from '../calendar/BurningActivityCalendar.tsx'
import { CsvExportButton } from '../export/CsvExportButton.tsx'
import { createDefaultDateRange } from '../filters/dateRange.ts'
import { FilterSidebar } from '../filters/FilterSidebar.tsx'
import { CesiumViewer } from '../globe/CesiumViewer.tsx'
import { MetricCards } from '../metrics/MetricCards.tsx'
import { DashboardHeader } from './DashboardHeader.tsx'

export function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFilters>(() => ({
    areaOfInterestId: null,
    dateRange: createDefaultDateRange(),
  }))

  const selectedArea = DEMO_AREAS.find((area) => area.id === filters.areaOfInterestId) ?? null

  return (
    <div className="flex min-h-dvh flex-col bg-ink text-paper lg:h-dvh lg:overflow-hidden">
      <DashboardHeader />
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <FilterSidebar
          areas={DEMO_AREAS}
          areasAreDemo
          filters={filters}
          onFiltersChange={setFilters}
        >
          <CsvExportButton />
        </FilterSidebar>
        <div className="flex min-w-0 flex-1 flex-col lg:min-h-0">
          <CesiumViewer area={selectedArea} extentIsDemo={selectedArea !== null} />
          <div className="space-y-4 border-t border-line p-4 lg:max-h-[46%] lg:overflow-y-auto">
            <MetricCards />
            <BurningActivityCalendar dateRange={filters.dateRange} />
          </div>
        </div>
      </div>
    </div>
  )
}
