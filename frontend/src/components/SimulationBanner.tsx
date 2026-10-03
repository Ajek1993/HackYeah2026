import { findScenario } from '../config/demo'
import type { Demo } from '../hooks/useDemo'
import { formatUpdatedAt } from '../lib/time'

// Shown on every tab while a scenario runs, so no screenshot passes for a real alarm (US-06)
export function SimulationBanner({ demo }: { demo: Demo }) {
  const scenario = findScenario(demo.active)
  if (!scenario) return null
  const until = formatUpdatedAt(demo.expiresAt)

  return (
    <aside aria-label="Symulacja" className="sticky top-0 z-30 bg-caution-soft text-ink">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <p className="min-w-0 flex-1 basis-64">
          <span className="mr-2 inline-block rounded bg-ink px-2 text-lg font-extrabold tracking-wide text-caution-soft">
            SYMULACJA
          </span>
          <span className="font-semibold">To nie jest prawdziwy alarm.</span>{' '}
          <span className="text-ink-muted">
            Scenariusz: {scenario.title}
            {until && `, wyłączy się o ${until}`}
          </span>
        </p>
        <button
          type="button"
          onClick={() => void demo.deactivate()}
          disabled={demo.switching}
          className="min-h-12 rounded-lg border-2 border-ink bg-surface px-4 font-semibold hover:bg-paper disabled:opacity-60"
        >
          Zakończ symulację
        </button>
      </div>
      <div aria-hidden="true" className="hazard-tape h-2.5" />
    </aside>
  )
}
