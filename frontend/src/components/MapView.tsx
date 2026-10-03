import { useEffect, useState, type FormEvent } from 'react'
import {
  geocode,
  getNearestShelters,
  getPowerOutages,
  getShelters,
  getSummary,
  getWarnings,
  reverseGeocode,
  type GeocodeResult,
  type PowerOutage,
  type Shelter,
  type SummaryTile,
  type Warning,
} from '../api/data'
import { formatDistance } from '../lib/distance'
import { requestLocation } from '../lib/geolocation'
import { googleMapsDirectionsUrl, NAVIGATE_LABEL, NEW_TAB_HINT } from '../lib/navigation'
import { ExternalIcon } from './ExternalIcon'
import { LeafletMap, type LayerId, type MapPoint } from './map/LeafletMap'
import { SummaryTiles } from './map/SummaryTiles'
import { WARNING_HATCH } from './map/warningHatch'

const OUT_OF_AREA_MESSAGE = 'KryzIO działa na razie tylko na terenie Krakowa'

const LAYERS: { id: LayerId; label: string }[] = [
  { id: 'shelters', label: 'Schrony i bezpieczne miejsca' },
  { id: 'warnings', label: 'Obszary ostrzeżeń' },
  { id: 'power', label: 'Wyłączenia prądu' },
]

type Search =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'not_found' }
  | { state: 'out_of_area' }
  | { state: 'error' }
  | { state: 'no_location' }
  | { state: 'found'; address: MapPoint; nearest: Shelter | null }

