import { useEffect, useRef, useCallback, useState } from 'react'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

interface UseWebSocketOptions {
  onMessage?: (data: any) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
  reconnect?: boolean
  reconnectDelay?: number
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Keep latest callbacks/options in a ref so `connect` doesn't need to be
  // recreated (and the connection torn down/reopened) on every render.
  const optionsRef = useRef(options)
  optionsRef.current = options

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    const wsUrl = `${WS_BASE}${url}?token=${token}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      optionsRef.current.onOpen?.()
      // Start heartbeat
      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
      ws.onclose = () => {
        clearInterval(heartbeat)
        setIsConnected(false)
        optionsRef.current.onClose?.()
        if (optionsRef.current.reconnect ?? true) {
          reconnectTimerRef.current = setTimeout(connect, optionsRef.current.reconnectDelay ?? 3000)
        }
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        optionsRef.current.onMessage?.(data)
      } catch {}
    }

    ws.onerror = (error) => {
      optionsRef.current.onError?.(error)
    }
  }, [url])

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
    }
    wsRef.current?.close()
    setIsConnected(false)
  }, [])

  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect])

  return { isConnected, send, disconnect }
}

// ─── Driver location hook ──────────────────────────────────
export function useDriverLocationSender(driverId: number | string, deliveryId?: string) {
  const { isConnected, send } = useWebSocket(`/ws/driver/${driverId}`)

  // Auto-send GPS position every 5s if browser supports geolocation
  useEffect(() => {
    if (!isConnected) return
    const watchId = navigator.geolocation?.watchPosition(
      (pos) => {
        send({
          type: 'location_update',
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          speed: pos.coords.speed ?? 0,
          delivery_id: deliveryId,
        })
      },
      undefined,
      { enableHighAccuracy: true, maximumAge: 5000 }
    )
    return () => { if (watchId !== undefined) navigator.geolocation.clearWatch(watchId) }
  }, [isConnected, send, deliveryId])

  const sendLocation = useCallback((lat: number, lng: number, speed?: number) => {
    send({ type: 'location_update', lat, lng, speed, delivery_id: deliveryId })
  }, [send, deliveryId])

  return { isConnected, sendLocation }
}

// ─── Delivery tracking hook ────────────────────────────────
export function useDeliveryTracking(
  deliveryId: string,
  onLocationUpdate: (data: any) => void,
  onDeliveryUpdate: (data: any) => void,
) {
  return useWebSocket(`/ws/track/${deliveryId}`, {
    onMessage: (data) => {
      if (data.type === 'location_update' || data.type === 'initial_location') {
        onLocationUpdate(data)
      } else if (data.type === 'delivery_update') {
        onDeliveryUpdate(data)
      }
    },
  })
}

// ─── Fleet monitoring hook ─────────────────────────────────
export function useFleetMonitor() {
  const [lastEvent, setLastEvent] = useState<any>(null)
  const { isConnected } = useWebSocket('/ws/fleet', {
    onMessage: (data) => setLastEvent(data),
  })
  return { connected: isConnected, lastEvent }
}
