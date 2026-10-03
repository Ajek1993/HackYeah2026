import { useEffect, useRef, useState, type FormEvent } from 'react'
import { DISCLAIMER } from '../config/emergency'
import { useChat } from '../hooks/useChat'
import type { LocationStatus } from '../lib/geolocation'
import { ExchangeView } from './chat/ExchangeView'

const QUICK_QUESTIONS = [
  'Co spakować na wypadek ewakuacji?',
  'Gdzie jest najbliższy schron?',
  'Czy w mojej okolicy grozi powódź?',
  'Co robić, gdy nie ma prądu?',
]

type Props = {
  /** Replaces the default questions, e.g. with ones fitting the running demo scenario */
  quickQuestions?: string[]
}

export function ChatView({ quickQuestions = QUICK_QUESTIONS }: Props) {
  const { exchanges, pending, ask, retry, reset, locationStatus } = useChat()
  const [message, setMessage] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const lastRef = useRef<HTMLDivElement>(null)
  const started = exchanges.length > 0
  const last = exchanges.at(-1)

  // Bring the newest question into view when it is asked and when its answer arrives.
  useEffect(() => {
    lastRef.current?.scrollIntoView?.({ block: 'start', behavior: 'smooth' })
  }, [exchanges.length, last?.status])

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = message.trim()
    if (!trimmed || pending) return
    ask(trimmed)
    setMessage('')
  }

  function handleReset() {
    reset()
    setMessage('')
    inputRef.current?.focus()
  }

  return (
    <section className="flex flex-col gap-8">
      {!started && (
        <>
          <div className="max-w-[34ch]">
            <h1 className="text-[2rem] font-extrabold leading-[1.15] tracking-tight sm:text-[2.5rem]">
              Co chcesz wiedzieć o bezpieczeństwie w swojej okolicy?
            </h1>
            <p className="mt-3 text-ink-muted">
              Zapytaj własnymi słowami i podaj ulicę albo osiedle. Powiem, co zrobić przed, w
              trakcie i po zdarzeniu.
            </p>
          </div>

          <div>
            <h2 className="mb-3 text-base font-semibold text-ink-muted">Często zadawane pytania</h2>
            <ul className="grid gap-2 sm:grid-cols-2">
              {quickQuestions.map((question) => (
                <li key={question}>
                  <button
                    type="button"
                    onClick={() => ask(question)}
                    disabled={pending}
                    className="min-h-14 w-full rounded-lg border-2 border-line bg-surface px-4 py-3 text-left font-semibold text-vistula-deep hover:border-vistula"
                  >
                    {question}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {started && (
        <div className="flex flex-col gap-10">
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-2xl font-extrabold tracking-tight">Rozmowa</h1>
            <button
              type="button"
              onClick={handleReset}
              className="min-h-12 rounded-lg border-2 border-line bg-surface px-4 font-semibold text-vistula-deep hover:border-vistula"
            >
              Nowa rozmowa
            </button>
          </div>
          {exchanges.map((exchange) => (
            <div
              key={exchange.id}
              ref={exchange.id === last?.id ? lastRef : undefined}
              className="scroll-mt-6"
            >
              <ExchangeView
                exchange={exchange}
                locating={exchange.id === last?.id && locationStatus === 'locating'}
                onRetry={retry}
                retryDisabled={pending}
              />
            </div>
          ))}
        </div>
      )}

      <p aria-live="polite" className="sr-only">
        {last?.status === 'pending' && 'KryzIO sprawdza dane.'}
        {last?.status === 'done' && 'Odpowiedź gotowa.'}
        {last?.status === 'error' && 'Nie udało się uzyskać odpowiedzi.'}
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label htmlFor="question" className="font-semibold">
          {started ? 'Kolejne pytanie' : 'Twoje pytanie'}
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            ref={inputRef}
            id="question"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={
              started
                ? 'np. Mam w domu seniora, co dodać?'
                : 'np. Czy na Kobierzyńskiej grozi zalanie?'
            }
            autoComplete="off"
            maxLength={2000}
            className="min-h-14 flex-1 rounded-lg border-2 border-ink-muted bg-surface px-4 text-lg placeholder:text-ink-muted focus:border-vistula"
          />
          <button
            type="submit"
            disabled={pending}
            className="min-h-14 rounded-lg bg-vistula px-6 text-lg font-semibold text-white hover:bg-vistula-deep disabled:opacity-60"
          >
            {pending ? 'Czekam na odpowiedź' : 'Zapytaj'}
          </button>
        </div>
        <LocationHint status={locationStatus} />
      </form>

      {!started && (
        <p className="border-l-4 border-vistula pl-4 text-sm text-ink-muted">{DISCLAIMER}</p>
      )}
    </section>
  )
}

const LOCATION_HINT: Partial<Record<LocationStatus, string>> = {
  unknown:
    'Przy pierwszym pytaniu przeglądarka zapyta o lokalizację. Jeśli nie podasz adresu, sprawdzę Twoją okolicę.',
  granted: 'Używam Twojej lokalizacji, gdy w pytaniu nie ma adresu.',
  denied: 'Bez dostępu do lokalizacji. Podawaj ulicę albo osiedle w pytaniu.',
  unavailable: 'Nie udało się ustalić lokalizacji. Podawaj ulicę albo osiedle w pytaniu.',
}

function LocationHint({ status }: { status: LocationStatus }) {
  const text = LOCATION_HINT[status]
  if (!text) return null
  return <p className="text-base text-ink-muted">{text}</p>
}
