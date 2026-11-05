# Shared application state - avoids circular imports
from typing import Optional
from app.services.news_ingestion import NewsIngestionService
from app.services.forex_data import ForexDataService
from app.services.prediction_engine import PredictionEngine
from app.ml.models.sentiment_analyzer import SentimentAnalyzer
from app.ml.models.market_predictor import MarketPredictor
from app.ws.manager import ConnectionManager

# Global service instances (initialized in main.py lifespan)
news_service: Optional[NewsIngestionService] = None
forex_service: Optional[ForexDataService] = None
prediction_engine: Optional[PredictionEngine] = None
sentiment_analyzer: Optional[SentimentAnalyzer] = None
market_predictor: Optional[MarketPredictor] = None
manager: Optional[ConnectionManager] = None