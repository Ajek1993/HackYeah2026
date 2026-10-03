import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ChatError,
  clearSession,
  sendMessage,
  type ChatErrorKind,
  type ChatResponse,
} from '../api/chat'
import { requestLocation, type DeviceLocation, type LocationStatus } from '../lib/geolocation'

export type Exchange = {
  id: number
  question: string
  status: 'pending' | 'done' | 'error'
  response?: ChatResponse
  error?: ChatErrorKind
}

export function useChat() {
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  // Issued by the agent with the first answer; kept in page memory only (reload = new context)
  const sessionId = useRef<string | null>(null)
  const nextId = useRef(1)
  const controller = useRef<AbortController | null>(null)
  // Device location lives only in page memory and is asked for once, with the first question.
  const location = useRef<DeviceLocation | null>(null)
  const [locationStatus, setLocationStatus] = useState<LocationStatus>('unknown')
  const locationAsked = useRef(false)

  useEffect(() => () => controller.current?.abort(), [])

  const run = useCallback(async (id: number, question: string) => {
    const abort = new AbortController()
    controller.current = abort
    const update = (patch: Partial<Exchange>) =>
      setExchanges((list) => list.map((item) => (item.id === id ? { ...item, ...patch } : item)))

    if (!locationAsked.current) {
      locationAsked.current = true
      setLocationStatus('locating')
      const result = await requestLocation()
      if (result.status === 'granted') location.current = result.location
      setLocationStatus(result.status)
      if (abort.signal.aborted) return
    }

    try {
      const response = await sendMessage(
        sessionId.current,
        question,
        location.current,
        abort.signal,
      )
      sessionId.current = response.session_id
      update({ status: 'done', response, error: undefined })
    } catch (error) {
      if (abort.signal.aborted) return
      update({ status: 'error', error: error instanceof ChatError ? error.kind : 'network' })
    }
  }, [])

  const pending = exchanges.some((item) => item.status === 'pending')

  const ask = useCallback(
    (question: string) => {
      if (pending) return
      const id = nextId.current++
      setExchanges((list) => [...list, { id, question, status: 'pending' }])
      void run(id, question)
    },
    [pending, run],
  )

  const retry = useCallback(
    (id: number) => {
      const item = exchanges.find((entry) => entry.id === id)
      if (!item || pending) return
      setExchanges((list) =>
        list.map((entry) => (entry.id === id ? { ...entry, status: 'pending' } : entry)),
      )
      void run(id, item.question)
    },
    [exchanges, pending, run],
  )

  const reset = useCallback(() => {
    controller.current?.abort()
    if (sessionId.current) void clearSession(sessionId.current)
    sessionId.current = null
    setExchanges([])
  }, [])

  return { exchanges, pending, ask, retry, reset, locationStatus }
}
