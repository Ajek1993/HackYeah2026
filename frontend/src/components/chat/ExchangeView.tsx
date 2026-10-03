import type { Exchange } from '../../hooks/useChat'
import { looksLikeEmergency } from '../../lib/emergency'
import { ActionPlan } from './ActionPlan'
import { EmergencyBanner } from './EmergencyBanner'
import { RichText } from './RichText'
import { SourceList } from './SourceList'

const ERROR_TEXT = {
  unavailable: 'Agent chwilowo niedostępny.',
  network: 'Brak połączenia z KryzIO. Sprawdź internet i spróbuj ponownie.',
}

type Props = {
  exchange: Exchange
  locating?: boolean
  onRetry: (id: number) => void
  retryDisabled: boolean
}

export function ExchangeView({ exchange, locating = false, onRetry, retryDisabled }: Props) {
  const { question, status, response, error } = exchange
  // Keyword fallback shows the banner at once, without waiting for (or despite failure of) the agent.
  const emergency = Boolean(response?.emergency) || looksLikeEmergency(question)

  return (
    <article aria-label={`Pytanie: ${question}`} className="flex flex-col gap-4">
      <p className="self-start rounded-lg bg-vistula-soft px-4 py-3 font-semibold text-vistula-deep">
        <span className="sr-only">Twoje pytanie: </span>
        {question}
      </p>

      {emergency && <EmergencyBanner />}

      {status === 'pending' && (
        <div className="flex items-center gap-3 text-ink-muted">
          <span aria-hidden="true" className="flex gap-1.5">
            {[0, 1, 2].map((dot) => (
              <span
                key={dot}
                className="size-2.5 animate-pulse rounded-full bg-vistula"
                style={{ animationDelay: `${dot * 200}ms` }}
              />
            ))}
          </span>
          <p>
            {locating
              ? 'Czekam na zgodę na lokalizację. Dzięki niej sprawdzę Twoją okolicę bez podawania adresu.'
              : 'Sprawdzam ostrzeżenia, stany wód i poradnik. To może potrwać do pół minuty.'}
          </p>
        </div>
      )}

      {status === 'error' && error && (
        <div className="flex flex-col gap-3 rounded-lg border-2 border-danger bg-danger-soft p-4">
          <p className="font-semibold text-danger">{ERROR_TEXT[error]}</p>
          <p>
            Jeśli coś zagraża życiu lub zdrowiu, dzwoń <strong>112</strong> — numery alarmowe są
            zawsze na dole ekranu.
          </p>
          <button
            type="button"
            onClick={() => onRetry(exchange.id)}
            disabled={retryDisabled}
            className="min-h-12 self-start rounded-lg bg-vistula px-5 font-semibold text-white hover:bg-vistula-deep disabled:opacity-60"
          >
            Spróbuj ponownie
          </button>
        </div>
      )}

      {status === 'done' && response && (
        <div className="flex flex-col gap-5 rounded-xl border border-line bg-surface p-5 sm:p-6">
          {response.is_simulated && (
            <p className="self-start rounded bg-caution-soft px-2 py-0.5 font-semibold text-caution">
              Dane symulowane
            </p>
          )}
          {response.sections ? (
            <ActionPlan sections={response.sections} />
          ) : (
            <RichText text={response.answer} />
          )}
          <SourceList sources={response.sources} />
          {response.disclaimer && (
            <p className="border-l-4 border-vistula pl-4 text-base text-ink-muted">
              {response.disclaimer}
            </p>
          )}
        </div>
      )}
    </article>
  )
}
