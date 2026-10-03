import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { formatDistance } from '../lib/distance'
import { MapView } from './MapView'

// Leaflet needs a real layout engine; the map itself is checked in the browser.
vi.mock('./map/LeafletMap', () => ({
  LeafletMap: (props: { address: { label: string } | null; nearest: { name: string } | null }) => (
    <div data-testid="map">
      {props.address?.label}|{props.nearest?.name}
    </div>
  ),
}))

const NOW = new Date().toISOString()
const STALE = new Date(Date.now() - 4 * 3_600_000).toISOString()

const SUMMARY = {
  generated_at: NOW,
  demo_scenario: null,
  tiles: [
    {
      kind: 'warnings',
      status: 'warning',
      headline: '1 ostrzeżenie hydrologiczne',
      source: 'IMGW',
      updated_at: NOW,
      is_stale: false,
      is_simulated: false,
    },
    {
      kind: 'air',
      status: 'danger',
      headline: 'Jakość powietrza: zła',
      source: 'GIOŚ',
      updated_at: STALE,
      is_stale: true,
      is_simulated: false,
    },
  ],
}

const envelope = (data: unknown) => ({
  source: 'Test',
  updated_at: NOW,
  is_stale: false,
  is_simulated: false,
  data,
})

const SHELTER = {
  id: 's-1',
  name: 'Schron przy Testowej',
  address: 'Testowa 2',
  lat: 50.03,
  lon: 19.92,
  capacity: 100,
  type: 'shelter',
  distance_m: 1240,
}

type Routes = Record<string, unknown | ((url: URL) => unknown)>

let fetchMock: ReturnType<typeof vi.fn>

function serve(routes: Routes) {
  fetchMock.mockImplementation(async (input: URL | string) => {
    const url = new URL(String(input))
    const route = routes[url.pathname]
    if (route === undefined) return new Response('{}', { status: 404 })
    const body = typeof route === 'function' ? route(url) : route
    return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } })
  })
}

const baseRoutes: Routes = {
  '/summary': SUMMARY,
  '/warnings': envelope([]),
  '/power-outages': envelope([]),
  '/shelters': envelope([SHELTER]),
}

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => vi.unstubAllGlobals())

async function searchAddress(text: string) {
  await userEvent.type(screen.getByLabelText('Znajdź najbliższy schron'), text)
  await userEvent.click(screen.getByRole('button', { name: 'Pokaż na mapie' }))
}

