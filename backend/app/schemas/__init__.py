from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class NewsSource(str, Enum):
    FOREX_FACTORY = "forex_factory"
    INVESTING_COM = "investing_com"
    DAILYFX = "dailyfx"
    BLOOMBERG = "bloomberg"
    REUTERS = "reuters"
    CNBC = "cnbc"
    MARKETWATCH = "marketwatch"
    YAHOO_FINANCE = "yahoo_finance"
    TWITTER = "twitter"
    REDDIT = "reddit"
    CUSTOM = "custom"


class NewsImpact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SentimentLabel(str, Enum):
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"


class PredictionDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


# News Schemas
class NewsArticleBase(BaseModel):
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    url: HttpUrl
    source: NewsSource
    published_at: datetime
    related_pairs: List[str] = []
    impact_level: NewsImpact = NewsImpact.LOW
    categories: List[str] = []


class NewsArticleCreate(NewsArticleBase):
    pass


class NewsArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    impact_level: Optional[NewsImpact] = None
    categories: Optional[List[str]] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[SentimentLabel] = None
    sentiment_confidence: Optional[float] = None
    sentiment_details: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None


class NewsArticleResponse(NewsArticleBase):
    id: uuid.UUID
    fetched_at: datetime
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[SentimentLabel] = None
    sentiment_confidence: Optional[float] = None
    sentiment_details: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None

    class Config:
        from_attributes = True


