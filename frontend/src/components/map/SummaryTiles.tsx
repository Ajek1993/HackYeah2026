import type { SummaryTile, TileStatus } from '../../api/data'
import { formatUpdatedAt, hoursSince } from '../../lib/time'

const KIND_LABEL: Record<SummaryTile['kind'], string> = {
  warnings: 'Ostrzeżenia',
  water: 'Stan wód',
  air: 'Jakość powietrza',
  power: 'Prąd',
}

// Status is spelled out, never carried by colour alone.
const STATUS: Record<TileStatus, { label: string; tone: string; bar: string }> = {
  ok: { label: 'W normie', tone: 'text-ok', bar: 'bg-ok' },
  warning: { label: 'Uwaga', tone: 'text-caution', bar: 'bg-caution' },
  danger: { label: 'Zagrożenie', tone: 'text-danger', bar: 'bg-danger' },
  no_data: { label: 'Brak danych', tone: 'text-ink-muted', bar: 'bg-line' },
}

export function SummaryTiles({ tiles }: { tiles: SummaryTile[] }) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {tiles.map((tile) => {
        const status = STATUS[tile.status] ?? STATUS.no_data
        const updated = formatUpdatedAt(tile.updated_at)
        const age = hoursSince(tile.updated_at)
        return (
          <li
            key={tile.kind}
            className="relative flex flex-col gap-1 overflow-hidden rounded-lg border border-line bg-surface py-4 pr-4 pl-6"
          >
            <span aria-hidden="true" className={`absolute inset-y-0 left-0 w-2 ${status.bar}`} />
            <h2 className="text-base font-semibold text-ink-muted">{KIND_LABEL[tile.kind]}</h2>
            <p className={`text-lg font-extrabold ${status.tone}`}>{status.label}</p>
            <p className="leading-snug">{tile.headline}</p>
            <p className="mt-1 text-base text-ink-muted">
              {tile.source}
              {updated && `, aktualizacja ${updated}`}
            </p>
            {tile.is_stale && (
              <p className="self-start rounded bg-caution-soft px-2 py-0.5 text-base font-semibold text-caution">
                {age !== null ? `dane sprzed ${age} godz.` : 'dane nieaktualne'}
              </p>
            )}
            {tile.is_simulated && (
              <p className="self-start rounded bg-caution-soft px-2 py-0.5 text-base font-semibold text-caution">
                Dane symulowane
              </p>
            )}
          </li>
        )
      })}
    </ul>
  )
}
