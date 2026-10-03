type Point = { lat: number; lon: number }

const coords = (point: Point) => `${point.lat},${point.lon}`

/**
 * Walking directions in Google Maps (Maps URLs, no API key). Without an origin Google
 * starts from the device location itself, so KryzIO never has to ask for it.
 */
export function googleMapsDirectionsUrl(destination: Point, origin?: Point | null): string {
  const params = new URLSearchParams({ api: '1', destination: coords(destination) })
  if (origin) params.set('origin', coords(origin))
  params.set('travelmode', 'walking')
  return `https://www.google.com/maps/dir/?${params}`
}

export const NAVIGATE_LABEL = 'Nawiguj w Google Maps'
// Announced to screen readers: the link leaves the app (WCAG 3.2.5)
export const NEW_TAB_HINT = '(otwiera się w nowej karcie)'
