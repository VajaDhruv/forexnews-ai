import { useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Newspaper,
  Target,
  Activity,
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area } from 'recharts'
import { useStore } from '../store'
import { useWebSocket } from '../hooks/useWebSocket'
import { forexApi, predictionsApi } from '../services/api'
import { format, parseISO } from 'date-fns'

interface PairCardProps {
  pair: string
  price: any
  sentiment: any
  predictions: any[]
}

function PairCard({ pair, price, sentiment, predictions }: PairCardProps) {
  if (!price) return null

  const change = price.change_24h_percent
  const isPositive = change >= 0
  const activePredictions = predictions.filter(p => p.pair === pair && !p.resolved_at).slice(0, 3)
  const latestPrediction = activePredictions[0]

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-mono text-lg font-bold text-dark-900 dark:text-dark-100">{pair}</h3>
          <p className="text-sm text-dark-500 dark:text-dark-400">
            {format(parseISO(price.timestamp), 'HH:mm:ss')}
          </p>
        </div>
        <div className="text-right">
          <p className="font-mono text-xl font-bold text-dark-900 dark:text-dark-100">
            {(price.bid + price.ask) / 2}
          </p>
          <p className={`font-mono text-sm ${isPositive ? 'text-bullish-600' : 'text-bearish-600'}`}>
            {isPositive ? '+' : ''}{change.toFixed(2)}%
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-4 text-xs">
        <span className={`flex items-center gap-1 ${
          sentiment?.overall_label === 'bullish' || sentiment?.overall_label === 'very_bullish' ? 'text-bullish-600' :
          sentiment?.overall_label === 'bearish' || sentiment?.overall_label === 'very_bearish' ? 'text-bearish-600' :
          'text-dark-500'
        }`}>
          {sentiment?.overall_label === 'bullish' || sentiment?.overall_label === 'very_bullish' ? <TrendingUp className="w-3 h-3" /> :
           sentiment?.overall_label === 'bearish' || sentiment?.overall_label === 'very_bearish' ? <TrendingDown className="w-3 h-3" /> :
           <Minus className="w-3 h-3" />}
          {sentiment?.overall_label || 'Neutral'}
        </span>
        <span className="flex items-center gap-1 text-dark-500 dark:text-dark-400">
          <Newspaper className="w-3 h-3" />
          {sentiment?.news_count || 0} news
        </span>
      </div>

      {latestPrediction && (
        <div className="mt-4 p-3 rounded-lg bg-dark-50 dark:bg-dark-800/50">
          <div className="flex items-center justify-between">
            <span className={`text-xs font-medium ${
              latestPrediction.direction === 'up' ? 'text-bullish-600' :
              latestPrediction.direction === 'down' ? 'text-bearish-600' :
              'text-dark-500'
            }`}>
              {latestPrediction.direction.toUpperCase()} {latestPrediction.horizon_minutes}min
            </span>
            <span className="text-xs text-dark-500 dark:text-dark-400">
              {(latestPrediction.confidence * 100).toFixed(0)}% conf
            </span>
          </div>
          <div className="mt-1 flex gap-4 text-xs text-dark-500 dark:text-dark-400">
            <span>Target: {latestPrediction.target_price?.toFixed(5) || 'N/A'}</span>
            <span>SL: {latestPrediction.stop_loss?.toFixed(5) || 'N/A'}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export function Dashboard() {
  const { isConnected } = useWebSocket()
  const prices = useStore(state => state.prices)
  const predictions = useStore(state => state.predictions)
  const sentiments = useStore(state => state.sentiments)
  const [systemStats, setSystemStats] = useState<any>(null)
  const [priceHistory, setPriceHistory] = useState<any[]>([])
  const [selectedPair, setSelectedPair] = useState('EURUSD')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [statsRes, historyRes] = await Promise.all([
        forexApi.getSystemStats(),
        forexApi.getHistory(selectedPair, 24),
      ])
      setSystemStats(statsRes.data)
      setPriceHistory(historyRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
      setLoading(false)
    }
  }

  const pairs = Object.keys(prices).length > 0 ? Object.keys(prices) : ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP']

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-dark-100">Dashboard</h1>
          <p className="text-dark-500 dark:text-dark-400">Real-time forex market overview</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedPair}
            onChange={(e) => setSelectedPair(e.target.value)}
            className="input w-auto px-3 py-1 text-sm"
          >
            {pairs.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <button onClick={loadData} className="btn-secondary" disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Pairs"
          value={systemStats?.active_pairs || Object.keys(prices).length}
          icon={Activity}
          color="primary"
        />
        <StatCard
          title="Predictions (24h)"
          value={systemStats?.total_predictions_24h || predictions.length}
          icon={Target}
          color="bullish"
        />
        <StatCard
          title="News Articles (24h)"
          value={systemStats?.total_news_24h || 0}
          icon={Newspaper}
          color="bearish"
        />
        <StatCard
          title="Accuracy (24h)"
          value={systemStats?.overall_accuracy ? `${(systemStats.overall_accuracy * 100).toFixed(1)}%` : 'N/A'}
          icon={TrendingUp}
          color="primary"
        />
      </div>

      {/* Price Chart */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-dark-900 dark:text-dark-100">
            {selectedPair} - 24h Price Chart
          </h2>
          <span className={`flex items-center gap-1 text-sm ${
            isConnected ? 'text-bullish-600' : 'text-bearish-600'
          }`}>
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-bullish-500' : 'bg-bearish-500'}`} />
            {isConnected ? 'Live' : 'Offline'}
          </span>
        </div>
        <div className="h-80">
          {loading ? (
            <div className="flex items-center justify-center h-full text-dark-500">Loading...</div>
          ) : priceHistory.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={priceHistory}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-dark-200 dark:stroke-dark-700" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(value) => format(parseISO(value), 'HH:mm')}
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  stroke="#94a3b8"
                />
                <YAxis
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  stroke="#94a3b8"
                  tickFormatter={(value) => value.toFixed(5)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#f1f5f9'
                  }}
                  formatter={(value: number) => [value.toFixed(5), 'Price']}
                />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke="#0ea5e9"
                  strokeWidth={2}
                  fillOpacity={0.1}
                  fill="#0ea5e9"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-dark-500">No data available</div>
          )}
        </div>
      </div>

      {/* Pair Grid */}
      <div>
        <h2 className="text-lg font-semibold text-dark-900 dark:text-dark-100 mb-4">Market Overview</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
          {pairs.map(pair => (
            <PairCard
              key={pair}
              pair={pair}
              price={prices[pair]}
              sentiment={sentiments[pair]}
              predictions={predictions}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon: Icon, color }: { title: string; value: any; icon: any; color: string }) {
  const colors = {
    primary: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300',
    bullish: 'bg-bullish-100 text-bullish-700 dark:bg-bullish-900/30 dark:text-bullish-300',
    bearish: 'bg-bearish-100 text-bearish-700 dark:bg-bearish-900/30 dark:text-bearish-300',
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-dark-500 dark:text-dark-400">{title}</p>
          <p className="text-2xl font-bold text-dark-900 dark:text-dark-100 mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colors[color as keyof typeof colors] || colors.primary}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  )
}