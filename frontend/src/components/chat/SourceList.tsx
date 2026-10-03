import type { Source } from '../../api/chat'
import { formatUpdatedAt, hoursSince } from '../../lib/time'

// Only https links are rendered: source URLs come from the backend and the model's context
function isHttps(url: string | null): boolean {
  if (!url) return false
  try {
    return new URL(url).protocol === 'https:'
  } catch {
    return false
  }
}

export function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) return null

  return (
    <div className="border-t border-line pt-4">
      <h3 className="text-base font-semibold text-ink-muted">Źródła</h3>
      <ul className="mt-2 flex flex-col gap-2">
        {sources.map((source) => {
          const updated = formatUpdatedAt(source.updated_at)
          const age = hoursSince(source.updated_at)
          const name = isHttps(source.url) ? (
            <a
              href={source.url!}
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-vistula underline underline-offset-2 hover:text-vistula-deep"
            >
              {source.name}
            </a>
          ) : (
            <span className="font-semibold">{source.name}</span>
          )
          return (
            <li
              key={`${source.name}-${source.updated_at}`}
              className="flex flex-wrap items-baseline gap-x-2 gap-y-1"
            >
              {name}
              <span className="text-ink-muted">
                {updated ? `aktualizacja ${updated}` : 'brak daty aktualizacji'}
              </span>
              {source.is_stale && (
                <span className="rounded bg-caution-soft px-2 py-0.5 text-base font-semibold text-caution">
                  {age !== null ? `dane sprzed ${age} godz.` : 'dane nieaktualne'}
                </span>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
