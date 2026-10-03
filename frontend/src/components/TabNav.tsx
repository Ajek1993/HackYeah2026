import { useRef, type KeyboardEvent } from 'react'

export type TabId = 'chat' | 'map' | 'demo'

export type TabDef = {
  id: TabId
  label: string
}

type Props = {
  tabs: TabDef[]
  active: TabId
  onChange: (id: TabId) => void
}

export function TabNav({ tabs, active, onChange }: Props) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})

  // Arrow-key navigation per WAI-ARIA tabs pattern
  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    event.preventDefault()
    const next = tabs[(index + step + tabs.length) % tabs.length]
    onChange(next.id)
    refs.current[next.id]?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label="Sekcje aplikacji"
      className="flex gap-1 rounded-xl bg-vistula-soft p-1"
    >
      {tabs.map((tab, index) => {
        const selected = tab.id === active
        const isDemo = tab.id === 'demo'
        return (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[tab.id] = el
            }}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={selected}
            aria-controls={selected ? `panel-${tab.id}` : undefined}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={[
              'min-h-12 flex-1 rounded-lg px-4 text-base font-semibold transition-colors',
              selected
                ? isDemo
                  ? 'bg-caution text-white'
                  : 'bg-vistula text-white'
                : 'text-vistula-deep hover:bg-white',
            ].join(' ')}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
