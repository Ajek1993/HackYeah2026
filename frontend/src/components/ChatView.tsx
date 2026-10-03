import { useState, type FormEvent } from 'react'
import { DISCLAIMER } from '../config/emergency'

const QUICK_QUESTIONS = [
  'Co spakować na wypadek ewakuacji?',
  'Gdzie jest najbliższy schron?',
  'Czy w mojej okolicy grozi powódź?',
  'Co robić, gdy nie ma prądu?',
]

type Props = {
  onAsk?: (message: string) => void
}

export function ChatView({ onAsk }: Props) {
  const [message, setMessage] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = message.trim()
    if (!trimmed) return
    onAsk?.(trimmed)
  }

  return (
    <section className="flex flex-col gap-8">
      <div className="max-w-[34ch]">
        <h1 className="text-[2rem] font-extrabold leading-[1.15] tracking-tight sm:text-[2.5rem]">
          Co chcesz wiedzieć o bezpieczeństwie w swojej okolicy?
        </h1>
        <p className="mt-3 text-ink-muted">
          Zapytaj własnymi słowami i podaj ulicę albo osiedle. Powiem, co zrobić przed, w trakcie i
          po zdarzeniu.
        </p>
      </div>

      <div>
        <h2 className="mb-3 text-base font-semibold text-ink-muted">Często zadawane pytania</h2>
        <ul className="grid gap-2 sm:grid-cols-2">
          {QUICK_QUESTIONS.map((question) => (
            <li key={question}>
              <button
                type="button"
                onClick={() => setMessage(question)}
                className="min-h-14 w-full rounded-lg border-2 border-line bg-surface px-4 py-3 text-left font-semibold text-vistula-deep hover:border-vistula"
              >
                {question}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label htmlFor="question" className="font-semibold">
          Twoje pytanie
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id="question"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="np. Czy na Kobierzyńskiej grozi zalanie?"
            autoComplete="off"
            className="min-h-14 flex-1 rounded-lg border-2 border-ink-muted bg-surface px-4 text-lg placeholder:text-ink-muted focus:border-vistula"
          />
          <button
            type="submit"
            className="min-h-14 rounded-lg bg-vistula px-6 text-lg font-semibold text-white hover:bg-vistula-deep"
          >
            Zapytaj
          </button>
        </div>
      </form>

      <p className="border-l-4 border-vistula pl-4 text-sm text-ink-muted">{DISCLAIMER}</p>
    </section>
  )
}
