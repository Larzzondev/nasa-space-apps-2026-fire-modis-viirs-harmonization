import { CalendarDays, Globe, Satellite, Wind, type LucideIcon } from 'lucide-react'

export type ScreenId = 'globe' | 'history' | 'sensors' | 'spread'

export interface ScreenItem {
  id: ScreenId
  label: string
  description: string
  icon: LucideIcon
}

export const SCREENS: readonly ScreenItem[] = [
  {
    id: 'globe',
    label: 'Global',
    description: 'Hotspot sample',
    icon: Globe,
  },
  {
    id: 'history',
    label: 'Historical',
    description: 'July 2024 archive',
    icon: CalendarDays,
  },
  {
    id: 'sensors',
    label: 'Sensors',
    description: 'MODIS and VIIRS',
    icon: Satellite,
  },
  {
    id: 'spread',
    label: 'Propagation',
    description: 'Conceptual sketch',
    icon: Wind,
  },
]
