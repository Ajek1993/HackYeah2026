import { config } from '../config/env'
import type { DeviceLocation } from '../lib/geolocation'

export type Sections = {
  situation: string
  before: string[]
  during: string[]
  after: string[]
}

export type Source = {
  name: string
  url: string | null
  updated_at: string | null
  is_stale: boolean
}

export type ChatShelter = {
  name: string
  address: string
  lat: number
  lon: number
  distance_m: number | null
}

// Shape of agent POST /chat (docs_ai/api-contract.md)
export type ChatResponse = {
  session_id: string
  answer: string
  sections: Sections | null
  sources: Source[]
  /** Nearest first; empty unless the agent looked shelters up. Optional for older agents. */
  shelters?: ChatShelter[]
  emergency: boolean
  out_of_area: boolean
  off_topic: boolean
  is_simulated: boolean
  disclaimer: string | null
}

export type ChatErrorKind = 'unavailable' | 'network' | 'rate_limited'

export class ChatError extends Error {
  readonly kind: ChatErrorKind

  constructor(kind: ChatErrorKind) {
    super(kind)
    this.kind = kind
  }
}

/** `sessionId` is null for the first question; the agent issues one in its answer. */
export async function sendMessage(
  sessionId: string | null,
  message: string,
  location: DeviceLocation | null,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  let response: Response
  try {
    response = await fetch(`${config.agentUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...(sessionId ? { session_id: sessionId } : {}), message, location }),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ChatError('network')
  }
  if (response.status === 429) throw new ChatError('rate_limited')
  if (!response.ok) throw new ChatError('unavailable')
  return (await response.json()) as ChatResponse
}

export async function clearSession(sessionId: string): Promise<void> {
  try {
    await fetch(`${config.agentUrl}/chat/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
  } catch {
    // Context expires on the agent anyway (TTL); nothing for the user to do.
  }
}