class NewsArticleList(BaseModel):
    items: List[NewsArticleResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Forex Price Schemas
class ForexPriceBase(BaseModel):
    pair: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0


class ForexPriceCreate(ForexPriceBase):
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    atr_14: Optional[float] = None


class ForexPriceResponse(ForexPriceBase):
    id: uuid.UUID
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    atr_14: Optional[float] = None

    class Config:
        from_attributes = True


class CurrentPriceResponse(BaseModel):
    pair: str
    bid: float
    ask: float
    spread: float
    timestamp: datetime
    change_24h: float
    change_24h_percent: float
    high_24h: float
    low_24h: float


# Prediction Schemas
class PredictionBase(BaseModel):
    pair: str
    horizon_minutes: int
    direction: PredictionDirection
    confidence: float = Field(ge=0, le=1)
    expected_move_pips: Optional[float] = None
    expected_move_percent: Optional[float] = None
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_reward_ratio: Optional[float] = None


class PredictionCreate(PredictionBase):
    news_id: uuid.UUID
    model_version: str
    features_used: Dict[str, Any] = {}
    feature_importance: Dict[str, float] = {}
    expires_at: datetime


class PredictionUpdate(BaseModel):
    actual_direction: Optional[PredictionDirection] = None
    actual_move_pips: Optional[float] = None
    actual_move_percent: Optional[float] = None
    outcome: Optional[str] = None
    profit_loss_pips: Optional[float] = None
    resolved_at: Optional[datetime] = None


class PredictionResponse(PredictionBase):
    id: uuid.UUID
    news_id: uuid.UUID
    model_version: str
    features_used: Dict[str, Any]
    feature_importance: Dict[str, float]
    predicted_at: datetime
    expires_at: datetime
    resolved_at: Optional[datetime] = None
    actual_direction: Optional[PredictionDirection] = None
    actual_move_pips: Optional[float] = None
    actual_move_percent: Optional[float] = None
    outcome: Optional[str] = None
    profit_loss_pips: Optional[float] = None

    class Config:
        from_attributes = True


class PredictionList(BaseModel):
    items: List[PredictionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Sentiment Schemas
class SentimentAnalysisRequest(BaseModel):
    text: str
    pair: Optional[str] = None


class SentimentAnalysisResponse(BaseModel):
    text: str
    score: float = Field(ge=-1, le=1)
    label: SentimentLabel
    confidence: float = Field(ge=0, le=1)
    details: Dict[str, Any] = {}
    pair: Optional[str] = None
    analyzed_at: datetime


class MarketSentimentResponse(BaseModel):
    pair: str
    timestamp: datetime
    overall_score: float
    overall_label: SentimentLabel
    news_sentiment: Optional[float] = None
    social_sentiment: Optional[float] = None
    technical_sentiment: Optional[float] = None
    news_count: int
    social_mentions: int
    top_bullish_factors: List[str] = []
    top_bearish_factors: List[str] = []


# Economic Event Schemas
class EconomicEventBase(BaseModel):
    name: str
    country: str
    currency: str
    scheduled_at: datetime
    impact: NewsImpact = NewsImpact.LOW
    category: Optional[str] = None
    previous: Optional[str] = None
    forecast: Optional[str] = None


class EconomicEventResponse(EconomicEventBase):
    id: uuid.UUID
    actual_release_at: Optional[datetime] = None
    actual: Optional[str] = None
    revised: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


# Model Performance Schemas
class ModelPerformanceResponse(BaseModel):
    model_name: str
    model_version: str
    pair: Optional[str] = None
    horizon_minutes: Optional[int] = None
    total_predictions: int
    correct_predictions: int
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    total_pips: float
    avg_pips_per_trade: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    period_start: datetime
    period_end: datetime
    calculated_at: datetime

    class Config:
        from_attributes = True


# WebSocket Schemas
class WSMessage(BaseModel):
    type: str
    data: Optional[Dict[str, Any]] = None


class WSSubscribeMessage(WSMessage):
    type: str = "subscribe"
    data: Dict[str, List[str]] = {"topics": []}


class WSUnsubscribeMessage(WSMessage):
    type: str = "unsubscribe"
    data: Dict[str, List[str]] = {"topics": []}


class WSGetLatestMessage(WSMessage):
    type: str = "get_latest"
    data: Dict[str, str] = {"topic": ""}


class WSPingMessage(WSMessage):
    type: str = "ping"


class WSPongMessage(WSMessage):
    type: str = "pong"
    data: Dict[str, str] = {"timestamp": ""}


class WSHeartbeatMessage(WSMessage):
    type: str = "heartbeat"
    data: Dict[str, Any] = {"timestamp": "", "connections": 0}


class WSPredictionMessage(WSMessage):
    type: str = "prediction"
    data: PredictionResponse


class WSNewsMessage(WSMessage):
    type: str = "news"
    data: NewsArticleResponse


class WSPriceMessage(WSMessage):
    type: str = "price"
    data: CurrentPriceResponse


class WSSentimentMessage(WSMessage):
    type: str = "sentiment"
    data: MarketSentimentResponse


# Filter/Query Schemas
class NewsFilter(BaseModel):
    source: Optional[List[NewsSource]] = None
    pairs: Optional[List[str]] = None
    impact_level: Optional[List[NewsImpact]] = None
    sentiment_label: Optional[List[SentimentLabel]] = None
    categories: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "published_at"
    sort_order: str = "desc"


class PredictionFilter(BaseModel):
    pair: Optional[List[str]] = None
    horizon_minutes: Optional[List[int]] = None
    direction: Optional[List[PredictionDirection]] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    outcome: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "predicted_at"
    sort_order: str = "desc"


# Stats/Analytics Schemas
class PairStats(BaseModel):
    pair: str
    current_price: float
    change_24h: float
    change_24h_percent: float
    volume_24h: float
    high_24h: float
    low_24h: float
    prediction_count_24h: int
    avg_confidence_24h: float
    accuracy_24h: Optional[float] = None
    sentiment: SentimentLabel
    sentiment_score: float


class SystemStats(BaseModel):
    total_news_24h: int
    total_predictions_24h: int
    avg_prediction_confidence: float
    overall_accuracy: Optional[float] = None
    active_pairs: int
    ws_connections: int
    news_sources_active: int
    last_model_update: Optional[datetime] = None
    uptime_seconds: float


# Error Schemas
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorResponse(BaseModel):
    detail: List[Dict[str, Any]]
    code: str = "validation_error"
    timestamp: datetime = Field(default_factory=datetime.utcnow)