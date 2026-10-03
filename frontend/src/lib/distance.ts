const km = new Intl.NumberFormat('pl-PL', { maximumFractionDigits: 1 })

/** "350 m" below a kilometre, "1,2 km" above. */
export function formatDistance(metres: number): string {
  if (metres < 1000) return `${Math.round(metres / 10) * 10} m`
  return `${km.format(metres / 1000)} km`
}
