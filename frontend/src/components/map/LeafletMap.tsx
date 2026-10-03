import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef } from 'react'
import type { PowerOutage, Shelter, Warning } from '../../api/data'
import { formatDistance } from '../../lib/distance'
import { googleMapsDirectionsUrl, NAVIGATE_LABEL, NEW_TAB_HINT } from '../../lib/navigation'
import { APPROXIMATE_NOTE, groupOutages, outageCount, outageTitle } from '../../lib/outages'
import { WARNING_HATCH, WarningHatchDefs } from './warningHatch'

export type LayerId = 'warnings' | 'power' | 'shelters'

export type MapPoint = { lat: number; lon: number; label: string }

type Props = {
  warnings: Warning[]
  outages: PowerOutage[]
  shelters: Shelter[]
  visible: Record<LayerId, boolean>
  address: MapPoint | null
  nearest: Shelter | null
}

const KRAKOW: L.LatLngTuple = [50.0614, 19.9366]

// Civil defence sign (blue triangle on orange), same mark as the logo
const shelterIcon = (highlight: boolean) =>
  L.divIcon({
    className: '',
    iconSize: highlight ? [36, 36] : [26, 26],
    html: `<svg viewBox="0 0 32 32" width="100%" height="100%" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#c2410c" stroke="#fff" stroke-width="${highlight ? 3 : 2}"/>
      <path d="M16 6 27 25H5Z" fill="#1d4e89"/></svg>`,
  })

const addressIcon = L.divIcon({
  className: '',
  iconSize: [28, 28],
  html: '<span style="display:block;width:28px;height:28px;border-radius:50%;background:#1d4e89;border:4px solid #fff;box-shadow:0 0 0 2px #1d4e89"></span>',
})

function escape(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// Popup link to walking directions; starts from the searched address when there is one
function navigateLink(shelter: Shelter, origin: MapPoint | null): string {
  const href = escape(googleMapsDirectionsUrl(shelter, origin))
  return `<p style="margin:8px 0 0"><a href="${href}" target="_blank" rel="noopener noreferrer" class="kryzio-navigate">${NAVIGATE_LABEL}<span class="sr-only"> ${NEW_TAB_HINT}</span></a></p>`
}

export function LeafletMap({ warnings, outages, shelters, visible, address, nearest }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const layers = useRef<Record<LayerId, L.LayerGroup> | null>(null)
  const pinLayer = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!container.current) return
    const instance = L.map(container.current, { scrollWheelZoom: false, zoomControl: false })
    instance.setView(KRAKOW, 12)
    // Polish labels for screen readers (WCAG 3.1.2)
    L.control.zoom({ zoomInTitle: 'Przybliż mapę', zoomOutTitle: 'Oddal mapę' }).addTo(instance)
    instance.on('popupopen', (event) => {
      event.popup
        .getElement()
        ?.querySelector('.leaflet-popup-close-button')
        ?.setAttribute('aria-label', 'Zamknij')
    })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(instance)
    layers.current = {
      warnings: L.layerGroup(),
      power: L.layerGroup(),
      shelters: L.layerGroup(),
    }
    pinLayer.current = L.layerGroup().addTo(instance)
    map.current = instance
    return () => {
      instance.remove()
      map.current = null
    }
  }, [])

  useEffect(() => {
    const group = layers.current?.warnings
    if (!group) return
    group.clearLayers()
    for (const warning of warnings) {
      if (!warning.geometry) continue
      L.geoJSON(warning.geometry, {
        style: { color: '#b42318', weight: 2, fillColor: WARNING_HATCH, fillOpacity: 1 },
      })
        .bindPopup(`<strong>${escape(warning.title)}</strong><br>${escape(warning.area)}`)
        .addTo(group)
    }
  }, [warnings])

  useEffect(() => {
    const group = layers.current?.power
    if (!group) return
    group.clearLayers()
    for (const point of groupOutages(outages)) {
      const items = point.outages
        .map(
          (outage) => `<li><strong>${outageTitle(outage)}</strong><br>${escape(outage.area)}</li>`,
        )
        .join('')
      const count =
        point.outages.length > 1 ? `<strong>${outageCount(point.outages.length)}</strong>` : ''
      const note = point.approximate
        ? `<p style="margin:0 0 6px"><em>${APPROXIMATE_NOTE}</em></p>`
        : ''
      // A district centre is not where the power is off: dashed, translucent marker
      L.circleMarker([point.lat, point.lon], {
        radius: point.approximate ? 14 : 9,
        color: point.approximate ? '#8a5a00' : '#ffffff',
        weight: 2,
        dashArray: point.approximate ? '4 4' : undefined,
        fillColor: '#8a5a00',
        fillOpacity: point.approximate ? 0.35 : 1,
      })
        .bindPopup(
          `${note}${count}<ul style="margin:4px 0 0;padding-left:18px;max-height:220px;overflow-y:auto">${items}</ul>`,
          { maxWidth: 320 },
        )
        .addTo(group)
    }
  }, [outages])

  useEffect(() => {
    const group = layers.current?.shelters
    if (!group) return
    group.clearLayers()
    for (const shelter of shelters) {
      if (shelter.id === nearest?.id) continue
      L.marker([shelter.lat, shelter.lon], { icon: shelterIcon(false), title: shelter.name })
        .bindPopup(
          `<strong>${escape(shelter.name)}</strong><br>${escape(shelter.address)}${navigateLink(shelter, address)}`,
        )
        .addTo(group)
    }
  }, [shelters, nearest, address])

  useEffect(() => {
    const instance = map.current
    if (!instance || !layers.current) return
    for (const [id, group] of Object.entries(layers.current) as [LayerId, L.LayerGroup][]) {
      if (visible[id]) group.addTo(instance)
      else group.remove()
    }
  }, [visible])

  useEffect(() => {
    const instance = map.current
    const pins = pinLayer.current
    if (!instance || !pins) return
    pins.clearLayers()
    if (!address) return

    const points: L.LatLngTuple[] = [[address.lat, address.lon]]
    L.marker(points[0], { icon: addressIcon, title: address.label, zIndexOffset: 1000 })
      .bindPopup(escape(address.label))
      .addTo(pins)

    if (nearest) {
      const shelterPoint: L.LatLngTuple = [nearest.lat, nearest.lon]
      points.push(shelterPoint)
      L.polyline(points, { color: '#c2410c', weight: 4, dashArray: '8 8' }).addTo(pins)
      const distance = nearest.distance_m != null ? `, ${formatDistance(nearest.distance_m)}` : ''
      L.marker(shelterPoint, { icon: shelterIcon(true), title: nearest.name, zIndexOffset: 900 })
        .bindPopup(
          `<strong>${escape(nearest.name)}</strong>${distance}<br>${escape(nearest.address)}${navigateLink(nearest, address)}`,
        )
        .addTo(pins)
    }
    instance.fitBounds(L.latLngBounds(points), { padding: [48, 48], maxZoom: 16 })
  }, [address, nearest])

  // Leaflet panes use z-index 400-1000; `isolate` keeps them under the sticky
  // emergency bar and simulation banner
  return (
    <>
      <WarningHatchDefs />
      <div
        ref={container}
        role="region"
        aria-label="Mapa Krakowa z zagrożeniami i schronami"
        className="isolate h-[60vh] min-h-80 w-full lg:h-[70vh] lg:min-h-[32rem] overflow-hidden rounded-xl border border-line"
      />
    </>
  )
}
