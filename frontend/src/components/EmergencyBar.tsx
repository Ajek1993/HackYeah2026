import { useState } from 'react'
import { OTHER_EMERGENCY, PRIMARY_EMERGENCY } from '../config/emergency'

// Always visible, independent of the agent (PRD F13)
export function EmergencyBar() {
  const [open, setOpen] = useState(false)

  return (
    <footer className="sticky bottom-0 z-20 bg-civil text-white shadow-[0_-2px_0_var(--color-civil-deep)] [@media(max-height:480px)]:static [&_:focus-visible]:outline-white">
      <ul
        id="other-numbers"
        hidden={!open}
        className="mx-auto grid max-h-[40vh] max-w-6xl grid-cols-2 gap-2 overflow-y-auto px-4 pt-4 sm:grid-cols-3"
      >
        {OTHER_EMERGENCY.map((item) => (
          <li key={item.number}>
            <a
              href={`tel:${item.number}`}
              className="flex min-h-12 items-baseline gap-2 rounded-lg bg-civil-deep px-3 py-2 hover:bg-black/20"
            >
              <span className="text-xl font-extrabold">{item.number}</span>
              <span className="text-sm leading-snug">{item.name}</span>
            </a>
          </li>
        ))}
      </ul>
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
        <a
          href={`tel:${PRIMARY_EMERGENCY.number}`}
          className="flex min-h-14 min-w-0 flex-1 basis-56 items-center gap-3 rounded-lg bg-white px-4 text-civil-deep hover:bg-paper"
        >
          <span className="text-3xl font-extrabold tracking-tight">{PRIMARY_EMERGENCY.number}</span>
          <span className="text-base font-semibold leading-tight">
            Zagrożenie życia? Dzwoń teraz
          </span>
        </a>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="other-numbers"
          onClick={() => setOpen((value) => !value)}
          className="min-h-14 rounded-lg border-2 border-white px-4 text-base font-semibold hover:bg-civil-deep"
        >
          {open ? 'Zwiń' : 'Inne numery'}
        </button>
      </div>
    </footer>
  )
}
