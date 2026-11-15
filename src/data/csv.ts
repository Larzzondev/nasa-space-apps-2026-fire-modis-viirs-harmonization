import { deliveryOn } from './archiveJuly2024.ts'
import type { ArchiveSatellite } from '../types/domain.ts'

function cell(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replaceAll('"', '""')}"`
  return value
}

export function buildArchiveCsv(
  dates: readonly string[],
  satellites: readonly ArchiveSatellite[],
): string {
  const header = [
    'source',
    'acquisition_date',
    'satellite',
    'sensor',
    'delivered_rows',
    'delivery_status',
    'coverage_note',
  ]
  const lines = [header.join(',')]
  for (const date of dates) {
    for (const satellite of satellites) {
      const row = deliveryOn(date, satellite)
      if (!row) {
        lines.push(
          [
            'No FIRMS archive loaded for this date',
            date,
            satellite,
            satellite === 'Terra' || satellite === 'Aqua' ? 'MODIS' : 'VIIRS',
            '',
            'archive_not_loaded',
            'Missing archive days are blank, not zero detections.',
          ].map(cell).join(','),
        )
        continue
      }
      lines.push(
        [
          'NASA FIRMS July 2024 local extract',
          row.date,
          row.satellite,
          row.sensor === 'modis' ? 'MODIS' : 'VIIRS',
          row.deliveredRows === null ? '' : String(row.deliveredRows),
          row.status,
          row.note ?? '',
        ].map(cell).join(','),
      )
    }
  }
  return `\uFEFF${lines.join('\n')}\n`
}

export function downloadTextFile(filename: string, contents: string, type: string) {
  const blob = new Blob([contents], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
