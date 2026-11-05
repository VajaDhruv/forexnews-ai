from sqlalchemy import Column, String, Float, DateTime, Integer, Text, Index, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.session import Base
import uuid
import enum
from datetime import datetime


class NewsSource(str, enum.Enum):
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


class NewsImpact(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SentimentLabel(str, enum.Enum):
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"


class PredictionDirection(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False, index=True)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    url = Column(String(500), unique=True, nullable=False, index=True)
    source = Column(SQLEnum(NewsSource), nullable=False, index=True)
    published_at = Column(DateTime, nullable=False, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Forex relevance
    related_pairs = Column(JSONB, default=list, nullable=False)  # ["EURUSD", "GBPUSD"]
    impact_level = Column(SQLEnum(NewsImpact), default=NewsImpact.LOW, index=True)
    categories = Column(JSONB, default=list, nullable=False)  # ["central_bank", "economic_data", "geopolitical"]

    # Sentiment
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    sentiment_label = Column(SQLEnum(SentimentLabel), nullable=True, index=True)
    sentiment_confidence = Column(Float, nullable=True)
    sentiment_details = Column(JSONB, default=dict, nullable=False)

    # Embeddings for similarity search
    embedding = Column(JSONB, nullable=True)

    # Relationships
    predictions = relationship("Prediction", back_populates="news_article", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_news_published_source', 'published_at', 'source'),
        Index('ix_news_sentiment_pair', 'sentiment_label', 'related_pairs'),
    )


class ForexPrice(Base):
    __tablename__ = "forex_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # OHLCV
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, default=0)

    # Technical indicators
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    ema_12 = Column(Float, nullable=True)
    ema_26 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    atr_14 = Column(Float, nullable=True)

    # Spread
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    spread = Column(Float, nullable=True)

    __table_args__ = (
        Index('ix_forex_pair_timestamp', 'pair', 'timestamp'),
        Index('ix_forex_timestamp', 'timestamp'),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    news_id = Column(UUID(as_uuid=True), ForeignKey("news_articles.id"), nullable=False, index=True)
    pair = Column(String(10), nullable=False, index=True)

    # Prediction details
    horizon_minutes = Column(Integer, nullable=False)  # 15, 30, 60, 240, 1440
    direction = Column(SQLEnum(PredictionDirection), nullable=False, index=True)
    confidence = Column(Float, nullable=False)  # 0 to 1
    expected_move_pips = Column(Float, nullable=True)
    expected_move_percent = Column(Float, nullable=True)

    # Price targets
    entry_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)

    # Model info
    model_version = Column(String(50), nullable=False)
    features_used = Column(JSONB, default=dict, nullable=False)
    feature_importance = Column(JSONB, default=dict, nullable=False)

    # Timestamps
    predicted_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    # Outcome tracking
    actual_direction = Column(SQLEnum(PredictionDirection), nullable=True)
    actual_move_pips = Column(Float, nullable=True)
    actual_move_percent = Column(Float, nullable=True)
    outcome = Column(String(20), nullable=True)  # "correct", "incorrect", "partial", "pending"
    profit_loss_pips = Column(Float, nullable=True)

    # Relationships
    news_article = relationship("NewsArticle", back_populates="predictions")

    __table_args__ = (
        Index('ix_prediction_pair_horizon', 'pair', 'horizon_minutes'),
        Index('ix_prediction_confidence', 'confidence'),
        Index('ix_prediction_expires', 'expires_at'),
    )


class MarketSentiment(Base):
    __tablename__ = "market_sentiment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Aggregate sentiment
    overall_score = Column(Float, nullable=False)  # -1 to 1
    overall_label = Column(SQLEnum(SentimentLabel), nullable=False)

    # Source breakdown
    news_sentiment = Column(Float, nullable=True)
    social_sentiment = Column(Float, nullable=True)
    technical_sentiment = Column(Float, nullable=True)

    # Volume metrics
    news_count = Column(Integer, default=0)
    social_mentions = Column(Integer, default=0)

    # Key drivers
    top_bullish_factors = Column(JSONB, default=list, nullable=False)
    top_bearish_factors = Column(JSONB, default=list, nullable=False)

    __table_args__ = (
        Index('ix_sentiment_pair_timestamp', 'pair', 'timestamp'),
    )


class ModelPerformance(Base):
    __tablename__ = "model_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)
    pair = Column(String(10), nullable=True, index=True)
    horizon_minutes = Column(Integer, nullable=True)

    # Metrics
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)

    # Profit metrics
    total_pips = Column(Float, default=0)
    avg_pips_per_trade = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)

    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('ix_perf_model_pair_horizon', 'model_name', 'pair', 'horizon_minutes'),
    )


class EconomicEvent(Base):
    __tablename__ = "economic_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    country = Column(String(3), nullable=False, index=True)  # ISO code
    currency = Column(String(3), nullable=False, index=True)

    # Schedule
    scheduled_at = Column(DateTime, nullable=False, index=True)
    actual_release_at = Column(DateTime, nullable=True)

    # Values
    previous = Column(String(50), nullable=True)
    forecast = Column(String(50), nullable=True)
    actual = Column(String(50), nullable=True)
    revised = Column(String(50), nullable=True)

    # Impact
    impact = Column(SQLEnum(NewsImpact), default=NewsImpact.LOW, index=True)
    category = Column(String(50), nullable=True)  # "employment", "inflation", "gdp", "central_bank"

    # Status
    status = Column(String(20), default="scheduled")  # "scheduled", "released", "revised", "cancelled"

    __table_args__ = (
        Index('ix_event_currency_time', 'currency', 'scheduled_at'),
        Index('ix_event_impact_time', 'impact', 'scheduled_at'),
    )