from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import field_validator
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "ForexNews AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/forexnews"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # External APIs
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    NEWSAPI_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    TWELVE_DATA_API_KEY: Optional[str] = None
    OANDA_API_KEY: Optional[str] = None
    OANDA_ACCOUNT_ID: Optional[str] = None
    OANDA_ENVIRONMENT: str = "practice"

    # News Sources (comma-separated string from env, parsed to list via property)
    NEWS_SOURCES_STR: str = (
        "https://www.forexfactory.com/ffcal_week_this.xml,"
        "https://www.investing.com/rss/news_285.rss,"
        "https://www.dailyfx.com/feeds/market_news,"
        "https://feeds.bloomberg.com/markets/news.rss,"
        "https://www.reuters.com/business/finance/rss,"
        "https://www.cnbc.com/id/10000113/device/rss/rss.html,"
        "https://www.marketwatch.com/rss/topstories,"
        "https://finance.yahoo.com/rss/topstories"
    )

    @property
    def NEWS_SOURCES(self) -> List[str]:
        return [s.strip() for s in self.NEWS_SOURCES_STR.split(",") if s.strip()]

    # Forex Pairs to Track (comma-separated string from env, parsed to list via property)
    FOREX_PAIRS_STR: str = (
        "EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD,"
        "EURGBP,EURJPY,GBPJPY,AUDJPY,CADJPY,CHFJPY,"
        "EURAUD,EURCAD,EURCHF,GBPAUD,GBPCAD,GBPCHF,"
        "AUDCAD,AUDCHF,AUDNZD,CADCHF,NZDCAD,NZDCHF"
    )

    @property
    def FOREX_PAIRS(self) -> List[str]:
        return [s.strip() for s in self.FOREX_PAIRS_STR.split(",") if s.strip()]

    # ML Model Settings
    MODEL_PATH: str = "/app/ml/models"
    SENTIMENT_MODEL: str = "ProsusAI/finbert"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    PREDICTION_HORIZON_MINUTES: List[int] = [15, 30, 60, 240, 1440]
    CONFIDENCE_THRESHOLD: float = 0.65
    RETRAIN_INTERVAL_HOURS: int = 24

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()