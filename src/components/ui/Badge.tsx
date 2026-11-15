import type { ReactNode } from 'react'

type BadgeTone = 'demo' | 'placeholder'

interface BadgeProps {
  tone: BadgeTone
  children: ReactNode
}

const toneClass: Record<BadgeTone, string> = {
  demo: 'border-[#e07a3d]/50 bg-[#e07a3d]/15 text-[#f3c7a4]',
  placeholder: 'border-line bg-ink text-mist',
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
