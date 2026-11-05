# ForexNews AI

> **Real-time Forex Market Reaction Prediction & Analysis System**

A powerful, live forex trading intelligence platform that ingests real-time news, analyzes sentiment using FinBERT, and predicts market reactions using deep learning models.

## 🚀 Features

- **Real-time News Ingestion** - Multiple sources (Forex Factory, Investing.com, DailyFX, Bloomberg, Reuters, CNBC, MarketWatch, Yahoo Finance)
- **Advanced Sentiment Analysis** - FinBERT + keyword + currency-specific analysis
- **ML-Powered Predictions** - Deep learning model predicting market direction (up/down/sideways) with confidence scores
- **Multi-horizon Forecasting** - 15min, 30min, 1h, 4h, 24h prediction horizons
- **Live WebSocket Updates** - Real-time price, news, predictions, and sentiment streaming
- **Technical Indicators** - RSI, MACD, Bollinger Bands, ATR, Moving Averages
- **Performance Analytics** - Accuracy tracking, profit/loss analysis, model performance metrics
- **Modern React Dashboard** - Dark/light theme, responsive design, real-time charts

## 🏗 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  News Sources   │────▶│  News Ingestion │────▶│  Sentiment      │
│  (RSS/XML/API)  │     │  Service        │     │  Analyzer       │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐     ┌────────▼────────┐
│  Forex Data     │────▶│  Forex Data     │────▶│  Prediction     │
│  (OANDA/CCXT/   │     │  Service        │     │  Engine         │
│   yfinance)     │     └─────────────────┘     └────────┬────────┘
└─────────────────┘                                      │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PostgreSQL     │◀───▶│  FastAPI        │◀───▶│  React Frontend │
│  Database       │     │  Backend        │     │  (TypeScript)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                ┌────────▼────────┐
                                                │  WebSocket      │
                                                │  Real-time UI   │
                                                └─────────────────┘
```

## 🛠 Tech Stack

### Backend
- **FastAPI** - High-performance async API
- **PostgreSQL** - Primary database with asyncpg
- **Redis** - Caching & Celery broker
- **Celery** - Background task processing
- **PyTorch** - Deep learning models
- **Transformers** - FinBERT for sentiment
- **Sentence Transformers** - Embeddings
- **CCXT/yfinance** - Market data
- **SQLAlchemy 2.0** - Async ORM

### Frontend
- **React 18** + **TypeScript**
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling
- **Recharts** - Data visualization
- **Zustand** - State management
- **Socket.io** - Real-time updates
- **React Router** - Navigation

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Local development
- **Nginx** - Reverse proxy
- **Prometheus** - Metrics (optional)

## 📦 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone & Configure
```bash
git clone <repository-url>
cd ForexNewsAI

# Copy environment file and add your API keys
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start with Docker Compose
```bash
# Development (with hot reload)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

### 3. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Flower (Celery)**: http://localhost:5555

## 🔑 API Keys Required

For full functionality, obtain free API keys from:

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| [Alpha Vantage](https://www.alphavantage.co/) | Forex data | 500 requests/day |
| [NewsAPI](https://newsapi.org/) | News articles | 100 requests/day |
| [Finnhub](https://finnhub.io/) | Market data | 60 calls/min |
| [Twelve Data](https://twelvedata.com/) | Forex data | 800 requests/day |
| [OANDA](https://developer.oanda.com/) | Live streaming | Practice account |

Add keys to `.env` file.

## 📁 Project Structure

```
ForexNewsAI/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API routes
│   │   ├── db/              # Database models & session
│   │   ├── ml/models/       # ML models (sentiment, predictor)
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic services
│   │   ├── config.py        # Configuration
│   │   └── main.py          # FastAPI app entry
│   ├── scripts/             # Database init scripts
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   ├── services/        # API services
│   │   ├── store/           # Zustand store
│   │   ├── types/           # TypeScript types
│   │   └── App.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔌 API Endpoints

