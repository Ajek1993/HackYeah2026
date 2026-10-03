import type { GeoJsonObject } from 'geojson'
import { config } from '../config/env'

// Shapes of the api service (docs_ai/api-contract.md)

export type Envelope<T> = {
  source: string
  source_url?: string | null
  updated_at: string | null
  is_stale: boolean
  is_simulated: boolean
  data: T | null
}

export type TileStatus = 'ok' | 'warning' | 'danger' | 'no_data'

export type SummaryTile = {
  kind: 'warnings' | 'water' | 'air' | 'power'
  status: TileStatus
  headline: string
  source: string
  updated_at: string | null
  is_stale: boolean
  is_simulated: boolean
}

export type Summary = {
  generated_at: string
  demo_scenario: string | null
  tiles: SummaryTile[]
}

export type GeocodeResult = {
  query: string
  found: boolean
  lat: number | null
  lon: number | null
  display_name: string | null
  district: string | null
  in_krakow: boolean | null
}

export type Warning = {
  id: string
  kind: string
  level: number
  title: string
  description: string
  area: string
  valid_from: string | null
  valid_to: string | null
  geometry: GeoJsonObject | null
}

export type PowerOutage = {
  id: string
  planned: boolean
  area: string
  start: string | null
  end: string | null
  lat: number | null
  lon: number | null
  // exact: Tauron coordinates; street: first address of the message; approximate: district centre
  location_precision: 'exact' | 'street' | 'approximate'
}

export type Shelter = {
  id: string
  name: string
  address: string
  lat: number
  lon: number
  capacity: number | null
  type: 'shelter' | 'hiding_place'
  distance_m?: number
}

export class ApiError extends Error {}

async function getJson<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(path, config.apiUrl)
  for (const [key, value] of Object.entries(params ?? {})) url.searchParams.set(key, String(value))
  let response: Response
  try {
    response = await fetch(url)
  } catch {
    throw new ApiError('network')
  }
  if (!response.ok) throw new ApiError(String(response.status))
  return (await response.json()) as T
}

export const getSummary = () => getJson<Summary>('/summary')
export const getShelters = () => getJson<Envelope<Shelter[]>>('/shelters')
export const getWarnings = () => getJson<Envelope<Warning[]>>('/warnings')
export const getPowerOutages = () => getJson<Envelope<PowerOutage[]>>('/power-outages')
export const geocode = (query: string) => getJson<GeocodeResult>('/geocode', { q: query })
export const reverseGeocode = (lat: number, lon: number) =>
  getJson<GeocodeResult>('/reverse', { lat, lon })
export const getNearestShelters = (lat: number, lon: number, limit = 1) =>
  getJson<Envelope<Shelter[]>>('/shelters/nearest', { lat, lon, limit })
