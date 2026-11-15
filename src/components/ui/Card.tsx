import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

interface CardProps {
  title: string
  icon?: LucideIcon
  children: ReactNode
  className?: string
}

export function Card({ title, icon: Icon, children, className = '' }: CardProps) {
  return (
    <section className={`rounded-lg border border-line bg-panel p-4 ${className}`}>
      <div className="flex items-center gap-2">
        {Icon ? <Icon className="size-4 text-ember" aria-hidden="true" /> : null}
        <h2 className="text-sm font-medium text-paper">{title}</h2>
      </div>
      <div className="mt-3">{children}</div>
    </section>
  )
}
