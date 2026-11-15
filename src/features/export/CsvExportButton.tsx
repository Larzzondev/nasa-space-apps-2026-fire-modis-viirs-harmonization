import { Download } from 'lucide-react'
import { Button } from '../../components/ui/Button.tsx'

export function CsvExportButton() {
  return (
    <div className="space-y-2">
      <Button icon={Download} disabled aria-describedby="csv-export-note">
        Export CSV
      </Button>
      <p id="csv-export-note" className="text-xs text-mist">
        Export stays disabled until a verified detection dataset is available.
      </p>
    </div>
  )
}
