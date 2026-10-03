// Kept in page memory only: reloading the page starts a fresh context (PRD story 1).
export function newSessionId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}
