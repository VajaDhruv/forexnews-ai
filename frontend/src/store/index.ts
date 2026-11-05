import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface PriceData {
  pair: string
  bid: number
  ask: number
  spread: number
  timestamp: string
  change_24h: number
  change_24h_percent: number
  high_24h: number
  low_24h: number
}

export interface PredictionData {
  id: string
  news_id: string
  pair: string
  horizon_minutes: number
  direction: 'up' | 'down' | 'sideways'
  confidence: number
  expected_move_pips: number
  expected_move_percent: number
  entry_price: number
  target_price: number
  stop_loss: number
  risk_reward_ratio: number
  predicted_at: string
  expires_at: string
  model_version: string
}

export interface NewsData {
  id: string
  title: string
  summary: string
  url: string
  source: string
  published_at: string
  related_pairs: string[]
  impact_level: 'low' | 'medium' | 'high' | 'critical'
  categories: string[]
  sentiment_score: number
  sentiment_label: string
  sentiment_confidence: number
}

export interface SentimentData {
  pair: string
  timestamp: string
  overall_score: number
  overall_label: string
  news_sentiment: number
  social_sentiment: number
  technical_sentiment: number
  news_count: number
  social_mentions: number
  top_bullish_factors: string[]
  top_bearish_factors: string[]
}

export interface Notification {
  id: string
  type: 'prediction' | 'news' | 'success' | 'warning' | 'error' | 'info'
  title: string
  message: string
  timestamp: string
  read: boolean
}

interface StoreState {
  // Prices
  prices: Record<string, PriceData>
  updatePrice: (pair: string, data: PriceData) => void
  getPrice: (pair: string) => PriceData | undefined

  // Predictions
  predictions: PredictionData[]
  addPrediction: (prediction: PredictionData) => void
  removePrediction: (id: string) => void
  clearPredictions: () => void

  // News
  news: NewsData[]
  addNews: (news: NewsData) => void
  clearNews: () => void

  // Sentiment
  sentiments: Record<string, SentimentData>
  updateSentiment: (pair: string, data: SentimentData) => void
  getSentiment: (pair: string) => SentimentData | undefined

  // Notifications
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  markNotificationRead: (id: string) => void
  clearNotifications: () => void
}

export const useStore = create<StoreState>()(
  persist(
    (set, get) => ({
      // Prices
      prices: {},
      updatePrice: (pair, data) =>
        set(state => ({
          prices: { ...state.prices, [pair]: data }
        })),
      getPrice: (pair) => get().prices[pair],

      // Predictions
      predictions: [],
      addPrediction: (prediction) =>
        set(state => ({
          predictions: [prediction, ...state.predictions.filter(p => p.id !== prediction.id)].slice(0, 100)
        })),
      removePrediction: (id) =>
        set(state => ({
          predictions: state.predictions.filter(p => p.id !== id)
        })),
      clearPredictions: () => set({ predictions: [] }),

      // News
      news: [],
      addNews: (news) =>
        set(state => ({
          news: [news, ...state.news.filter(n => n.id !== news.id)].slice(0, 200)
        })),
      clearNews: () => set({ news: [] }),

      // Sentiment
      sentiments: {},
      updateSentiment: (pair, data) =>
        set(state => ({
          sentiments: { ...state.sentiments, [pair]: data }
        })),
      getSentiment: (pair) => get().sentiments[pair],

      // Notifications
      notifications: [],
      addNotification: (notification) =>
        set(state => ({
          notifications: [
            { ...notification, id: crypto.randomUUID(), timestamp: new Date().toISOString(), read: false },
            ...state.notifications
          ].slice(0, 50)
        })),
      markNotificationRead: (id) =>
        set(state => ({
          notifications: state.notifications.map(n =>
            n.id === id ? { ...n, read: true } : n
          )
        })),
      clearNotifications: () => set({ notifications: [] }),
    }),
    {
      name: 'forexnews-store',
      partialize: (state) => ({
        prices: state.prices,
        predictions: state.predictions.slice(0, 50),
        news: state.news.slice(0, 100),
        sentiments: state.sentiments,
      }),
    }
  )
)