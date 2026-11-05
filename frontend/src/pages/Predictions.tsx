import { useEffect, useState } from 'react'
import {
  Filter,
  ChevronLeft,
  ChevronRight,
  Target,
  CheckCircle,
  XCircle,
  MinusCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  RefreshCw
} from 'lucide-react'
import { format, parseISO, differenceInMinutes } from 'date-fns'
import { predictionsApi } from '../services/api'
import { useStore } from '../store'

interface PredictionFilters {
  pairs: string[]
  horizons: number[]
  directions: string[]
  outcomes: string[]
  minConfidence: number
  page: number
  pageSize: number
}

export function Predictions() {
  const { predictions: localPredictions } = useStore()
  const [predictions, setPredictions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [activeTab, setActiveTab] = useState<'active' | 'history'>('active')
  const [filters, setFilters] = useState<PredictionFilters>({
    pairs: [],
    horizons: [],
    directions: [],
    outcomes: [],
    minConfidence: 0,
    page: 1,
    pageSize: 20,
  })
  const [showFilters, setShowFilters] = useState(false)

  const pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY']
  const horizons = [15, 30, 60, 240, 1440]
  const directions = ['up', 'down', 'sideways']
  const outcomes = ['correct', 'incorrect', 'partial', 'pending']

  useEffect(() => {
    fetchPredictions()
  }, [activeTab, filters])

  const fetchPredictions = async () => {
    setLoading(true)
    try {
      if (activeTab === 'active') {
        const response = await predictionsApi.getActive({ limit: 100 })
        setPredictions(response.data)
        setTotal(response.data.length)
      } else {
        const params: any = {
          page: filters.page,
          page_size: filters.pageSize,
        }
        if (filters.pairs.length) params.pair = filters.pairs
        if (filters.horizons.length) params.horizon_minutes = filters.horizons
        if (filters.directions.length) params.direction = filters.directions
        if (filters.outcomes.length) params.outcome = filters.outcomes
        if (filters.minConfidence > 0) params.min_confidence = filters.minConfidence

        const response = await predictionsApi.getAll(params)
        setPredictions(response.data.items)
        setTotal(response.data.total)
      }
    } catch (error) {
      console.error('Failed to fetch predictions:', error)
      // Fallback to local store
      setPredictions(localPredictions)
      setTotal(localPredictions.length)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key: keyof PredictionFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }))
  }

  const toggleFilter = (array: string[] | number[], value: string | number) => {
    return array.includes(value) ? array.filter(v => v !== value) : [...array, value]
  }

  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case 'up': return <TrendingUp className="w-4 h-4 text-bullish-600" />
      case 'down': return <TrendingDown className="w-4 h-4 text-bearish-600" />
      default: return <Minus className="w-4 h-4 text-dark-400" />
    }
  }

  const getOutcomeBadge = (outcome: string | null) => {
    if (!outcome) return <span className="badge-neutral">Pending</span>
    switch (outcome) {
      case 'correct': return <span className="badge-bullish"><CheckCircle className="w-3 h-3 mr-1" /> Correct</span>
      case 'incorrect': return <span className="badge-bearish"><XCircle className="w-3 h-3 mr-1" /> Incorrect</span>
      case 'partial': return <span className="badge-neutral"><MinusCircle className="w-3 h-3 mr-1" /> Partial</span>
      default: return <span className="badge-neutral"><Clock className="w-3 h-3 mr-1" /> Pending</span>
    }
  }

  const getTimeToExpiry = (expiresAt: string) => {
    const diff = differenceInMinutes(parseISO(expiresAt), new Date())
    if (diff <= 0) return 'Expired'
    if (diff < 60) return `${diff} min`
    return `${Math.floor(diff / 60)}h ${diff % 60}m`
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-dark-100">Predictions</h1>
          <p className="text-dark-500 dark:text-dark-400">AI-powered market reaction forecasts</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn-secondary"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </button>
          <button onClick={fetchPredictions} className="btn-secondary" disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-dark-100 dark:bg-dark-800 rounded-lg p-1">
        <button
          onClick={() => setActiveTab('active')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'active'
              ? 'bg-white dark:bg-dark-900 shadow-sm text-dark-900 dark:text-dark-100'
              : 'text-dark-600 dark:text-dark-400 hover:text-dark-900 dark:hover:text-dark-100'
          }`}
        >
          Active ({localPredictions.filter(p => !p.resolved_at).length})
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'history'
              ? 'bg-white dark:bg-dark-900 shadow-sm text-dark-900 dark:text-dark-100'
              : 'text-dark-600 dark:text-dark-400 hover:text-dark-900 dark:hover:text-dark-100'
          }`}
        >
          History
        </button>
      </div>

      {/* Filters */}
      {showFilters && activeTab === 'history' && (
        <div className="card animate-slide-up">
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <FilterGroup
                title="Pairs"
                options={pairs}
                selected={filters.pairs}
                onToggle={(v) => handleFilterChange('pairs', toggleFilter(filters.pairs, v))}
              />
              <FilterGroup
                title="Horizons"
                options={horizons.map(h => `${h}m`)}
                selected={filters.horizons.map(h => `${h}m`)}
                onToggle={(v) => handleFilterChange('horizons', toggleFilter(filters.horizons, parseInt(v.replace('m', ''))))}
              />
              <FilterGroup
                title="Direction"
                options={directions}
                selected={filters.directions}
                onToggle={(v) => handleFilterChange('directions', toggleFilter(filters.directions, v))}
              />
              <FilterGroup
                title="Outcome"
                options={outcomes}
                selected={filters.outcomes}
                onToggle={(v) => handleFilterChange('outcomes', toggleFilter(filters.outcomes, v))}
              />
              <div>
                <label className="block text-sm font-medium text-dark-700 dark:text-dark-300 mb-2">Min Confidence</label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={filters.minConfidence * 100}
                  onChange={(e) => handleFilterChange('minConfidence', parseInt(e.target.value) / 100)}
                  className="w-full h-2 bg-dark-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
                />
                <p className="text-xs text-dark-500 mt-1">{(filters.minConfidence * 100).toFixed(0)}%</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Predictions Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-8 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          </div>
        ) : predictions.length === 0 ? (
          <div className="p-8 text-center text-dark-500 dark:text-dark-400">
            No predictions found
          </div>
        ) : (
          <>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Pair</th>
                    <th>Direction</th>
                    <th>Horizon</th>
                    <th>Confidence</th>
                    <th>Expected Move</th>
                    <th>Entry / Target / SL</th>
                    <th>Status</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((pred) => (
                    <tr key={pred.id}>
                      <td className="font-mono font-medium">{pred.pair}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          {getDirectionIcon(pred.direction)}
                          <span className={`font-medium ${
                            pred.direction === 'up' ? 'text-bullish-600' :
                            pred.direction === 'down' ? 'text-bearish-600' :
                            'text-dark-600'
                          }`}>
                            {pred.direction.toUpperCase()}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="px-2 py-0.5 text-xs rounded bg-dark-100 dark:bg-dark-800 text-dark-600 dark:text-dark-400">
                          {pred.horizon_minutes}m
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                pred.confidence > 0.7 ? 'bg-bullish-500' :
                                pred.confidence > 0.5 ? 'bg-amber-500' :
                                'bg-bearish-500'
                              }`}
                              style={{ width: `${pred.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-mono text-dark-600 dark:text-dark-400">
                            {(pred.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td className="font-mono text-sm">
                        {pred.expected_move_pips?.toFixed(1) || 'N/A'} pips
                        <br />
                        <span className="text-xs text-dark-500">
                          {pred.expected_move_percent?.toFixed(2) || 'N/A'}%
                        </span>
                      </td>
                      <td className="font-mono text-xs text-dark-600 dark:text-dark-400">
                        <div>Entry: {pred.entry_price?.toFixed(5) || 'N/A'}</div>
                        <div className="text-bullish-600">T: {pred.target_price?.toFixed(5) || 'N/A'}</div>
                        <div className="text-bearish-600">SL: {pred.stop_loss?.toFixed(5) || 'N/A'}</div>
                      </td>
                      <td>{getOutcomeBadge(pred.outcome)}</td>
                      <td className="text-sm text-dark-500 dark:text-dark-400">
                        {activeTab === 'active' ? (
                          <span className="font-mono">{getTimeToExpiry(pred.expires_at)}</span>
                        ) : (
                          format(parseISO(pred.predicted_at), 'MMM d, HH:mm')
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination for history */}
            {activeTab === 'history' && total > filters.pageSize && (
              <div className="p-4 border-t border-dark-200 dark:border-dark-700 flex items-center justify-between">
                <p className="text-sm text-dark-500 dark:text-dark-400">
                  Showing {(filters.page - 1) * filters.pageSize + 1} to {Math.min(filters.page * filters.pageSize, total)} of {total}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleFilterChange('page', filters.page - 1)}
                    disabled={filters.page === 1}
                    className="btn-secondary"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleFilterChange('page', filters.page + 1)}
                    disabled={filters.page * filters.pageSize >= total}
                    className="btn-secondary"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function FilterGroup({ title, options, selected, onToggle }: { title: string; options: string[]; selected: string[]; onToggle: (v: string) => void }) {
  return (
    <div>
      <label className="block text-sm font-medium text-dark-700 dark:text-dark-300 mb-2">{title}</label>
      <div className="flex flex-wrap gap-2">
        {options.map(opt => (
          <button
            key={opt}
            onClick={() => onToggle(opt)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              selected.includes(opt)
                ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                : 'bg-dark-100 text-dark-600 hover:bg-dark-200 dark:bg-dark-800 dark:text-dark-400 dark:hover:bg-dark-700'
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  )
}