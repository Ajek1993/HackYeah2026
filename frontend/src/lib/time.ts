const TIME_ZONE = 'Europe/Warsaw'

const timeFormat = new Intl.DateTimeFormat('pl-PL', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: TIME_ZONE,
})

// Date and time formatted separately: the joined pl-PL pattern differs between ICU versions.
const dateFormat = new Intl.DateTimeFormat('pl-PL', {
  day: 'numeric',
  month: 'long',
  timeZone: TIME_ZONE,
})

const dayKey = new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE })

function parse(iso: string | null): Date | null {
  if (!iso) return null
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? null : date
}

/** "10:30" for today, "3 października, 10:30" otherwise (Kraków time). */
export function formatUpdatedAt(iso: string | null, now: Date = new Date()): string | null {
  const date = parse(iso)
  if (!date) return null
  const sameDay = dayKey.format(date) === dayKey.format(now)
  const time = timeFormat.format(date)
  return sameDay ? time : `${dateFormat.format(date)}, ${time}`
}

export function hoursSince(iso: string | null, now: Date = new Date()): number | null {
  const date = parse(iso)
  if (!date) return null
  return Math.max(0, Math.floor((now.getTime() - date.getTime()) / 3_600_000))
}