### News
- `GET /api/v1/news` - List news with filters
- `GET /api/v1/news/latest` - Latest news
- `GET /api/v1/news/{id}` - Get news article
- `GET /api/v1/news/stats/summary` - News statistics
- `POST /api/v1/news/analyze-sentiment` - Analyze custom text

### Forex
- `GET /api/v1/forex/prices/current` - Current prices
- `GET /api/v1/forex/prices/{pair}/current` - Pair price
- `GET /api/v1/forex/prices/{pair}/history` - Price history
- `GET /api/v1/forex/pairs` - Available pairs
- `GET /api/v1/forex/stats/{pair}` - Pair statistics
- `GET /api/v1/forex/stats/system` - System stats

### Predictions
- `GET /api/v1/predictions` - List predictions
- `GET /api/v1/predictions/active` - Active predictions
- `GET /api/v1/predictions/latest` - Latest predictions
- `GET /api/v1/predictions/{id}` - Get prediction
- `GET /api/v1/predictions/stats/performance` - Performance stats
- `GET /api/v1/predictions/stats/model-performance` - Model metrics

### Sentiment
- `GET /api/v1/sentiment/market/{pair}` - Market sentiment
- `GET /api/v1/sentiment/market` - All sentiments
- `GET /api/v1/sentiment/news/{pair}` - News sentiment
- `POST /api/v1/sentiment/analyze` - Analyze text
- `GET /api/v1/sentiment/history/{pair}` - Sentiment history

### WebSocket
- `WS /api/v1/ws` - Real-time updates
  - Subscribe: `{"type": "subscribe", "topics": ["predictions", "news", "prices", "sentiment"]}`
  - Get latest: `{"type": "get_latest", "topic": "predictions"}`

## 🧠 ML Models

### Sentiment Analyzer
- **FinBERT** (ProsusAI/finbert) - Financial domain BERT
- **Keyword Enhancement** - Forex-specific bullish/bearish keywords
- **Currency Context** - Pair-specific sentiment adjustment
- **Embeddings** - Sentence transformers for similarity

### Market Predictor
- **Architecture** - Feedforward NN with 3 heads (direction, magnitude, confidence)
- **Features** - 100+ technical, sentiment, time, and news features
- **Horizons** - 15m, 30m, 1h, 4h, 24h
- **Output** - Direction (up/down/sideways), confidence, expected move

## 📊 Dashboard Features

- **Real-time Price Grid** - All major pairs with 24h change
- **Live Charts** - Interactive price charts with indicators
- **News Feed** - Filterable, searchable news with sentiment
- **Predictions Table** - Active & historical with outcomes
- **Analytics** - Accuracy, P&L, model performance charts
- **Settings** - Full customization

## 🚀 Deployment

### Production with Docker
```bash
# Build images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Environment Variables (Production)
```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
ALPHA_VANTAGE_API_KEY=your_key
NEWSAPI_KEY=your_key
OANDA_API_KEY=your_key
OANDA_ACCOUNT_ID=your_id
OANDA_ENVIRONMENT=live

# Security
SECRET_KEY=your_secret_key
CORS_ORIGINS=https://yourdomain.com
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
```

## 📈 Monitoring

- **Health Check**: `GET /health`
- **Metrics**: Prometheus `/metrics` (if enabled)
- **Flower**: Celery monitoring at `:5555`
- **Logs**: Structured JSON logging

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

MIT License - see LICENSE file for details.

## ⚠️ Disclaimer

**This software is for educational and research purposes only.** 
- Not financial advice
- Past performance ≠ future results
- Always do your own research
- Trade at your own risk

## 🙏 Acknowledgments

- [FinBERT](https://github.com/ProsusAI/FinBERT) - Financial sentiment
- [Transformers](https://github.com/huggingface/transformers) - ML models
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [React](https://react.dev/) - Frontend library
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [Recharts](https://recharts.org/) - Charts

---

**Built with ❤️ for the forex trading community**