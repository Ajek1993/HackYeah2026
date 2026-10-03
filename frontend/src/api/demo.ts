import { config } from '../config/env'

// Demo endpoints of the api service (docs_ai/api-contract.md); exist only with DEMO_MODE=true

export type DemoStatus = {
  active: string | null
  expires_at: string | null
}

export type DemoErrorKind = 'forbidden' | 'unavailable'

export class DemoError extends Error {
  readonly kind: DemoErrorKind

  constructor(kind: DemoErrorKind) {
    super(kind)
    this.kind = kind
  }
}

async function request(path: string, method: 'GET' | 'POST'): Promise<DemoStatus> {
  let response: Response
  try {
    response = await fetch(new URL(path, config.apiUrl), {
      method,
      headers: method === 'POST' ? { 'X-Demo-Token': config.demoToken } : undefined,
    })
  } catch {
    throw new DemoError('unavailable')
  }
  if (response.status === 403) throw new DemoError('forbidden')
  if (!response.ok) throw new DemoError('unavailable')
  return (await response.json()) as DemoStatus
}

export const getActiveScenario = () => request('demo/active', 'GET')
export const activateScenario = (id: string) =>
  request(`demo/activate/${encodeURIComponent(id)}`, 'POST')
export const deactivateScenario = () => request('demo/deactivate', 'POST')
