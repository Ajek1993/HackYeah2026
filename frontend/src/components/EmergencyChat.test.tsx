import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ChatResponse } from '../api/chat'
import { looksLikeEmergency } from '../lib/emergency'
import { ChatView } from './ChatView'

function reply(overrides: Partial<ChatResponse> = {}): ChatResponse {
  return {
    session_id: 's',
    answer: 'Odpowiedź agenta.',
    sections: null,
    sources: [],
    emergency: false,
    out_of_area: false,
    off_topic: false,
    is_simulated: false,
    disclaimer: null,
    ...overrides,
  }
}

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => vi.unstubAllGlobals())

async function ask(question: string) {
  await userEvent.type(screen.getByRole('textbox'), question)
  await userEvent.click(screen.getByRole('button', { name: 'Zapytaj' }))
}

const banner = () => screen.queryByRole('link', { name: /Dzwoń 112/ })

describe('Quick questions', () => {
  it('sends the question with one click', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(reply()))
    render(<ChatView />)

    await userEvent.click(screen.getByRole('button', { name: 'Gdzie jest najbliższy schron?' }))

    expect(await screen.findByText('Odpowiedź agenta.')).toBeInTheDocument()
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string)
    expect(body.message).toBe('Gdzie jest najbliższy schron?')
  })
})

describe('112 banner', () => {
  it('appears from keywords before the agent answers', async () => {
    fetchMock.mockReturnValueOnce(new Promise(() => {}))
    render(<ChatView />)

    await ask('Woda wlewa się do piwnicy, mama nie może zejść!')

    expect(banner()).toHaveAttribute('href', 'tel:112')
    expect(screen.getByText(/Sprawdzam ostrzeżenia/)).toBeInTheDocument()
  })

  it('stays visible when the agent is unavailable', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ error: 'agent_unavailable' }, 503))
    render(<ChatView />)

    await ask('Pali się w kuchni')

    expect(await screen.findByText('Agent chwilowo niedostępny.')).toBeInTheDocument()
    expect(banner()).toBeInTheDocument()
  })

  it('appears when the agent flags an emergency without keywords', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(reply({ emergency: true })))
    render(<ChatView />)

    await ask('Mama źle się czuje po powodzi, co teraz?')

    expect(await screen.findByText('Odpowiedź agenta.')).toBeInTheDocument()
    expect(banner()).toBeInTheDocument()
  })

  it('does not appear for preparedness questions', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(reply()))
    render(<ChatView />)

    await ask('Jak się przygotować na pożar?')

    expect(await screen.findByText('Odpowiedź agenta.')).toBeInTheDocument()
    expect(banner()).not.toBeInTheDocument()
  })
})

describe('looksLikeEmergency', () => {
  it.each([
    'Woda wlewa się do piwnicy',
    'POŻAR W KUCHNI',
    'czuć gaz na klatce',
    'sąsiad jest nieprzytomny',
    'pali sie dom obok',
    'Ratunku!',
  ])('detects "%s"', (text) => {
    expect(looksLikeEmergency(text)).toBe(true)
  })

  it.each([
    'Jak się przygotować na pożar?',
    'Co spakować na wypadek ewakuacji?',
    'Czy w mojej okolicy grozi powódź?',
    'Co robić, gdy nie ma prądu?',
    'Gdzie jest najbliższy schron?',
  ])('ignores "%s"', (text) => {
    expect(looksLikeEmergency(text)).toBe(false)
  })
})
