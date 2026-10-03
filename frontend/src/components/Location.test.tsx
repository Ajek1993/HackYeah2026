import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatView } from './ChatView'
import { MapView } from './MapView'

vi.mock('./map/LeafletMap', () => ({
  LeafletMap: (props: { address: { label: string } | null }) => (
    <div data-testid="map">{props.address?.label}</div>
  ),
}))

const POSITION = { coords: { latitude: 50.0312, longitude: 19.9204, accuracy: 24.6 } }
const DENIED = { code: 1, PERMISSION_DENIED: 1 }

const reply = {
  session_id: 's',
  answer: 'Odpowiedź agenta.',
  sections: null,
  sources: [],
  emergency: false,
  out_of_area: false,
  off_topic: false,
  is_simulated: false,
  disclaimer: null,
}

const json = (body: unknown) =>
  new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } })

let fetchMock: ReturnType<typeof vi.fn>
let getCurrentPosition: ReturnType<typeof vi.fn>

function grant() {
  getCurrentPosition.mockImplementation((success: (p: unknown) => void) => success(POSITION))
}

function deny() {
  getCurrentPosition.mockImplementation((_: unknown, error: (e: unknown) => void) => error(DENIED))
}

beforeEach(() => {
  fetchMock = vi.fn()
  getCurrentPosition = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('navigator', { ...navigator, geolocation: { getCurrentPosition } })
})

afterEach(() => vi.unstubAllGlobals())

const chatBodies = () =>
  fetchMock.mock.calls
    .filter(([, init]) => init?.method === 'POST')
    .map(([, init]) => JSON.parse(init.body as string))

async function ask(question: string) {
  const input = screen.getByRole('textbox')
  await userEvent.clear(input)
  await userEvent.type(input, question)
  await userEvent.click(screen.getByRole('button', { name: 'Zapytaj' }))
}

describe('Chat with device location', () => {
  it('asks for location with the first question and sends it with every question', async () => {
    grant()
    fetchMock.mockResolvedValue(json(reply))
    render(<ChatView />)

    await ask('Czy grozi mi zalanie?')
    await screen.findByText('Odpowiedź agenta.')
    await ask('A co z prądem?')
    await vi.waitFor(() => expect(chatBodies()).toHaveLength(2))

    expect(getCurrentPosition).toHaveBeenCalledTimes(1)
    for (const body of chatBodies()) {
      expect(body.location).toEqual({ lat: 50.0312, lon: 19.9204, accuracy_m: 25 })
    }
    expect(screen.getByText(/Używam Twojej lokalizacji/)).toBeInTheDocument()
  })

  it('shows a waiting message while the browser asks for permission', async () => {
    getCurrentPosition.mockImplementation(() => {})
    render(<ChatView />)

    await ask('Czy grozi mi zalanie?')

    expect(screen.getByText(/Czekam na zgodę na lokalizację/)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('still answers without location when permission is denied', async () => {
    deny()
    fetchMock.mockResolvedValue(json(reply))
    render(<ChatView />)

    await ask('Czy grozi mi zalanie?')

    expect(await screen.findByText('Odpowiedź agenta.')).toBeInTheDocument()
    expect(chatBodies()[0].location).toBeNull()
    expect(screen.getByText(/Bez dostępu do lokalizacji/)).toBeInTheDocument()
  })

  it('explains before the first question that location will be requested', () => {
    render(<ChatView />)

    expect(screen.getByText(/przeglądarka zapyta o lokalizację/)).toBeInTheDocument()
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })
})

describe('Map with device location', () => {
  function serveMap(reverse: unknown) {
    fetchMock.mockImplementation(async (input: URL | string) => {
      const url = new URL(String(input))
      if (url.pathname === '/reverse') return json(reverse)
      if (url.pathname === '/shelters/nearest') {
        return json({
          source: 'Test',
          updated_at: null,
          is_stale: false,
          is_simulated: false,
          data: [
            {
              id: 's-1',
              name: 'Schron przy Testowej',
              address: 'Testowa 2',
              lat: 50,
              lon: 19.9,
              capacity: null,
              type: 'shelter',
              distance_m: 420,
            },
          ],
        })
      }
      return new Response('{}', { status: 404 })
    })
  }

  it('shows the nearest shelter for the device location', async () => {
    grant()
    serveMap({
      query: null,
      found: true,
      lat: 50.0312,
      lon: 19.9204,
      display_name: 'Testowa 1, Dębniki',
      district: 'Dębniki',
      in_krakow: true,
    })
    render(<MapView />)

    await userEvent.click(screen.getByRole('button', { name: 'Użyj mojej lokalizacji' }))

    expect(await screen.findByText('Schron przy Testowej')).toBeInTheDocument()
    expect(screen.getByText('420 m od podanego adresu')).toBeInTheDocument()
    const reverseCall = fetchMock.mock.calls.find(([url]) => String(url).includes('/reverse'))
    expect(String(reverseCall?.[0])).toContain('lat=50.0312')
  })

  it('refuses a device location outside Kraków', async () => {
    grant()
    serveMap({
      query: null,
      found: true,
      lat: 49.97,
      lon: 19.83,
      display_name: 'Skawina',
      district: null,
      in_krakow: false,
    })
    render(<MapView />)

    await userEvent.click(screen.getByRole('button', { name: 'Użyj mojej lokalizacji' }))

    expect(
      await screen.findByText('KryzIO działa na razie tylko na terenie Krakowa'),
    ).toBeInTheDocument()
  })

  it('asks for an address when location is denied', async () => {
    deny()
    serveMap({})
    render(<MapView />)

    await userEvent.click(screen.getByRole('button', { name: 'Użyj mojej lokalizacji' }))

    expect(await screen.findByText(/Nie udało się ustalić lokalizacji/)).toBeInTheDocument()
  })
})
