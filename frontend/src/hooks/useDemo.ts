import { useCallback, useEffect, useState } from 'react'
import {
  activateScenario,
  deactivateScenario,
  DemoError,
  getActiveScenario,
  type DemoErrorKind,
  type DemoStatus,
} from '../api/demo'

const INACTIVE: DemoStatus = { active: null, expires_at: null }

/** Active demo scenario; it is global on the api, so every tab reads data from it. */
export function useDemo(enabled: boolean) {
  const [status, setStatus] = useState<DemoStatus>(INACTIVE)
  const [switching, setSwitching] = useState(false)
  const [error, setError] = useState<DemoErrorKind | null>(null)

  // Restore the banner after a reload while a scenario is still running
  useEffect(() => {
    if (!enabled) return
    let current = true
    getActiveScenario()
      .then((result) => current && setStatus(result))
      .catch(() => {})
    return () => {
      current = false
    }
  }, [enabled])

  // The api switches back to real data after its TTL; follow it without polling
  useEffect(() => {
    if (!status.expires_at) return
    const left = new Date(status.expires_at).getTime() - Date.now()
    const timer = setTimeout(() => setStatus(INACTIVE), Math.max(left, 0))
    return () => clearTimeout(timer)
  }, [status.expires_at])

  const run = useCallback(async (call: () => Promise<DemoStatus>) => {
    setSwitching(true)
    setError(null)
    try {
      setStatus(await call())
    } catch (failure) {
      setError(failure instanceof DemoError ? failure.kind : 'unavailable')
    } finally {
      setSwitching(false)
    }
  }, [])

  const activate = useCallback((id: string) => run(() => activateScenario(id)), [run])
  const deactivate = useCallback(() => run(deactivateScenario), [run])

  return {
    active: status.active,
    expiresAt: status.expires_at,
    switching,
    error,
    activate,
    deactivate,
  }
}

export type Demo = ReturnType<typeof useDemo>
