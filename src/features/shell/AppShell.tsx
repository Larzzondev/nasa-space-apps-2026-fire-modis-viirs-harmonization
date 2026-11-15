import { lazy, Suspense, useEffect, useState } from 'react'
import { Flame } from 'lucide-react'
import { ScreenErrorBoundary } from '../../components/ui/ErrorBoundary.tsx'
import { ScreenFallback } from '../../components/ui/ScreenFallback.tsx'
import { SCREENS, type ScreenId } from './nav.ts'

const GlobeScreen = lazy(() => import('../globe/GlobeScreen.tsx'))
const HistoryScreen = lazy(() => import('../history/HistoryScreen.tsx'))
const ComparisonScreen = lazy(() => import('../compare/ComparisonScreen.tsx'))
const PropagationScreen = lazy(() => import('../spread/PropagationScreen.tsx'))

export function AppShell() {
  const [screen, setScreen] = useState<ScreenId>('globe')
  const [mounted, setMounted] = useState<ReadonlySet<ScreenId>>(() => new Set(['globe']))

  useEffect(() => {
    const current = SCREENS.find((item) => item.id === screen)
    document.title = current ? `${current.label} · FireLens` : 'FireLens'
  }, [screen])

  function open(next: ScreenId) {
    setScreen(next)
    setMounted((current) => {
      if (current.has(next)) return current
      const copy = new Set(current)
      copy.add(next)
      return copy
    })
  }

  return (
    <div className="flex h-dvh flex-col bg-ink text-paper">
      <div className="h-px bg-gradient-to-r from-ember via-amber to-cyan" />
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line bg-panel px-3 py-2.5 sm:px-4">
        <div className="flex items-center gap-3">
          <span className="flex size-9 items-center justify-center rounded-md bg-ink text-ember ring-1 ring-ember/40">
            <Flame className="size-5" aria-hidden="true" />
          </span>
          <div>
            <p className="text-[10px] font-semibold tracking-[0.18em] text-mist uppercase">NASA Space Apps 2026</p>
            <h1 className="text-base font-semibold tracking-tight text-paper">FireLens</h1>
          </div>
        </div>
        <p className="hidden text-right text-[11px] text-mist sm:block">
          Archive rows are not unique fires
        </p>
      </header>

      <div className="flex min-h-0 flex-1">
        <nav className="hidden w-[196px] shrink-0 flex-col border-r border-line bg-panel/80 p-2 lg:flex" aria-label="Screens">
          <ul className="space-y-1">
            {SCREENS.map((item) => {
              const Icon = item.icon
              const current = screen === item.id
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-current={current ? 'page' : undefined}
                    onClick={() => open(item.id)}
                    className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left ${
                      current
                        ? 'bg-white/5 text-paper shadow-[inset_2px_0_0_#ff7a3c]'
                        : 'text-mist hover:bg-white/5 hover:text-paper'
                    }`}
                  >
                    <Icon className="size-4 shrink-0" aria-hidden="true" />
                    <span>
                      <span className="block text-sm font-medium">{item.label}</span>
                      <span className="block text-[11px] text-muted">{item.description}</span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
          <p className="mt-auto px-2.5 pt-4 text-[11px] leading-relaxed text-muted">
            Globe points are labeled demo data. July statistics come from the tracked FIRMS reports.
          </p>
        </nav>

        <main className="relative min-w-0 flex-1">
          {mounted.has('globe') ? (
            <div className={screen === 'globe' ? 'h-full' : 'hidden'}>
              <ScreenErrorBoundary title="Global fire intelligence">
                <Suspense fallback={<ScreenFallback label="Opening the globe" />}>
                  <GlobeScreen active={screen === 'globe'} />
                </Suspense>
              </ScreenErrorBoundary>
            </div>
          ) : null}
          {mounted.has('history') ? (
            <div className={screen === 'history' ? 'h-full' : 'hidden'}>
              <ScreenErrorBoundary title="Historical explorer">
                <Suspense fallback={<ScreenFallback label="Loading the July archive" />}>
                  <HistoryScreen />
                </Suspense>
              </ScreenErrorBoundary>
            </div>
          ) : null}
          {mounted.has('sensors') ? (
            <div className={screen === 'sensors' ? 'h-full' : 'hidden'}>
              <ScreenErrorBoundary title="Sensor comparison">
                <Suspense fallback={<ScreenFallback label="Loading sensor comparison" />}>
                  <ComparisonScreen />
                </Suspense>
              </ScreenErrorBoundary>
            </div>
          ) : null}
          {mounted.has('spread') ? (
            <div className={screen === 'spread' ? 'h-full' : 'hidden'}>
              <ScreenErrorBoundary title="Propagation preview">
                <Suspense fallback={<ScreenFallback label="Loading the propagation sketch" />}>
                  <PropagationScreen active={screen === 'spread'} />
                </Suspense>
              </ScreenErrorBoundary>
            </div>
          ) : null}
        </main>
      </div>

      <nav className="grid shrink-0 grid-cols-4 border-t border-line bg-panel lg:hidden" aria-label="Screens">
        {SCREENS.map((item) => {
          const Icon = item.icon
          const current = screen === item.id
          return (
            <button
              key={item.id}
              type="button"
              aria-current={current ? 'page' : undefined}
              onClick={() => open(item.id)}
              className={`flex flex-col items-center gap-1 px-1 py-2 text-[11px] ${
                current ? 'text-ember' : 'text-mist'
              }`}
            >
              <Icon className="size-4" aria-hidden="true" />
              {item.label}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
