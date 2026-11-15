export function ScreenFallback({ label }: { label: string }) {
  return (
    <div className="grid h-full min-h-64 place-items-center bg-ink p-6">
      <div className="text-center">
        <div className="mx-auto size-8 animate-pulse rounded-full bg-ember" />
        <p className="mt-4 text-sm text-paper">{label}</p>
      </div>
    </div>
  )
}
