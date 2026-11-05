import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if needed
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// News API
export const newsApi = {
  getAll: (params?: any) => api.get('/news', { params }),
  getLatest: (params?: any) => api.get('/news/latest', { params }),
  getById: (id: string) => api.get(`/news/${id}`),
  getStats: (hours?: number) => api.get('/news/stats/summary', { params: { hours } }),
  analyzeSentiment: (text: string, pair?: string) =>
    api.post('/news/analyze-sentiment', { text, pair }),
}

// Forex API
export const forexApi = {
  getCurrentPrices: (pairs?: string[]) =>
    api.get('/forex/prices/current', { params: { pairs } }),
  getCurrentPrice: (pair: string) => api.get(`/forex/prices/${pair}/current`),
  getHistory: (pair: string, hours?: number) =>
    api.get(`/forex/prices/${pair}/history`, { params: { hours } }),
  getPairs: () => api.get('/forex/pairs'),
  getPairStats: (pair: string) => api.get(`/forex/stats/${pair}`),
  getSystemStats: () => api.get('/forex/stats/system'),
}

// Predictions API
export const predictionsApi = {
  getAll: (params?: any) => api.get('/predictions', { params }),
  getActive: (params?: any) => api.get('/predictions/active', { params }),
  getLatest: (limit?: number) => api.get('/predictions/latest', { params: { limit } }),
  getById: (id: string) => api.get(`/predictions/${id}`),
  getPerformance: (params?: any) => api.get('/predictions/stats/performance', { params }),
  getModelPerformance: () => api.get('/predictions/stats/model-performance'),
}

// Sentiment API
export const sentimentApi = {
  getMarketSentiment: (pair: string) => api.get(`/sentiment/market/${pair}`),
  getAllMarketSentiment: () => api.get('/sentiment/market'),
  getNewsSentiment: (pair: string, hours?: number) =>
    api.get(`/sentiment/news/${pair}`, { params: { hours } }),
  analyzeText: (text: string, pair?: string) =>
    api.post('/sentiment/analyze', { text, pair }),
  getHistory: (pair: string, hours?: number) =>
    api.get(`/sentiment/history/${pair}`, { params: { hours } }),
}

export default api