export function MapView() {
  const [tiles, setTiles] = useState<SummaryTile[] | null>(null)
  const [summaryFailed, setSummaryFailed] = useState(false)
  const [warnings, setWarnings] = useState<Warning[]>([])
  const [outages, setOutages] = useState<PowerOutage[]>([])
  const [shelters, setShelters] = useState<Shelter[]>([])
  const [visible, setVisible] = useState<Record<LayerId, boolean>>({
    shelters: false,
    warnings: true,
    power: true,
  })
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState<Search>({ state: 'idle' })

  useEffect(() => {
    let active = true
    getSummary()
      .then((summary) => active && setTiles(summary.tiles))
      .catch(() => active && setSummaryFailed(true))
    getWarnings()
      .then((envelope) => active && setWarnings(envelope.data ?? []))
      .catch(() => {})
    getPowerOutages()
      .then((envelope) => active && setOutages(envelope.data ?? []))
      .catch(() => {})
    getShelters()
      .then((envelope) => active && setShelters(envelope.data ?? []))
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])

  async function showNearest(place: GeocodeResult, fallbackLabel: string) {
    if (!place.found || place.lat == null || place.lon == null) {
      setSearch({ state: 'not_found' })
      return
    }
    if (!place.in_krakow) {
      setSearch({ state: 'out_of_area' })
      return
    }
    const nearest = await getNearestShelters(place.lat, place.lon, 1)
      .then((envelope) => envelope.data?.[0] ?? null)
      .catch(() => null)
    setSearch({
      state: 'found',
      address: { lat: place.lat, lon: place.lon, label: place.display_name ?? fallbackLabel },
      nearest,
    })
  }

  async function handleSearch(event: FormEvent) {
    event.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    setSearch({ state: 'loading' })
    try {
      await showNearest(await geocode(trimmed), trimmed)
    } catch {
      setSearch({ state: 'error' })
    }
  }

  async function handleUseLocation() {
    setSearch({ state: 'loading' })
    const result = await requestLocation()
    if (result.status !== 'granted') {
      setSearch({ state: 'no_location' })
      return
    }
    const { lat, lon } = result.location
    try {
      await showNearest(await reverseGeocode(lat, lon), 'Twoja lokalizacja')
    } catch {
      setSearch({ state: 'error' })
    }
  }

  const found = search.state === 'found' ? search : null

  return (
    <section className="flex flex-col gap-8">
      <div>
        <h1 className="text-[2rem] font-extrabold leading-tight tracking-tight">
          Sytuacja w Krakowie
        </h1>
        <p className="mt-2 max-w-[60ch] text-ink-muted">
          Ostrzeżenia, stany wód, jakość powietrza, wyłączenia prądu i schrony w jednym miejscu.
        </p>
      </div>

      {tiles && tiles.length > 0 && <SummaryTiles tiles={tiles} />}
      {(summaryFailed || (tiles && tiles.length === 0)) && (
        <p className="rounded-lg border-2 border-line bg-surface p-4">
          <strong>Brak danych.</strong> Podsumowanie zagrożeń jest chwilowo niedostępne. W razie
          zagrożenia życia dzwoń 112 i śledź komunikaty RCB.
        </p>
      )}

      {/* Desktop: search and its result beside the map instead of above it */}
      <div className="flex flex-col gap-8 lg:grid lg:grid-cols-[22rem_minmax(0,1fr)] lg:items-start">
        <form onSubmit={handleSearch} className="flex flex-col gap-3">
          <label htmlFor="address" className="font-semibold">
            Znajdź najbliższy schron
          </label>
          <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
            <input
              id="address"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="np. Kobierzyńska 1"
              autoComplete="street-address"
              className="min-h-14 flex-1 rounded-lg border-2 border-ink-muted bg-surface px-4 text-lg placeholder:text-ink-muted focus:border-vistula"
            />
            <button
              type="submit"
              disabled={search.state === 'loading'}
              className="min-h-14 rounded-lg bg-vistula px-6 text-lg font-semibold text-white hover:bg-vistula-deep disabled:opacity-60"
            >
              {search.state === 'loading' ? 'Szukam' : 'Pokaż na mapie'}
            </button>
          </div>
          <button
            type="button"
            onClick={handleUseLocation}
            disabled={search.state === 'loading'}
            className="min-h-12 self-start rounded-lg border-2 border-vistula bg-surface px-4 font-semibold text-vistula-deep hover:bg-vistula-soft disabled:opacity-60"
          >
            Użyj mojej lokalizacji
          </button>
          <div aria-live="polite">
            {search.state === 'not_found' && (
              <p className="text-danger">
                Nie znaleziono tego adresu. Wpisz ulicę z numerem, np. „Kobierzyńska 1”.
              </p>
            )}
            {search.state === 'out_of_area' && (
              <p className="font-semibold text-danger">{OUT_OF_AREA_MESSAGE}</p>
            )}
            {search.state === 'no_location' && (
              <p className="text-danger">
                Nie udało się ustalić lokalizacji. Zezwól na nią w przeglądarce albo wpisz adres.
              </p>
            )}
            {search.state === 'error' && (
              <p className="text-danger">
                Wyszukiwanie jest chwilowo niedostępne. Spróbuj ponownie za chwilę.
              </p>
            )}
            {found && (
              <div className="rounded-lg border-2 border-civil bg-surface p-4">
                {found.nearest ? (
                  <>
                    <p className="text-base text-ink-muted">Najbliższy schron</p>
                    <p className="text-xl font-extrabold">{found.nearest.name}</p>
                    <p>{found.nearest.address}</p>
                    {found.nearest.distance_m != null && (
                      <p className="mt-1 text-lg font-semibold text-civil-deep">
                        {formatDistance(found.nearest.distance_m)} od podanego adresu
                      </p>
                    )}
                    <a
                      href={googleMapsDirectionsUrl(found.nearest, found.address)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 inline-flex min-h-12 items-center gap-2 rounded-lg bg-vistula px-5 font-semibold text-white hover:bg-vistula-deep"
                    >
                      {NAVIGATE_LABEL}
                      <ExternalIcon />
                      <span className="sr-only">{NEW_TAB_HINT}</span>
                    </a>
                  </>
                ) : (
                  <p>
                    <strong>Brak danych</strong> o schronach w pobliżu tego adresu.
                  </p>
                )}
              </div>
            )}
          </div>
        </form>

        <div className="flex flex-col gap-3">
          <LeafletMap
            warnings={warnings}
            outages={outages}
            shelters={shelters}
            visible={visible}
            address={found?.address ?? null}
            nearest={found?.nearest ?? null}
          />
          <fieldset className="flex flex-wrap gap-x-6 gap-y-2">
            <legend className="sr-only">Warstwy mapy</legend>
            {LAYERS.map((layer) => (
              <label key={layer.id} className="flex min-h-12 items-center gap-3">
                <input
                  type="checkbox"
                  checked={visible[layer.id]}
                  onChange={(event) =>
                    setVisible((current) => ({ ...current, [layer.id]: event.target.checked }))
                  }
                  className="size-6 accent-vistula"
                />
                <LayerSwatch id={layer.id} />
                {layer.label}
              </label>
            ))}
          </fieldset>
          <MapTextList warnings={warnings} outages={outages} />
        </div>
      </div>
    </section>
  )
}

function LayerSwatch({ id }: { id: LayerId }) {
  if (id === 'shelters') {
    return (
      <svg viewBox="0 0 32 32" className="size-6" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="var(--color-civil)" />
        <path d="M16 6 27 25H5Z" fill="var(--color-vistula)" />
      </svg>
    )
  }
  if (id === 'warnings') {
    // Irregular area outline, filled with the same hatch as the map polygons
    return (
      <svg viewBox="0 0 32 24" className="h-6 w-8" aria-hidden="true">
        <path
          d="M3 9 11 3l9 3 9-1-2 10 2 6-12 1-9-3-4-5Z"
          fill={WARNING_HATCH}
          stroke="var(--color-danger)"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      </svg>
    )
  }
  return <span aria-hidden="true" className="size-5 rounded-full bg-caution" />
}

// Text alternative for the map layers: keyboard and screen reader users get the same
// information as from the popups (WCAG 1.1.1, 2.1.1)
function MapTextList({ warnings, outages }: { warnings: Warning[]; outages: PowerOutage[] }) {
  return (
    <details className="rounded-lg border-2 border-line bg-surface p-4">
      <summary className="min-h-12 cursor-pointer font-semibold">
        Lista zagrożeń z mapy ({warnings.length + outages.length})
      </summary>
      <h2 className="mt-3 text-lg font-extrabold">Ostrzeżenia</h2>
      {warnings.length ? (
        <ul className="mt-1 flex list-disc flex-col gap-1 pl-6">
          {warnings.map((warning) => (
            <li key={warning.id}>
              <strong>{warning.title}</strong> – {warning.area}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1">Brak aktywnych ostrzeżeń.</p>
      )}
      <h2 className="mt-3 text-lg font-extrabold">Wyłączenia prądu</h2>
      {outages.length ? (
        <ul className="mt-1 flex list-disc flex-col gap-1 pl-6">
          {outages.map((outage) => (
            <li key={outage.id}>
              {outage.planned ? 'Planowane wyłączenie' : 'Awaria'}: {outage.area}
              {outage.location_precision === 'approximate' && ' (lokalizacja przybliżona)'}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1">Brak wyłączeń prądu.</p>
      )}
    </details>
  )
}
