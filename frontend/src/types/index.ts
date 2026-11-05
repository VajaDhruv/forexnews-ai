export interface NewsArticleResponse {
  id: string
  title: string
  content: string | null
  summary: string | null
  url: string
  source: string
  published_at: string
  fetched_at: string
  related_pairs: string[]
  impact_level: 'low' | 'medium' | 'high' | 'critical'
  categories: string[]
  sentiment_score: number | null
  sentiment_label: string | null
  sentiment_confidence: number | null
  sentiment_details: Record<string, any>
  embedding: number[] | null
}

export interface ForexPriceResponse {
  id: string
  pair: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  bid: number | null
  ask: number | null
  spread: number | null
  sma_20: number | null
  sma_50: number | null
  ema_12: number | null
  ema_26: number | null
  rsi_14: number | null
  macd: number | null
  macd_signal: number | null
  bollinger_upper: number | null
  bollinger_lower: number | null
  atr_14: number | null
}

export interface CurrentPriceResponse {
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

export interface PredictionResponse {
  id: string
  news_id: string
  pair: string
  horizon_minutes: number
  direction: 'up' | 'down' | 'sideways'
  confidence: number
  expected_move_pips: number | null
  expected_move_percent: number | null
  entry_price: number | null
  target_price: number | null
  stop_loss: number | null
  risk_reward_ratio: number | null
  model_version: string
  features_used: Record<string, any>
  feature_importance: Record<string, number>
  predicted_at: string
  expires_at: string
  resolved_at: string | null
  actual_direction: 'up' | 'down' | 'sideways' | null
  actual_move_pips: number | null
  actual_move_percent: number | null
  outcome: string | null
  profit_loss_pips: number | null
}

export interface MarketSentimentResponse {
  pair: string
  timestamp: string
  overall_score: number
  overall_label: string
  news_sentiment: number | null
  social_sentiment: number | null
  technical_sentiment: number | null
  news_count: number
  social_mentions: number
  top_bullish_factors: string[]
  top_bearish_factors: string[]
}

export interface PairStats {
  pair: string
  current_price: number
  change_24h: number
  change_24h_percent: number
  volume_24h: number
  high_24h: number
  low_24h: number
  prediction_count_24h: number
  avg_confidence_24h: number
  accuracy_24h: number | null
  sentiment: string
  sentiment_score: number
}

export interface SystemStats {
  total_news_24h: number
  total_predictions_24h: number
  avg_prediction_confidence: number
  overall_accuracy: number | null
  active_pairs: number
  ws_connections: number
  news_sources_active: number
  last_model_update: string | null
  uptime_seconds: number
}

export interface PerformanceStats {
  period_hours: number
  total_predictions: number
  correct: number
  incorrect: number
  partial: number
  accuracy: number | null
  avg_confidence: number
  avg_pips_per_trade: number
  total_pips: number
  by_direction: Record<string, {
    count: number
    correct: number
    accuracy: number
    avg_pips: number
  }>
  by_horizon: Record<string, {
    count: number
    correct: number
    accuracy: number
    avg_pips: number
  }>
  timestamp: string
}

export interface ModelPerformance {
  model_name: string
  model_version: string
  pair: string | null
  horizon_minutes: number | null
  total_predictions: number
  correct_predictions: number
  accuracy: number | null
  precision: number | null
  recall: number | null
  f1_score: number | null
  total_pips: number
  avg_pips_per_trade: number | null
  win_rate: number | null
  profit_factor: number | null
  max_drawdown: number | null
  sharpe_ratio: number | null
  period_start: string | null
  period_end: string | null
}

export interface SentimentAnalysisResponse {
  text: string
  score: number
  label: string
  confidence: number
  details: Record<string, any>
  pair: string | null
  analyzed_at: string
}

export type NewsSource =
  | 'forex_factory'
  | 'investing_com'
  | 'dailyfx'
  | 'bloomberg'
  | 'reuters'
  | 'cnbc'
  | 'marketwatch'
  | 'yahoo_finance'
  | 'twitter'
  | 'reddit'
  | 'custom'

export type NewsImpact = 'low' | 'medium' | 'high' | 'critical'

export type SentimentLabel =
  | 'very_bearish'
  | 'bearish'
  | 'neutral'
  | 'bullish'
  | 'very_bullish'

export type PredictionDirection = 'up' | 'down' | 'sideways'

export type PredictionOutcome = 'correct' | 'incorrect' | 'partial' | 'pending'

export interface WSMessage {
  type: string
  data?: any
  timestamp?: string
}

export interface WSSubscribeMessage extends WSMessage {
  type: 'subscribe'
  topics: string[]
}

export interface WSUnsubscribeMessage extends WSMessage {
  type: 'unsubscribe'
  topics: string[]
}

export interface WSGetLatestMessage extends WSMessage {
  type: 'get_latest'
  topic: string
}

export interface WSPredictionMessage extends WSMessage {
  type: 'prediction' | 'new_prediction' | 'prediction_resolved'
  data: PredictionResponse
}

export interface WSNewsMessage extends WSMessage {
  type: 'news' | 'new_news'
  data: NewsArticleResponse
}

export interface WSPriceMessage extends WSMessage {
  type: 'price' | 'price_update'
  pair: string
  data: CurrentPriceResponse
}

export interface WSSentimentMessage extends WSMessage {
  type: 'sentiment' | 'sentiment_update'
  pair: string
  data: MarketSentimentResponse
}

export interface WSHeartbeatMessage extends WSMessage {
  type: 'heartbeat'
  timestamp: string
  connections: number
}