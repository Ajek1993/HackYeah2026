import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ChatError,
  clearSession,
  sendMessage,
  type ChatErrorKind,
  type ChatResponse,
} from '../api/chat'
import { newSessionId } from '../lib/session'

export type Exchange = {
  id: number
  question: string
  status: 'pending' | 'done' | 'error'
  response?: ChatResponse
  error?: ChatErrorKind
}

export function useChat() {
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const sessionId = useRef(newSessionId())
  const nextId = useRef(1)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => () => controller.current?.abort(), [])

  const run = useCallback(async (id: number, question: string) => {
    const abort = new AbortController()
    controller.current = abort
    const update = (patch: Partial<Exchange>) =>
      setExchanges((list) => list.map((item) => (item.id === id ? { ...item, ...patch } : item)))

    try {
      const response = await sendMessage(sessionId.current, question, abort.signal)
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
    void clearSession(sessionId.current)
    sessionId.current = newSessionId()
    setExchanges([])
  }, [])

  return { exchanges, pending, ask, retry, reset }
}
