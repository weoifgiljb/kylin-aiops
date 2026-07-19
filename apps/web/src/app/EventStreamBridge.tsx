import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { streamEvents } from '../api/client'

export function EventStreamBridge() {
  const queryClient = useQueryClient()
  useEffect(() => {
    const controller = new AbortController()
    const reconnect = () => {
      if (controller.signal.aborted) return
      void streamEvents(controller.signal, () => {
        void queryClient.invalidateQueries({ queryKey: ['overview'] })
        void queryClient.invalidateQueries({ queryKey: ['incidents'] })
      }).catch(() => {
        if (!controller.signal.aborted) window.setTimeout(reconnect, 3000)
      })
    }
    reconnect()
    return () => controller.abort()
  }, [queryClient])
  return null
}
