import { DEMO_SCENARIOS, findScenario } from '../config/demo'
import type { DemoErrorKind } from '../api/demo'
import type { Demo } from '../hooks/useDemo'
import type { TabId } from './TabNav'

const ERRORS: Record<DemoErrorKind, string> = {
  forbidden: 'Serwer odrzucił token demo. Ustaw VITE_DEMO_TOKEN równy DEMO_ADMIN_TOKEN w api.',
  unavailable: 'Nie udało się przełączyć scenariusza. Sprawdź, czy api działa z DEMO_MODE=true.',
}

type Props = {
  demo: Demo
  onOpenTab: (id: TabId) => void
}

export function DemoView({ demo, onOpenTab }: Props) {
  const active = findScenario(demo.active)

  return (
    <section className="flex flex-col gap-8">
      <div className="max-w-[60ch]">
        <h1 className="text-[2rem] font-extrabold leading-tight tracking-tight">
          Uruchom scenariusz
        </h1>
        <p className="mt-2 text-ink-muted">
          Scenariusz podmienia dane w czacie i na mapie zmyślonymi odczytami. Schrony i poradnik
          zostają prawdziwe. Przełączenie scenariusza zaczyna rozmowę od nowa.
        </p>
        {!active && (
          <p className="mt-3 border-l-4 border-caution pl-4 font-semibold">
            Do prezentacji. To nie jest prawdziwy alarm.
          </p>
        )}
      </div>

      <ul aria-label="Scenariusze" className="grid gap-3 sm:grid-cols-3">
        {DEMO_SCENARIOS.map((scenario) => {
          const selected = scenario.id === demo.active
          return (
            <li key={scenario.id}>
              <button
                type="button"
                aria-pressed={selected}
                onClick={() => void demo.activate(scenario.id)}
                disabled={demo.switching}
                className={[
                  'relative flex h-full min-h-32 w-full flex-col gap-1 overflow-hidden rounded-lg border-2 bg-surface p-4 text-left disabled:opacity-60',
                  selected ? 'border-ink' : 'border-line hover:border-caution',
                ].join(' ')}
              >
                {selected && (
                  <span aria-hidden="true" className="hazard-tape absolute inset-x-0 top-0 h-2" />
                )}
                <span className="text-xl font-extrabold">{scenario.title}</span>
                <span className="text-base leading-snug text-ink-muted">{scenario.summary}</span>
                <span className="mt-auto pt-2 font-semibold text-vistula-deep">
                  {selected ? 'Trwa' : 'Uruchom'}
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      <div aria-live="polite">
        {demo.error && <p className="font-semibold text-danger">{ERRORS[demo.error]}</p>}
        {active && (
          <div className="flex flex-col gap-4 rounded-lg border-2 border-line bg-surface p-5">
            <h2 className="text-xl font-extrabold">{active.title}: co się zmieniło</h2>
            <ul className="flex list-disc flex-col gap-1 pl-6">
              {active.changes.map((change) => (
                <li key={change}>{change}</li>
              ))}
            </ul>
            <p className="text-ink-muted">
              W czacie czekają pytania do tego scenariusza, np. „{active.questions[0]}”
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                onClick={() => onOpenTab('chat')}
                className="min-h-12 rounded-lg bg-vistula px-5 font-semibold text-white hover:bg-vistula-deep"
              >
                Otwórz czat
              </button>
              <button
                type="button"
                onClick={() => onOpenTab('map')}
                className="min-h-12 rounded-lg border-2 border-vistula bg-surface px-5 font-semibold text-vistula-deep hover:bg-vistula-soft"
              >
                Otwórz mapę
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
