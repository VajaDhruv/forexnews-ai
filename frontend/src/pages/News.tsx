import { useEffect, useState } from 'react'
import {
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  Clock,
  Zap,
  AlertTriangle,
  Circle,
  ExternalLink,
  Loader2
} from 'lucide-react'
import { format, parseISO, differenceInMinutes } from 'date-fns'
import { newsApi } from '../services/api'
import { NewsArticleResponse } from '../types'

interface NewsFilters {
  search: string
  sources: string[]
  pairs: string[]
  impact: string[]
  sentiment: string[]
  page: number
  pageSize: number
}

export function News() {
  const [news, setNews] = useState<NewsArticleResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState<NewsFilters>({
    search: '',
    sources: [],
    pairs: [],
    impact: [],
    sentiment: [],
    page: 1,
    pageSize: 20,
  })
  const [showFilters, setShowFilters] = useState(false)

  const sources = ['forex_factory', 'investing_com', 'dailyfx', 'bloomberg', 'reuters', 'cnbc', 'marketwatch', 'yahoo_finance']
  const pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY']
  const impacts = ['critical', 'high', 'medium', 'low']
  const sentiments = ['very_bullish', 'bullish', 'neutral', 'bearish', 'very_bearish']

  useEffect(() => {
    fetchNews()
  }, [filters.page, filters.search, filters.sources, filters.pairs, filters.impact, filters.sentiment])

  const fetchNews = async () => {
    setLoading(true)
    try {
      const params: any = {
        page: filters.page,
        page_size: filters.pageSize,
      }
      if (filters.search) params.search = filters.search
      if (filters.sources.length) params.source = filters.sources
      if (filters.pairs.length) params.pairs = filters.pairs
      if (filters.impact.length) params.impact_level = filters.impact
      if (filters.sentiment.length) params.sentiment_label = filters.sentiment

      const response = await newsApi.getAll(params)
      setNews(response.data.items)
      setTotal(response.data.total)
    } catch (error) {
      console.error('Failed to fetch news:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key: keyof NewsFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }))
  }

  const toggleFilter = (array: string[], value: string) => {
    return array.includes(value) ? array.filter(v => v !== value) : [...array, value]
  }

  const getImpactIcon = (impact: string) => {
    switch (impact) {
      case 'critical': return <AlertTriangle className="w-4 h-4 text-bearish-600" />
      case 'high': return <Zap className="w-4 h-4 text-amber-600" />
      case 'medium': return <Circle className="w-4 h-4 text-blue-600" />
      default: return <Clock className="w-4 h-4 text-dark-400" />
    }
  }

  const getSentimentBadge = (label: string) => {
    switch (label) {
      case 'very_bullish':
      case 'bullish':
        return <span className="badge-bullish">{label.replace('_', ' ')}</span>
      case 'very_bearish':
      case 'bearish':
        return <span className="badge-bearish">{label.replace('_', ' ')}</span>
      default:
        return <span className="badge-neutral">{label}</span>
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-dark-100">Market News</h1>
          <p className="text-dark-500 dark:text-dark-400">Real-time forex news with sentiment analysis</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="btn-secondary"
        >
          <Filter className="w-4 h-4 mr-2" />
          Filters
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="card animate-slide-up">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-700 dark:text-dark-300 mb-2">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
                <input
                  type="text"
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  placeholder="Search news..."
                  className="input pl-10"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <FilterGroup
                title="Sources"
                options={sources}
                selected={filters.sources}
                onToggle={(v) => handleFilterChange('sources', toggleFilter(filters.sources, v))}
              />
              <FilterGroup
                title="Pairs"
                options={pairs}
                selected={filters.pairs}
                onToggle={(v) => handleFilterChange('pairs', toggleFilter(filters.pairs, v))}
              />
              <FilterGroup
                title="Impact"
                options={impacts}
                selected={filters.impact}
                onToggle={(v) => handleFilterChange('impact', toggleFilter(filters.impact, v))}
              />
              <FilterGroup
                title="Sentiment"
                options={sentiments}
                selected={filters.sentiment}
                onToggle={(v) => handleFilterChange('sentiment', toggleFilter(filters.sentiment, v))}
              />
            </div>
          </div>
        </div>
      )}

      {/* News List */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-8 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          </div>
        ) : news.length === 0 ? (
          <div className="p-8 text-center text-dark-500 dark:text-dark-400">
            No news articles found
          </div>
        ) : (
          <>
            <div className="divide-y divide-dark-200 dark:divide-dark-700">
              {news.map((article) => (
                <article
                  key={article.id}
                  className="p-4 hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start gap-3 mb-2">
                        <h3 className="font-medium text-dark-900 dark:text-dark-100 line-clamp-2 flex-1">
                          <a href={article.url} target="_blank" rel="noopener noreferrer" className="hover:text-primary-600 dark:hover:text-primary-400">
                            {article.title}
                          </a>
                        </h3>
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-dark-400 hover:text-dark-600 dark:hover:text-dark-300"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>

                      {article.summary && (
                        <p className="text-sm text-dark-600 dark:text-dark-400 line-clamp-3 mb-3">
                          {article.summary}
                        </p>
                      )}

                      <div className="flex flex-wrap items-center gap-3 text-xs">
                        <span className="flex items-center gap-1 text-dark-500 dark:text-dark-400">
                          <span className="font-mono">{article.source.replace('_', ' ').toUpperCase()}</span>
                        </span>
                        <span className="text-dark-400">•</span>
                        <span className="text-dark-500 dark:text-dark-400">
                          {format(parseISO(article.published_at), 'MMM d, yyyy HH:mm')}
                        </span>
                        <span className="text-dark-400">•</span>
                        <span className="text-dark-500 dark:text-dark-400">
                          {differenceInMinutes(new Date(), parseISO(article.published_at))} min ago
                        </span>
                        {article.impact_level && (
                          <>
                            <span className="text-dark-400">•</span>
                            <span className="flex items-center gap-1">
                              {getImpactIcon(article.impact_level)}
                              <span className="capitalize">{article.impact_level}</span>
                            </span>
                          </>
                        )}
                        {article.related_pairs.length > 0 && (
                          <>
                            <span className="text-dark-400">•</span>
                            <span className="flex items-center gap-1 text-primary-600 dark:text-primary-400">
                              {article.related_pairs.slice(0, 3).join(', ')}
                              {article.related_pairs.length > 3 && ` +${article.related_pairs.length - 3}`}
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {article.sentiment_label && (
                        <div className="hidden sm:block">
                          {getSentimentBadge(article.sentiment_label)}
                        </div>
                      )}
                      {article.sentiment_score !== null && article.sentiment_score !== undefined && (
                        <div className={`text-xs font-mono font-medium ${
                          article.sentiment_score > 0.1 ? 'text-bullish-600' :
                          article.sentiment_score < -0.1 ? 'text-bearish-600' :
                          'text-dark-500'
                        }`}>
                          {article.sentiment_score > 0 ? '+' : ''}{article.sentiment_score.toFixed(2)}
                        </div>
                      )}
                    </div>
                  </div>

                  {article.categories.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {article.categories.map(cat => (
                        <span key={cat} className="px-2 py-0.5 text-xs rounded bg-dark-100 dark:bg-dark-800 text-dark-600 dark:text-dark-400">
                          {cat.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </div>

            {/* Pagination */}
            {total > filters.pageSize && (
              <div className="p-4 border-t border-dark-200 dark:border-dark-700 flex items-center justify-between">
                <p className="text-sm text-dark-500 dark:text-dark-400">
                  Showing {(filters.page - 1) * filters.pageSize + 1} to {Math.min(filters.page * filters.pageSize, total)} of {total} articles
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
            {opt.replace('_', ' ').toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  )
}