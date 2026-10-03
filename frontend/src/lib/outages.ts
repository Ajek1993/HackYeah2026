import type { PowerOutage } from '../api/data'

export type OutageGroup = {
  lat: number
  lon: number
  approximate: boolean
  outages: PowerOutage[]
}

export const APPROXIMATE_NOTE = 'Lokalizacja przybliżona: Tauron podał tylko rejon energetyczny.'

export const outageTitle = (outage: PowerOutage) =>
  outage.planned ? 'Planowane wyłączenie prądu' : 'Awaria prądu'

/** "2 wyłączenia w tym miejscu", "5 wyłączeń w tym miejscu" (Polish plural). */
export function outageCount(count: number): string {
  const few = count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 12 || count % 100 > 14)
  return `${count} ${few ? 'wyłączenia' : 'wyłączeń'} w tym miejscu`
}

/**
 * One map marker per point: several outages often share coordinates (one address with
 * several time windows, or a whole district published only as its centre).
 */
export function groupOutages(outages: PowerOutage[]): OutageGroup[] {
  const groups = new Map<string, OutageGroup>()
  for (const outage of outages) {
    if (outage.lat == null || outage.lon == null) continue
    const approximate = outage.location_precision === 'approximate'
    const key = `${outage.lat.toFixed(5)},${outage.lon.toFixed(5)},${approximate}`
    const group = groups.get(key)
    if (group) group.outages.push(outage)
    else groups.set(key, { lat: outage.lat, lon: outage.lon, approximate, outages: [outage] })
  }
  return [...groups.values()]
}
