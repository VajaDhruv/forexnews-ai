import { useEffect, useState } from 'react'
import {
  BarChart3,
  PieChart,
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Loader2,
  RefreshCw
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RePieChart, Pie, Cell,
  LineChart, Line, AreaChart, Area
} from 'recharts'
import { predictionsApi, forexApi } from '../services/api'
import { format, parseISO, startOfDay, subDays } from 'date-fns'

export function Analytics() {
  const [performance, setPerformance] = useState<any>(null)
  const [modelPerformance, setModelPerformance] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState(24)
  const [selectedPair, setSelectedPair] = useState('ALL')

  const pairs = ['ALL', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']

  useEffect(() => {
    loadAnalytics()
  }, [timeRange, selectedPair])

  const loadAnalytics = async () => {
    setLoading(true)
    try {
      const [perfRes, modelRes] = await Promise.all([
        predictionsApi.getPerformance({ hours: timeRange, pair: selectedPair === 'ALL' ? undefined : selectedPair }),
        predictionsApi.getModelPerformance(),
      ])
      setPerformance(perfRes.data)
      setModelPerformance(modelRes.data)
    } catch (error) {
      console.error('Failed to load analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  const accuracy = performance?.accuracy || 0
  const totalTrades = performance?.total_predictions || 0
  const winningTrades = performance?.correct || 0
  const losingTrades = performance?.incorrect || 0
  const avgPips = performance?.avg_pips_per_trade || 0
  const totalPips = performance?.total_pips || 0

  const directionData = Object.entries(performance?.by_direction || {}).map(([dir, data]: [string, any]) => ({
    direction: dir,
    count: data.count,
    correct: data.correct,
    accuracy: data.accuracy * 100,
    avgPips: data.avg_pips,
  }))

  const horizonData = Object.entries(performance?.by_horizon || {}).map(([horizon, data]: [string, any]) => ({
    horizon: `${horizon}m`,
    count: data.count,
    correct: data.correct,
    accuracy: data.accuracy * 100,
    avgPips: data.avg_pips,
  }))

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-dark-100">Analytics</h1>
          <p className="text-dark-500 dark:text-dark-400">Prediction performance and model metrics</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(parseInt(e.target.value))}
            className="input w-auto"
          >
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last 7 Days</option>
            <option value={720}>Last 30 Days</option>
          </select>
          <select
            value={selectedPair}
            onChange={(e) => setSelectedPair(e.target.value)}
            className="input w-auto"
          >
            {pairs.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <button onClick={loadAnalytics} className="btn-secondary">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <MetricCard
          title="Accuracy"
          value={`${(accuracy * 100).toFixed(1)}%`}
          icon={Target}
          color={accuracy > 0.55 ? 'bullish' : accuracy > 0.5 ? 'amber' : 'bearish'}
          trend={accuracy > 0.5 ? 'positive' : 'negative'}
        />
        <MetricCard
          title="Total Trades"
          value={totalTrades}
          icon={BarChart3}
          color="primary"
        />
        <MetricCard
          title="Wins / Losses"
          value={`${winningTrades} / ${losingTrades}`}
          icon={TrendingUp}
          color="bullish"
        />
        <MetricCard
          title="Avg Pips/Trade"
          value={avgPips.toFixed(1)}
          icon={DollarSign}
          color={avgPips > 0 ? 'bullish' : 'bearish'}
        />
        <MetricCard
          title="Total Pips"
          value={totalPips.toFixed(1)}
          icon={TrendingUp}
          color={totalPips > 0 ? 'bullish' : 'bearish'}
        />
        <MetricCard
          title="Win Rate"
          value={totalTrades > 0 ? `${((winningTrades / totalTrades) * 100).toFixed(1)}%` : 'N/A'}
          icon={PieChart}
          color="primary"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Accuracy by Direction */}
        <div className="card">
          <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100 mb-4">Accuracy by Direction</h3>
          <div className="h-64">
            {directionData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={directionData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="stroke-dark-200 dark:stroke-dark-700" />
                  <XAxis
                    type="number"
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    stroke="#94a3b8"
                    tickFormatter={(v) => `${v.toFixed(0)}%`}
                  />
                  <YAxis
                    type="category"
                    dataKey="direction"
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    stroke="#94a3b8"
                    width={80}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9'
                    }}
                    formatter={(value: number, name: string) => {
                      if (name === 'accuracy') return [`${value.toFixed(1)}%`, 'Accuracy'];
                      if (name === 'avgPips') return [`${value.toFixed(1)}`, 'Avg Pips'];
                      return [value, name];
                    }}
                  />
                  <Bar dataKey="accuracy" fill="#0ea5e9" radius={[0, 4, 4, 0]} name="Accuracy" />
                  <Bar dataKey="avgPips" fill="#22c55e" radius={[0, 4, 4, 0]} name="Avg Pips" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-dark-500">No data</div>
            )}
          </div>
        </div>

        {/* Accuracy by Horizon */}
        <div className="card">
          <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100 mb-4">Accuracy by Horizon</h3>
          <div className="h-64">
            {horizonData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={horizonData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-dark-200 dark:stroke-dark-700" />
                  <XAxis
                    dataKey="horizon"
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    stroke="#94a3b8"
                  />
                  <YAxis
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    stroke="#94a3b8"
                    tickFormatter={(v) => `${v.toFixed(0)}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9'
                    }}
                  />
                  <Bar dataKey="accuracy" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="Accuracy %" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-dark-500">No data</div>
            )}
          </div>
        </div>

        {/* Outcome Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100 mb-4">Outcome Distribution</h3>
          <div className="h-64">
            {totalTrades > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RePieChart>
                  <Pie
                    data={[
                      { name: 'Correct', value: winningTrades, color: '#22c55e' },
                      { name: 'Incorrect', value: losingTrades, color: '#ef4444' },
                      { name: 'Partial', value: performance?.partial || 0, color: '#f59e0b' },
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    fill="#8884d8"
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {[
                      { name: 'Correct', value: winningTrades, color: '#22c55e' },
                      { name: 'Incorrect', value: losingTrades, color: '#ef4444' },
                      { name: 'Partial', value: performance?.partial || 0, color: '#f59e0b' },
                    ].map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9'
                    }}
                  />
                </RePieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-dark-500">No data</div>
            )}
          </div>
        </div>

        {/* Pips Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100 mb-4">Pips by Horizon</h3>
          <div className="h-64">
            {horizonData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={horizonData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-dark-200 dark:stroke-dark-700" />
                  <XAxis
                    dataKey="horizon"
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    stroke="#94a3b8"
                  />
                  <YAxis
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    stroke="#94a3b8"
                    tickFormatter={(v) => `${v.toFixed(1)}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f1f5f9'
                    }}
                  />
                  <Bar dataKey="avgPips" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Avg Pips" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-dark-500">No data</div>
            )}
          </div>
        </div>
      </div>

      {/* Model Performance Table */}
      {modelPerformance.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100 mb-4">Model Performance</h3>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Version</th>
                  <th>Pair</th>
                  <th>Horizon</th>
                  <th>Total</th>
                  <th>Accuracy</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1</th>
                  <th>Profit Factor</th>
                  <th>Sharpe</th>
                  <th>Max DD</th>
                </tr>
              </thead>
              <tbody>
                {modelPerformance.map((model) => (
                  <tr key={`${model.model_name}-${model.model_version}-${model.pair || 'all'}-${model.horizon_minutes || 'all'}`}>
                    <td className="font-medium">{model.model_name}</td>
                    <td className="font-mono text-sm">{model.model_version}</td>
                    <td>{model.pair || 'All'}</td>
                    <td>{model.horizon_minutes ? `${model.horizon_minutes}m` : 'All'}</td>
                    <td>{model.total_predictions}</td>
                    <td className={model.accuracy && model.accuracy > 0.5 ? 'text-bullish-600' : 'text-bearish-600'}>
                      {model.accuracy ? `${(model.accuracy * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td>{model.precision ? `${(model.precision * 100).toFixed(1)}%` : 'N/A'}</td>
                    <td>{model.recall ? `${(model.recall * 100).toFixed(1)}%` : 'N/A'}</td>
                    <td>{model.f1_score ? `${(model.f1_score * 100).toFixed(1)}%` : 'N/A'}</td>
                    <td className={model.profit_factor && model.profit_factor > 1 ? 'text-bullish-600' : 'text-bearish-600'}>
                      {model.profit_factor ? model.profit_factor.toFixed(2) : 'N/A'}
                    </td>
                    <td>{model.sharpe_ratio ? model.sharpe_ratio.toFixed(2) : 'N/A'}</td>
                    <td className={model.max_drawdown && model.max_drawdown < 0.1 ? 'text-bullish-600' : 'text-bearish-600'}>
                      {model.max_drawdown ? `${(model.max_drawdown * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({
  title,
  value,
  icon: Icon,
  color,
  trend
}: {
  title: string;
  value: any;
  icon: any;
  color: string;
  trend?: 'positive' | 'negative';
}) {
  const colors = {
    primary: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300',
    bullish: 'bg-bullish-100 text-bullish-700 dark:bg-bullish-900/30 dark:text-bullish-300',
    bearish: 'bg-bearish-100 text-bearish-700 dark:bg-bearish-900/30 dark:text-bearish-300',
    amber: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
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
      {trend && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          <TrendingUp className={`w-3 h-3 ${trend === 'positive' ? 'text-bullish-600' : 'text-bearish-600'}`} />
          <span className={trend === 'positive' ? 'text-bullish-600' : 'text-bearish-600'}>
            {trend === 'positive' ? 'Above threshold' : 'Below threshold'}
          </span>
        </div>
      )}
    </div>
  )
}