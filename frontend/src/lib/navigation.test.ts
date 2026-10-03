import { describe, expect, it } from 'vitest'
import { googleMapsDirectionsUrl } from './navigation'

describe('googleMapsDirectionsUrl', () => {
  it('leads on foot from the searched address to the shelter', () => {
    const url = new URL(
      googleMapsDirectionsUrl({ lat: 50.034, lon: 19.92 }, { lat: 50.031, lon: 19.921 }),
    )

    expect(url.origin + url.pathname).toBe('https://www.google.com/maps/dir/')
    expect(Object.fromEntries(url.searchParams)).toEqual({
      api: '1',
      destination: '50.034,19.92',
      origin: '50.031,19.921',
      travelmode: 'walking',
    })
  })

  it('leaves the start to Google without an address', () => {
    const url = new URL(googleMapsDirectionsUrl({ lat: 50.034, lon: 19.92 }))

    expect(url.searchParams.has('origin')).toBe(false)
    expect(url.searchParams.get('destination')).toBe('50.034,19.92')
  })
})
