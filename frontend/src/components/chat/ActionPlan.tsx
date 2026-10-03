import type { Sections } from '../../api/chat'

const PHASES = [
  { key: 'before', label: 'Przed' },
  { key: 'during', label: 'W trakcie' },
  { key: 'after', label: 'Po' },
] as const

// Before / during / after drawn as an evacuation route: phases joined by a dashed line.
export function ActionPlan({ sections }: { sections: Sections }) {
  const phases = PHASES.filter((phase) => sections[phase.key].length > 0)

  return (
    <div className="flex flex-col gap-6">
      {sections.situation && (
        <div>
          <h3 className="text-base font-semibold text-ink-muted">Sytuacja</h3>
          <p className="mt-1 text-xl font-semibold leading-snug">{sections.situation}</p>
        </div>
      )}

      {phases.length > 0 && (
        <ol aria-label="Co zrobić" className="flex flex-col">
          {phases.map((phase, index) => {
            const last = index === phases.length - 1
            return (
              <li key={phase.key} className="relative grid grid-cols-[2.5rem_1fr] gap-x-4">
                {!last && (
                  <span
                    aria-hidden="true"
                    className="absolute top-10 bottom-0 left-[calc(1.25rem-1.5px)] border-l-[3px] border-dashed border-civil"
                  />
                )}
                <span
                  aria-hidden="true"
                  className="relative flex size-10 items-center justify-center rounded-full bg-civil text-lg font-extrabold text-white"
                >
                  {index + 1}
                </span>
                <div className={last ? 'pt-1.5' : 'pt-1.5 pb-7'}>
                  <h3 className="text-xl font-extrabold leading-tight">{phase.label}</h3>
                  <ul className="mt-2 flex list-disc flex-col gap-1.5 pl-5 marker:text-civil">
                    {sections[phase.key].map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ul>
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}
