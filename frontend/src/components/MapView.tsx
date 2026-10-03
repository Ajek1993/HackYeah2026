export function MapView() {
  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-[2rem] font-extrabold leading-tight tracking-tight">
        Mapa zagrożeń i schronów
      </h1>
      <p className="max-w-[60ch] text-ink-muted">
        Tu zobaczysz aktualne ostrzeżenia, stany wód, jakość powietrza, wyłączenia prądu i
        najbliższe schrony w Krakowie.
      </p>
      <div className="grid min-h-80 place-items-center rounded-xl border-2 border-dashed border-line bg-surface p-6 text-center text-ink-muted">
        Mapa pojawi się po podłączeniu danych.
      </div>
    </section>
  )
}
