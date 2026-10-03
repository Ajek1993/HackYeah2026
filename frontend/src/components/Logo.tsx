export function Logo() {
  return (
    <div className="flex items-center gap-3">
      <img src="/logo.png" alt="" width={48} height={48} className="size-12 shrink-0" />
      <div className="leading-tight">
        <p className="text-2xl font-extrabold tracking-tight">
          Kryz<span className="text-civil">IO</span>
        </p>
        <p className="text-sm text-ink-muted">Bezpieczeństwo mieszkańców Krakowa</p>
      </div>
    </div>
  )
}
