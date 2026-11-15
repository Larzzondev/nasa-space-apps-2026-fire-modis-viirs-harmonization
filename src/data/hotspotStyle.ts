export const FRP_BINS = [
  { label: '< 5 MW', color: '#f6c453' },
  { label: '5–20', color: '#ff8a3d' },
  { label: '20–80', color: '#ff4b3a' },
  { label: '≥ 80', color: '#ff2d6a' },
] as const

export function frpColor(frpMw: number): string {
  if (frpMw < 5) return FRP_BINS[0].color
  if (frpMw < 20) return FRP_BINS[1].color
  if (frpMw < 80) return FRP_BINS[2].color
  return FRP_BINS[3].color
}

export function frpPixelSize(frpMw: number): number {
  return Math.max(5, Math.min(15, 5 + Math.log10(frpMw + 1) * 6.5))
}
