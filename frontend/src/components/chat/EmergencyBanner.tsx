import { PRIMARY_EMERGENCY } from '../../config/emergency'

// Shown above the answer when the agent flags danger to life or the question matches keywords.
export function EmergencyBanner() {
  return (
    <div role="alert" className="rounded-xl bg-danger p-1">
      <a
        href={`tel:${PRIMARY_EMERGENCY.number}`}
        className="flex min-h-16 items-center gap-4 rounded-lg px-4 py-3 text-white hover:bg-black/15"
      >
        <span className="text-4xl font-extrabold tracking-tight">Dzwoń 112</span>
        <span className="text-base font-semibold leading-snug">
          Zagrożenie życia lub zdrowia? Zadzwoń teraz, zanim zaczniesz czytać dalej.
        </span>
      </a>
    </div>
  )
}
