import { useEffect, useRef, useState, useCallback } from 'react'
import { io, Socket } from 'socket.io-client'
import { useStore } from '../store'
import toast from 'react-hot-toast'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

interface WSMessage {
  type: string
  data?: any
  timestamp?: string
}

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false)
  const socketRef = useRef<Socket | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10

  const addNotification = useStore(state => state.addNotification)
  const updatePrice = useStore(state => state.updatePrice)
  const addPrediction = useStore(state => state.addPrediction)
  const addNews = useStore(state => state.addNews)
  const updateSentiment = useStore(state => state.updateSentiment)

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return

    socketRef.current = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
    })

    socketRef.current.on('connect', () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      reconnectAttempts.current = 0

      // Subscribe to all topics
      socketRef.current?.emit('message', {
        type: 'subscribe',
        topics: ['predictions', 'news', 'prices', 'sentiment', 'all']
      })
    })

    socketRef.current.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
      setIsConnected(false)
    })

    socketRef.current.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      reconnectAttempts.current++
      if (reconnectAttempts.current >= maxReconnectAttempts) {
        toast.error('Failed to connect to server')
      }
    })

    socketRef.current.on('message', (data: WSMessage) => {
      handleMessage(data)
    })

    socketRef.current.on('new_prediction', (data: any) => {
      addPrediction(data)
      addNotification({
        type: 'prediction',
        title: 'New Prediction',
        message: `${data.pair} - ${data.direction.toUpperCase()} (${(data.confidence * 100).toFixed(0)}%)`,
      })
    })

    socketRef.current.on('new_news', (data: any) => {
      addNews(data)
      addNotification({
        type: 'news',
        title: 'Breaking News',
        message: data.title,
      })
    })

    socketRef.current.on('price_update', (data: any) => {
      updatePrice(data.pair, data.data)
    })

    socketRef.current.on('sentiment_update', (data: any) => {
      updateSentiment(data.pair, data.data)
    })

    socketRef.current.on('prediction_resolved', (data: any) => {
      addNotification({
        type: data.outcome === 'correct' ? 'success' : 'warning',
        title: 'Prediction Resolved',
        message: `${data.pair} - ${data.outcome.toUpperCase()} (${data.profit_loss_pips?.toFixed(1)} pips)`,
      })
    })
  }, [addNotification, updatePrice, addPrediction, addNews, updateSentiment])

  const handleMessage = (data: WSMessage) => {
    switch (data.type) {
      case 'predictions':
        if (data.data) {
          data.data.forEach((p: any) => addPrediction(p))
        }
        break
      case 'news':
        if (data.data) {
          data.data.forEach((n: any) => addNews(n))
        }
        break
      case 'prices':
        if (data.data) {
          data.data.forEach((p: any) => updatePrice(p.pair, p))
        }
        break
      case 'sentiment':
        if (data.data) {
          Object.entries(data.data).forEach(([pair, sentiment]: [string, any]) => {
            updateSentiment(pair, sentiment)
          })
        }
        break
      case 'heartbeat':
        // Connection alive
        break
      case 'error':
        toast.error(data.data?.message || 'Server error')
        break
    }
  }

  const send = useCallback((message: any) => {
    socketRef.current?.emit('message', message)
  }, [])

  const subscribe = useCallback((topics: string[]) => {
    send({ type: 'subscribe', topics })
  }, [send])

  const unsubscribe = useCallback((topics: string[]) => {
    send({ type: 'unsubscribe', topics })
  }, [send])

  const getLatest = useCallback((topic: string) => {
    send({ type: 'get_latest', topic })
  }, [send])

  useEffect(() => {
    connect()

    return () => {
      socketRef.current?.disconnect()
    }
  }, [connect])

  return {
    isConnected,
    send,
    subscribe,
    unsubscribe,
    getLatest,
    socket: socketRef.current,
  }
}