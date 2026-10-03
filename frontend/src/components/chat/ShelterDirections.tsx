import type { ChatShelter } from '../../api/chat'
import { formatDistance } from '../../lib/distance'
import { googleMapsDirectionsUrl, NAVIGATE_LABEL, NEW_TAB_HINT } from '../../lib/navigation'
import { ExternalIcon } from '../ExternalIcon'

/**
 * Directions to the shelters the agent looked up. Without an origin Google Maps starts
 * from the device location, which is where the person asking usually is.
 */
export function ShelterDirections({ shelters }: { shelters: ChatShelter[] }) {
  if (!shelters.length) return null
  const [nearest, ...others] = shelters

  return (
    <div className="flex flex-col gap-4 rounded-lg border-2 border-civil p-4">
      <div>
        <h3 className="text-base text-ink-muted">Najbliższy schron</h3>
        <p className="text-xl font-extrabold">{nearest.name}</p>
        {nearest.address && <p>{nearest.address}</p>}
        {nearest.distance_m != null && (
          <p className="mt-1 text-lg font-semibold text-civil-deep">
            {formatDistance(nearest.distance_m)} od sprawdzanego miejsca
          </p>
        )}
        <a
          href={googleMapsDirectionsUrl(nearest)}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex min-h-12 items-center gap-2 rounded-lg bg-vistula px-5 font-semibold text-white hover:bg-vistula-deep"
        >
          {NAVIGATE_LABEL}
          <ExternalIcon />
          <span className="sr-only">{NEW_TAB_HINT}</span>
        </a>
      </div>

      {others.length > 0 && (
        <div className="border-t border-line pt-3">
          <h3 className="text-base text-ink-muted">Kolejne w pobliżu</h3>
          <ul className="mt-2 flex flex-col gap-2">
            {others.map((shelter) => (
              <li key={`${shelter.lat},${shelter.lon}`}>
                <a
                  href={googleMapsDirectionsUrl(shelter)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-12 items-center gap-2 font-semibold text-vistula underline underline-offset-2 hover:text-vistula-deep"
                >
                  {shelter.address || shelter.name}
                  {shelter.distance_m != null && `, ${formatDistance(shelter.distance_m)}`}
                  <ExternalIcon />
                  <span className="sr-only">
                    {NAVIGATE_LABEL} {NEW_TAB_HINT}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
