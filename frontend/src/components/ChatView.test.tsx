import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ChatResponse } from '../api/chat'
import { formatUpdatedAt, hoursSince } from '../lib/time'
import { ChatView } from './ChatView'

const DISCLAIMER = 'KryzIO nie zastępuje komunikatów służb.'

function reply(overrides: Partial<ChatResponse> = {}): ChatResponse {
  return {
    session_id: 'ignored',
    answer: 'Brak ostrzeżeń dla tej okolicy.',
    sections: null,
    sources: [],
    emergency: false,
    out_of_area: false,
    off_topic: false,
    is_simulated: false,
    disclaimer: DISCLAIMER,
    ...overrides,
  }
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

async function ask(question: string) {
  const input = screen.getByRole('textbox')
  await userEvent.clear(input)
  await userEvent.type(input, question)
  await userEvent.click(screen.getByRole('button', { name: 'Zapytaj' }))
}

function postedBodies() {
  return fetchMock.mock.calls
    .filter(([, init]) => init?.method === 'POST')
    .map(([, init]) => JSON.parse(init.body as string))
}

describe('ChatView', () => {
  it('sends the question and shows the answer with its disclaimer', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(reply()))
    render(<ChatView />)

    await ask('Czy na Testowej grozi zalanie?')

    expect(await screen.findByText('Brak ostrzeżeń dla tej okolicy.')).toBeInTheDocument()
    expect(screen.getByText('Czy na Testowej grozi zalanie?')).toBeInTheDocument()
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument()
    expect(postedBodies()[0].message).toBe('Czy na Testowej grozi zalanie?')
  })

  it('links the nearest shelter to walking directions in Google Maps', async () => {
    const shelter = { name: 'Schron testowy', address: 'Testowa 1', distance_m: 420 }
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        reply({
          shelters: [
            { ...shelter, lat: 50.05, lon: 19.94 },
            { name: 'Piwnica testowa', address: '', lat: 50.06, lon: 19.95, distance_m: 900 },
          ],
        }),
      ),
    )
    render(<ChatView />)

    await ask('Gdzie jest najbliższy schron?')

    expect(await screen.findByText('Schron testowy')).toBeInTheDocument()
    expect(screen.getByText('420 m od sprawdzanego miejsca')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /^Nawiguj w Google Maps/ })
    expect(link).toHaveAttribute('target', '_blank')
    const url = new URL(link.getAttribute('href')!)
    expect(url.searchParams.get('destination')).toBe('50.05,19.94')
    expect(url.searchParams.get('travelmode')).toBe('walking')
    expect(screen.getByRole('link', { name: /Piwnica testowa, 900 m/ })).toBeInTheDocument()
  })

  it('shows no directions when the agent found no shelters', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(reply({ shelters: [] })))
    render(<ChatView />)

    await ask('Pytanie')

    await screen.findByText('Brak ostrzeżeń dla tej okolicy.')
    expect(screen.queryByRole('link', { name: /Google Maps/ })).not.toBeInTheDocument()
  })

  it('shows a waiting message until the agent answers', async () => {
    let resolve: (value: Response) => void = () => {}
    fetchMock.mockReturnValueOnce(new Promise<Response>((r) => (resolve = r)))
    render(<ChatView />)

    await ask('Pytanie')

    expect(screen.getByText(/Sprawdzam ostrzeżenia, stany wód i poradnik/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Czekam na odpowiedź' })).toBeDisabled()

    resolve(jsonResponse(reply()))
    expect(await screen.findByText('Brak ostrzeżeń dla tej okolicy.')).toBeInTheDocument()
    expect(screen.queryByText(/Sprawdzam ostrzeżenia/)).not.toBeInTheDocument()
  })

  it('starts without a session and then uses the id issued by the agent', async () => {
    fetchMock.mockResolvedValue(jsonResponse(reply({ session_id: 'issued-by-agent-123' })))
    render(<ChatView />)

    await ask('Mieszkam przy Testowej 1')
    await screen.findByText('Brak ostrzeżeń dla tej okolicy.')
    await ask('Czy grozi mi zalanie?')
    await vi.waitFor(() => expect(postedBodies()).toHaveLength(2))

    const [first, second] = postedBodies()
    expect(first).not.toHaveProperty('session_id')
    expect(second.session_id).toBe('issued-by-agent-123')
  })

  it('shows a rate limit message when asking too often', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'Za dużo' }, 429))
    render(<ChatView />)

    await ask('Pytanie')

    expect(await screen.findByText(/Za dużo pytań naraz/)).toBeInTheDocument()
  })

  it('shows each question as a heading for screen reader navigation', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(reply()))
    render(<ChatView />)

    await ask('Czy grozi zalanie?')

    expect(
      await screen.findByRole('heading', { level: 2, name: /Czy grozi zalanie\?/ }),
    ).toBeInTheDocument()
  })

  it('links a source only when its address is https', async () => {
    const sources = [
      { name: 'IMGW', url: 'https://danepubliczne.imgw.pl/', updated_at: null, is_stale: false },
      { name: 'Podejrzane', url: 'data:text/html,<b>x</b>', updated_at: null, is_stale: false },
      { name: 'Bez TLS', url: 'http://example.test', updated_at: null, is_stale: false },
    ]
    fetchMock.mockResolvedValueOnce(jsonResponse(reply({ sources })))
    render(<ChatView />)

    await ask('Pytanie')

    expect(await screen.findByRole('link', { name: 'IMGW' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Podejrzane' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Bez TLS' })).not.toBeInTheDocument()
    expect(screen.getByText('Podejrzane')).toBeInTheDocument()
  })

  it('renders before / during / after steps when the agent returns sections', async () => {
    const sections = {
      situation: 'Wisła poniżej stanu ostrzegawczego.',
      before: ['Przygotuj dokumenty'],
      during: ['Wyłącz prąd'],
      after: ['Nie pij wody z kranu'],
    }
    fetchMock.mockResolvedValueOnce(jsonResponse(reply({ sections })))
    render(<ChatView />)

    await ask('Pytanie')

    const plan = await screen.findByRole('list', { name: 'Co zrobić' })
    expect(within(plan).getByRole('heading', { name: 'Przed' })).toBeInTheDocument()
    expect(within(plan).getByRole('heading', { name: 'W trakcie' })).toBeInTheDocument()
    expect(within(plan).getByRole('heading', { name: 'Po' })).toBeInTheDocument()
    expect(within(plan).getByText('Wyłącz prąd')).toBeInTheDocument()
    expect(screen.getByText('Wisła poniżej stanu ostrzegawczego.')).toBeInTheDocument()
  })

  it('lists sources with update time and marks stale data', async () => {
    const fresh = new Date(Date.now() - 20 * 60_000).toISOString()
    const stale = new Date(Date.now() - 5 * 3_600_000).toISOString()
    const sources = [
      { name: 'IMGW', url: 'https://danepubliczne.imgw.pl/', updated_at: fresh, is_stale: false },
      { name: 'GIOŚ', url: null, updated_at: stale, is_stale: true },
    ]
    fetchMock.mockResolvedValueOnce(jsonResponse(reply({ sources })))
    render(<ChatView />)

    await ask('Pytanie')

    expect(await screen.findByRole('link', { name: 'IMGW' })).toHaveAttribute(
      'href',
      'https://danepubliczne.imgw.pl/',
    )
    expect(screen.getByText(`aktualizacja ${formatUpdatedAt(fresh)}`)).toBeInTheDocument()
    expect(screen.getByText('dane sprzed 5 godz.')).toBeInTheDocument()
  })

  it('shows the unavailable message with 112 hint and retries on demand', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ error: 'agent_unavailable' }, 503))
      .mockResolvedValueOnce(jsonResponse(reply()))
    render(<ChatView />)

    await ask('Pytanie')

    expect(await screen.findByText('Agent chwilowo niedostępny.')).toBeInTheDocument()
    expect(screen.getByText(/dzwoń/)).toHaveTextContent('112')

    await userEvent.click(screen.getByRole('button', { name: 'Spróbuj ponownie' }))
    expect(await screen.findByText('Brak ostrzeżeń dla tej okolicy.')).toBeInTheDocument()
    expect(postedBodies()).toHaveLength(2)
  })

  it('shows a connection message when the agent cannot be reached', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    render(<ChatView />)

    await ask('Pytanie')

    expect(await screen.findByText(/Brak połączenia z KryzIO/)).toBeInTheDocument()
  })

  it('starts a new conversation and clears the old session in the agent', async () => {
    fetchMock.mockResolvedValue(jsonResponse(reply({ session_id: 'first-session-abc' })))
    render(<ChatView />)

    await ask('Pierwsze pytanie')
    await screen.findByText('Brak ostrzeżeń dla tej okolicy.')

    await userEvent.click(screen.getByRole('button', { name: 'Nowa rozmowa' }))

    expect(screen.queryByText('Pierwsze pytanie')).not.toBeInTheDocument()
    const deleteCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'DELETE')
    expect(deleteCall?.[0]).toContain('/chat/first-session-abc')

    await ask('Drugie pytanie')
    await vi.waitFor(() => expect(postedBodies()).toHaveLength(2))
    expect(postedBodies()[1]).not.toHaveProperty('session_id')
  })

  it('renders answer markdown without injecting HTML', async () => {
    const answer = '**Ważne:** zostań w domu.\n\n- Zamknij okna\n- <img src=x onerror=alert(1)>'
    fetchMock.mockResolvedValueOnce(jsonResponse(reply({ answer })))
    const { container } = render(<ChatView />)

    await ask('Pytanie')

    expect((await screen.findByText('Ważne:')).tagName).toBe('STRONG')
    expect(screen.getByText('Zamknij okna').tagName).toBe('LI')
    expect(container.querySelector('img')).toBeNull()
  })

  it('has no disclaimer under off-topic answers', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        reply({
          answer: 'Pomagam tylko w sprawach bezpieczeństwa.',
          disclaimer: null,
          off_topic: true,
        }),
      ),
    )
    render(<ChatView />)

    await ask('Przepis na pierogi')

    expect(await screen.findByText('Pomagam tylko w sprawach bezpieczeństwa.')).toBeInTheDocument()
    expect(screen.queryByText(DISCLAIMER)).not.toBeInTheDocument()
  })
})

describe('time helpers', () => {
  const now = new Date('2026-10-04T12:00:00+02:00')

  it('formats today as hour only and other days with date', () => {
    expect(formatUpdatedAt('2026-10-04T10:30:00+02:00', now)).toBe('10:30')
    expect(formatUpdatedAt('2026-10-03T10:30:00+02:00', now)).toBe('3 października, 10:30')
    expect(formatUpdatedAt(null, now)).toBeNull()
  })

  it('counts full hours since update', () => {
    expect(hoursSince('2026-10-04T06:30:00+02:00', now)).toBe(5)
    expect(hoursSince('garbage', now)).toBeNull()
  })
})
