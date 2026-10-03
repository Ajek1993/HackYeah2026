export type DeviceLocation = { lat: number; lon: number; accuracy_m: number }

export type LocationStatus = 'unknown' | 'locating' | 'granted' | 'denied' | 'unavailable'

export type LocationResult =
  { status: 'granted'; location: DeviceLocation } | { status: 'denied' | 'unavailable' }

/**
 * Asks the browser for the device position. The permission prompt is shown by the browser;
 * a refusal or failure resolves (never rejects) so the chat keeps working without it.
 */
export function requestLocation(timeoutMs = 10_000): Promise<LocationResult> {
  if (typeof navigator === 'undefined' || !navigator.geolocation) {
    return Promise.resolve({ status: 'unavailable' })
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          status: 'granted',
          location: {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            accuracy_m: Math.round(position.coords.accuracy),
          },
        }),
      (error) =>
        resolve({ status: error.code === error.PERMISSION_DENIED ? 'denied' : 'unavailable' }),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 5 * 60_000 },
    )
  })
}