describe('MapView', () => {
  it('shows summary tiles with spelled-out status and stale marking', async () => {
    serve(baseRoutes)
    render(<MapView />)

    // wait for the tiles; "Ostrzeżenia" is also a heading in the text list under the map
    const warningsTile = (await screen.findByText('1 ostrzeżenie hydrologiczne')).closest('li')!
    expect(within(warningsTile).getByRole('heading', { name: 'Ostrzeżenia' })).toBeInTheDocument()
    expect(within(warningsTile).getByText('Uwaga')).toBeInTheDocument()
    expect(within(warningsTile).getByText('1 ostrzeżenie hydrologiczne')).toBeInTheDocument()

    const airTile = screen.getByRole('heading', { name: 'Jakość powietrza' }).closest('li')!
    expect(within(airTile).getByText('Zagrożenie')).toBeInTheDocument()
    expect(within(airTile).getByText('dane sprzed 4 godz.')).toBeInTheDocument()
  })

  it('shows a no-data notice when the summary is unavailable', async () => {
    serve({ ...baseRoutes, '/summary': undefined })
    render(<MapView />)

    expect(
      await screen.findByText(/Podsumowanie zagrożeń jest chwilowo niedostępne/),
    ).toBeInTheDocument()
  })

  it('finds an address and shows the nearest shelter with distance', async () => {
    serve({
      ...baseRoutes,
      '/geocode': (url: URL) => ({
        query: url.searchParams.get('q'),
        found: true,
        lat: 50.031,
        lon: 19.921,
        display_name: 'Testowa 1, Kraków',
        district: 'Dębniki',
        in_krakow: true,
      }),
      '/shelters/nearest': (url: URL) => {
        expect(url.searchParams.get('limit')).toBe('1')
        return envelope([SHELTER])
      },
    })
    render(<MapView />)

    await searchAddress('Testowa 1')

    expect(await screen.findByText('Schron przy Testowej')).toBeInTheDocument()
    expect(screen.getByText('1,2 km od podanego adresu')).toBeInTheDocument()
    expect(screen.getByTestId('map')).toHaveTextContent('Testowa 1, Kraków|Schron przy Testowej')

    const link = screen.getByRole('link', { name: /Nawiguj w Google Maps/ })
    expect(link).toHaveAccessibleName(/otwiera się w nowej karcie/)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    const url = new URL(link.getAttribute('href')!)
    expect(url.searchParams.get('origin')).toBe('50.031,19.921')
    expect(url.searchParams.get('destination')).toBe('50.03,19.92')
  })

  it('refuses addresses outside Kraków with the fixed message', async () => {
    serve({
      ...baseRoutes,
      '/geocode': {
        query: 'Skawina',
        found: true,
        lat: 49.97,
        lon: 19.83,
        display_name: 'Skawina',
        district: null,
        in_krakow: false,
      },
    })
    render(<MapView />)

    await searchAddress('Skawina')

    expect(
      await screen.findByText('KryzIO działa na razie tylko na terenie Krakowa'),
    ).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/shelters/nearest'))).toBe(
      false,
    )
  })

  it('asks for a clearer address when the geocoder finds nothing', async () => {
    serve({
      ...baseRoutes,
      '/geocode': {
        query: 'xyz',
        found: false,
        lat: null,
        lon: null,
        display_name: null,
        district: null,
        in_krakow: null,
      },
    })
    render(<MapView />)

    await searchAddress('xyz')

    expect(await screen.findByText(/Nie znaleziono tego adresu/)).toBeInTheDocument()
  })

  it('says there is no shelter data when nearest shelters are missing', async () => {
    serve({
      ...baseRoutes,
      '/geocode': {
        query: 'Testowa 1',
        found: true,
        lat: 50,
        lon: 19.9,
        display_name: 'Testowa 1',
        district: null,
        in_krakow: true,
      },
      '/shelters/nearest': envelope(null),
    })
    render(<MapView />)

    await searchAddress('Testowa 1')

    expect(await screen.findByText(/o schronach w pobliżu tego adresu/)).toBeInTheDocument()
  })

  it('lets the user toggle map layers', async () => {
    serve(baseRoutes)
    render(<MapView />)

    const shelters = screen.getByRole('checkbox', { name: 'Schrony i bezpieczne miejsca' })
    expect(shelters).not.toBeChecked()
    await userEvent.click(shelters)
    expect(shelters).toBeChecked()
  })
})

describe('Map text alternative', () => {
  it('lists warnings and outages from the map as text', async () => {
    serve({
      ...baseRoutes,
      '/warnings': envelope([
        { id: 'w1', title: 'Susza hydrologiczna', area: 'zlewnia Rudawy', geometry: null },
      ]),
      '/power-outages': envelope([{ id: 'o1', planned: true, area: 'Kraków ul. Testowa 1-10' }]),
    })
    render(<MapView />)

    const summary = await screen.findByText(/Lista zagrożeń z mapy \(2\)/)
    await userEvent.click(summary)

    expect(screen.getByText('Susza hydrologiczna')).toBeInTheDocument()
    expect(screen.getByText(/Planowane wyłączenie: Kraków ul. Testowa 1-10/)).toBeInTheDocument()
  })
})

describe('formatDistance', () => {
  it('uses metres below a kilometre and kilometres above', () => {
    expect(formatDistance(347)).toBe('350 m')
    expect(formatDistance(1240)).toBe('1,2 km')
    expect(formatDistance(5000)).toBe('5 km')
  })
})
