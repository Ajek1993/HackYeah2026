const SCENARIOS = [
  { id: 'flood', title: 'Powódź', description: 'Wisła przekracza stan alarmowy w rejonie Dębnik.' },
  {
    id: 'power_outage',
    title: 'Brak prądu',
    description: 'Rozległa awaria sieci w kilku dzielnicach.',
  },
  {
    id: 'bomb_threat',
    title: 'Atak bombowy',
    description: 'Komunikat o zagrożeniu i wskazanie schronów.',
  },
]

export function DemoView() {
  return (
    <section className="flex flex-col gap-6">
      <div role="status" className="rounded-xl bg-caution-soft p-4 text-caution">
        <p className="text-lg font-extrabold">Symulacja</p>
        <p>Dane w tej zakładce są zmyślone na potrzeby prezentacji. To nie jest prawdziwy alarm.</p>
      </div>
      <h1 className="text-[2rem] font-extrabold leading-tight tracking-tight">
        Wybierz scenariusz
      </h1>
      <ul className="grid gap-3 sm:grid-cols-3">
        {SCENARIOS.map((scenario) => (
          <li key={scenario.id}>
            <button
              type="button"
              className="flex h-full min-h-28 w-full flex-col gap-1 rounded-lg border-2 border-line bg-surface p-4 text-left hover:border-caution"
            >
              <span className="text-xl font-extrabold">{scenario.title}</span>
              <span className="text-base text-ink-muted">{scenario.description}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
