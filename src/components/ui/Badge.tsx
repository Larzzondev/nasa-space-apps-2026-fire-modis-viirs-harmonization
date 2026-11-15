import type { ReactNode } from 'react'

type BadgeTone = 'demo' | 'archive' | 'gap' | 'alert' | 'neutral'

interface BadgeProps {
  tone: BadgeTone
  children: ReactNode
}

const toneClass: Record<BadgeTone, string> = {
  demo: 'border-amber/50 bg-amber/15 text-amber',
  archive: 'border-cyan/40 bg-cyan/10 text-cyan',
  gap: 'border-line bg-ink text-mist',
  alert: 'border-hot/50 bg-hot/15 text-[#ffc4ca]',
  neutral: 'border-line bg-white/5 text-mist',
}

export function Badge({ tone, children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-[0.14em] uppercase ${toneClass[tone]}`}
    >
      {children}
    </span>
  )
}
