// Mark based on the international civil defence sign: blue triangle on orange
export function Logo() {
  return (
    <div className="flex items-center gap-3">
      <svg viewBox="0 0 32 32" className="size-10 shrink-0" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="var(--color-civil)" />
        <path d="M16 6 27 25H5Z" fill="var(--color-vistula)" />
      </svg>
      <div className="leading-tight">
        <p className="text-2xl font-extrabold tracking-tight">KryzIO</p>
        <p className="text-sm text-ink-muted">Bezpieczeństwo mieszkańców Krakowa</p>
      </div>
    </div>
  )
}
