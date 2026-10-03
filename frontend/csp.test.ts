import { describe, expect, it } from 'vitest'
import { buildPolicy } from './csp.js'

describe('Content-Security-Policy', () => {
  const policy = buildPolicy({
    VITE_API_URL: 'https://api.kryzio.test/v1',
    VITE_AGENT_URL: 'https://agent.kryzio.test',
  })
  const directives = Object.fromEntries(
    policy.split('; ').map((d: string) => [d.split(' ')[0], d.split(' ').slice(1)]),
  )

  it('allows scripts only from the own origin', () => {
    expect(directives['script-src']).toEqual(["'self'"])
    expect(policy).not.toContain('unsafe-eval')
  })

  it('limits connections to the app, api and agent origins', () => {
    expect(directives['connect-src']).toEqual([
      "'self'",
      'https://api.kryzio.test',
      'https://agent.kryzio.test',
    ])
  })

  it('allows map tiles and self-hosted fonts only', () => {
    expect(directives['img-src']).toContain('https://tile.openstreetmap.org')
    expect(directives['font-src']).toEqual(["'self'"])
    expect(policy).not.toContain('fonts.googleapis.com')
  })

  it('blocks plugins and base tag hijacking', () => {
    expect(directives['object-src']).toEqual(["'none'"])
    expect(directives['base-uri']).toEqual(["'none'"])
  })
})
