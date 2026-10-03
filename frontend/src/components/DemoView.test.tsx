import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { DEMO_SCENARIOS } from '../config/demo'

const INACTIVE = { active: null, expires_at: null }
const inMinutes = (minutes: number) => new Date(Date.now() + minutes * 60_000).toISOString()

let fetchMock: ReturnType<typeof vi.fn>
let current: { active: string | null; expires_at: string | null }

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  current = INACTIVE
  fetchMock = vi.fn(async (input: URL | string, init?: RequestInit) => {
    const path = new URL(String(input)).pathname
    if (path === '/demo/active') return json(current)
    if (path.startsWith('/demo/activate/')) {
      current = { active: path.split('/').at(-1)!, expires_at: inMinutes(30) }
      return json(current)
    }
    if (path === '/demo/deactivate') {
      current = INACTIVE
      return json(current)
    }
    if (path === '/chat' && init?.method === 'POST') {
      return json({
        session_id: 'session-from-agent-1',
        answer: 'Udaj się do najbliższego schronu.',
        sections: null,
        sources: [],
        emergency: false,
        out_of_area: false,
        off_topic: false,
        is_simulated: true,
        disclaimer: null,
      })
    }
    return json({}, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => vi.unstubAllGlobals())

const banner = () => screen.queryByRole('complementary', { name: 'Symulacja' })

async function openDemo() {
  render(<App demoMode />)
  await userEvent.click(screen.getByRole('tab', { name: 'Demo' }))
}

async function start(title: string) {
  await userEvent.click(screen.getByRole('button', { name: new RegExp(`^${title}`) }))
  await screen.findByRole('button', { name: new RegExp(`^${title}.*Trwa`) })
}

describe('Demo tab', () => {
  it('lists the three scenarios with no banner before one starts', async () => {
    await openDemo()

    const list = screen.getByRole('list', { name: 'Scenariusze' })
    expect(within(list).getAllByRole('button')).toHaveLength(3)
    expect(banner()).not.toBeInTheDocument()
  })

  it('starts a scenario with the demo token and shows the banner on every tab', async () => {
    await openDemo()
    await start('Atak bombowy')

    const [url, init] = fetchMock.mock.calls.find(([u]) => String(u).includes('/activate/'))!
    expect(String(url)).toContain('/demo/activate/bomb_threat')
    expect(init.method).toBe('POST')
    expect(init.headers).toHaveProperty('X-Demo-Token')
    expect(banner()).toHaveTextContent('SYMULACJA')
    expect(banner()).toHaveTextContent('To nie jest prawdziwy alarm')
    expect(banner()).toHaveTextContent('Scenariusz: Atak bombowy')

    await userEvent.click(screen.getByRole('button', { name: 'Otwórz mapę' }))
    expect(screen.getByRole('tab', { name: 'Mapa' })).toHaveAttribute('aria-selected', 'true')
    expect(banner()).toBeInTheDocument()
  })

  it('offers questions that fit the scenario in the chat', async () => {
    await openDemo()
    await start('Atak bombowy')
    await userEvent.click(screen.getByRole('button', { name: 'Otwórz czat' }))

    const question = DEMO_SCENARIOS.find((s) => s.id === 'bomb_threat')!.questions[0]
    await userEvent.click(screen.getByRole('button', { name: question }))

    expect(await screen.findByText('Udaj się do najbliższego schronu.')).toBeInTheDocument()
    expect(screen.getByText('Dane symulowane')).toBeInTheDocument()
  })

  it('ending the simulation resets the chat and removes the banner', async () => {
    await openDemo()
    await start('Powódź')
    await userEvent.click(screen.getByRole('button', { name: 'Otwórz czat' }))
    await userEvent.click(screen.getByRole('button', { name: 'Woda podchodzi pod dom. Co robić?' }))
    await screen.findByText('Udaj się do najbliższego schronu.')

    await userEvent.click(screen.getByRole('button', { name: 'Zakończ symulację' }))

    await waitFor(() => expect(banner()).not.toBeInTheDocument())
    expect(screen.queryByText('Udaj się do najbliższego schronu.')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Gdzie jest najbliższy schron?' })).toBeVisible()
  })

  it('switching scenarios starts the chat over', async () => {
    await openDemo()
    await start('Powódź')
    await userEvent.click(screen.getByRole('button', { name: 'Otwórz czat' }))
    await userEvent.click(screen.getByRole('button', { name: 'Woda podchodzi pod dom. Co robić?' }))
    await screen.findByText('Udaj się do najbliższego schronu.')

    await userEvent.click(screen.getByRole('tab', { name: 'Demo' }))
    await start('Brak prądu')
    await userEvent.click(screen.getByRole('button', { name: 'Otwórz czat' }))

    expect(screen.queryByText('Udaj się do najbliższego schronu.')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nie mam prądu od rana. Co robić?' })).toBeVisible()
    expect(banner()).toHaveTextContent('Scenariusz: Brak prądu')
  })

  it('restores a running scenario after a reload', async () => {
    current = { active: 'flood', expires_at: inMinutes(10) }
    render(<App demoMode />)

    expect(await screen.findByRole('complementary', { name: 'Symulacja' })).toHaveTextContent(
      'Scenariusz: Powódź',
    )
  })

  it('drops the banner when the scenario expires on the api', async () => {
    current = { active: 'flood', expires_at: new Date(Date.now() + 200).toISOString() }
    render(<App demoMode />)
    await screen.findByRole('complementary', { name: 'Symulacja' })

    await waitFor(() => expect(banner()).not.toBeInTheDocument(), { timeout: 2000 })
  })

  it('explains a rejected demo token', async () => {
    await openDemo()
    fetchMock.mockResolvedValueOnce(json({ detail: 'Brak uprawnień' }, 403))

    await userEvent.click(screen.getByRole('button', { name: /^Powódź/ }))

    expect(await screen.findByText(/Serwer odrzucił token demo/)).toBeInTheDocument()
    expect(banner()).not.toBeInTheDocument()
  })

  it('never asks the api about the demo when demo mode is off', () => {
    render(<App demoMode={false} />)

    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/demo/'))).toBe(false)
  })
})
