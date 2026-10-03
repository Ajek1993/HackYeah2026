import { describe, expect, it } from 'vitest'
import type { PowerOutage } from '../api/data'
import { groupOutages, outageCount } from './outages'

const outage = (overrides: Partial<PowerOutage>): PowerOutage => ({
  id: 'o-1',
  planned: true,
  area: 'Kraków ul. Litewska 23',
  start: null,
  end: null,
  lat: 50.0771,
  lon: 19.9253,
  location_precision: 'street',
  ...overrides,
})

describe('groupOutages', () => {
  it('puts outages from one point under one marker', () => {
    const groups = groupOutages([
      outage({ id: 'a', lat: 50.0617, lon: 19.9373, location_precision: 'approximate' }),
      outage({ id: 'b', lat: 50.0617, lon: 19.9373, location_precision: 'approximate' }),
      outage({ id: 'c' }),
    ])

    expect(groups).toHaveLength(2)
    expect(groups[0]).toMatchObject({ approximate: true })
    expect(groups[0].outages.map((o) => o.id)).toEqual(['a', 'b'])
    expect(groups[1]).toMatchObject({ approximate: false, lat: 50.0771 })
  })

  it('keeps an approximate district centre apart from a street at the same point', () => {
    const groups = groupOutages([
      outage({ id: 'a', location_precision: 'approximate' }),
      outage({ id: 'b', location_precision: 'exact' }),
    ])

    expect(groups.map((g) => g.approximate)).toEqual([true, false])
  })

  it('skips outages without coordinates', () => {
    expect(groupOutages([outage({ lat: null, lon: null })])).toEqual([])
  })
})

describe('outageCount', () => {
  it.each([
    [2, '2 wyłączenia w tym miejscu'],
    [4, '4 wyłączenia w tym miejscu'],
    [5, '5 wyłączeń w tym miejscu'],
    [12, '12 wyłączeń w tym miejscu'],
    [22, '22 wyłączenia w tym miejscu'],
  ])('%i -> %s', (count, text) => {
    expect(outageCount(count)).toBe(text)
  })
})
