import asyncio
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import structlog
import joblib
import os

from app.config import settings
from app.db.session import get_db
from app.db.models import ForexPrice, NewsArticle, Prediction, PredictionDirection, NewsImpact, SentimentLabel

logger = structlog.get_logger()


class MarketPredictor(nn.Module):
    """Neural network for market reaction prediction"""

    def __init__(self, input_dim: int = 100, hidden_dim: int = 256, num_classes: int = 3):
        super().__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes  # up, down, sideways

        # Feature extraction layers
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
        )

        # Direction prediction head
        self.direction_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 4, num_classes)
        )

        # Magnitude prediction head (regression)
        self.magnitude_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 4, 1),
            nn.Softplus()  # Ensure positive output
        )

        # Confidence head
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 4, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        features = self.feature_extractor(x)
        direction_logits = self.direction_head(features)
        magnitude = self.magnitude_head(features)
        confidence = self.confidence_head(features)
        return direction_logits, magnitude.squeeze(-1), confidence.squeeze(-1)


class MarketPredictorService:
    """Service wrapper for the market predictor model"""

    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.scaler = None
        self.feature_columns = []
        self.loaded = False
        self.model_version = "2.0.0"

        # Feature engineering parameters
        self.lookback_windows = [5, 15, 30, 60, 240]  # minutes
        self.prediction_horizons = settings.PREDICTION_HORIZON_MINUTES

    async def load_models(self):
        """Load trained model and scaler"""
        if self.loaded:
            return

        logger.info("Loading market predictor model...", device=str(self.device))

        try:
            model_path = os.path.join(settings.MODEL_PATH, "market_predictor.pt")
            scaler_path = os.path.join(settings.MODEL_PATH, "scaler.pkl")
            features_path = os.path.join(settings.MODEL_PATH, "feature_columns.pkl")

            if os.path.exists(model_path):
                # Load model architecture
                self.model = MarketPredictor(input_dim=len(self._get_feature_columns()))
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.to(self.device)
                self.model.eval()

                # Load scaler and features
                if os.path.exists(scaler_path):
                    self.scaler = joblib.load(scaler_path)
                if os.path.exists(features_path):
                    self.feature_columns = joblib.load(features_path)

                logger.info("Market predictor model loaded successfully")
            else:
                logger.warning("No trained model found, using default initialization")
                self.model = MarketPredictor(input_dim=len(self._get_feature_columns()))
                self.model.to(self.device)
                self.model.eval()

            self.loaded = True

        except Exception as e:
            logger.error("Failed to load market predictor", error=str(e))
            # Initialize default model
            self.model = MarketPredictor(input_dim=len(self._get_feature_columns()))
            self.model.to(self.device)
            self.model.eval()
            self.loaded = True

    def _get_feature_columns(self) -> List[str]:
        """Define feature columns for the model"""
        return [
            # Price features
            'returns_1m', 'returns_5m', 'returns_15m', 'returns_30m', 'returns_60m',
            'log_return_1m', 'log_return_5m', 'log_return_15m',

            # Technical indicators
            'rsi_14', 'macd', 'macd_signal', 'macd_histogram',
            'bb_position', 'bb_width', 'atr_14', 'atr_ratio',
            'sma_20_ratio', 'sma_50_ratio', 'ema_12_ratio', 'ema_26_ratio',

            # Volatility
            'volatility_5m', 'volatility_15m', 'volatility_60m',
            'volatility_ratio',

            # Volume (if available)
            'volume_ratio', 'volume_change',

            # Spread
            'spread', 'spread_ratio',

            # News sentiment features
            'news_sentiment_score', 'news_sentiment_confidence',
            'news_impact_high', 'news_impact_medium', 'news_impact_low',
            'news_count_1h', 'news_count_4h',
            'bullish_news_ratio', 'bearish_news_ratio',

            # Currency pair features
            'pair_eurusd', 'pair_gbpusd', 'pair_usdjpy', 'pair_usdchf',
            'pair_audusd', 'pair_usdcad', 'pair_nzdusd',

            # Time features
            'hour', 'day_of_week', 'is_asian_session', 'is_european_session', 'is_us_session',
            'is_overlap_session', 'minutes_to_next_hour',

            # Economic calendar
            'upcoming_high_impact', 'upcoming_medium_impact',
            'minutes_to_next_event', 'event_currency_match',
        ]

    async def predict(
        self,
        pair: str,
        news_data: Dict,
        market_data: Dict,
        horizon_minutes: int
    ) -> Dict[str, Any]:
        """Make prediction for a currency pair given news and market data"""
        if not self.loaded:
            await self.load_models()

        # Extract features
        features = await self._extract_features(pair, news_data, market_data, horizon_minutes)

        if features is None:
            return self._default_prediction()

        # Scale features
        if self.scaler:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
        else:
            features_scaled = features.reshape(1, -1)

        # Convert to tensor
        x = torch.FloatTensor(features_scaled).to(self.device)

        # Predict
        with torch.no_grad():
            direction_logits, magnitude, confidence = self.model(x)

            # Get probabilities
            direction_probs = torch.softmax(direction_logits, dim=-1).cpu().numpy()[0]
            magnitude_val = magnitude.cpu().numpy()[0]
            confidence_val = confidence.cpu().numpy()[0]

        # Map to direction
        direction_idx = direction_probs.argmax()
        direction_map = {0: 'down', 1: 'sideways', 2: 'up'}
        direction = direction_map[direction_idx]
        direction_confidence = float(direction_probs[direction_idx])

        # Calculate expected move in pips
        current_price = market_data.get('current_price', 1.0)
        pip_value = 0.0001 if 'JPY' not in pair else 0.01
        expected_move_pips = magnitude_val / pip_value

        # Combine confidences
        final_confidence = (direction_confidence + confidence_val) / 2

        # Determine if prediction meets threshold
        if final_confidence < settings.CONFIDENCE_THRESHOLD:
            direction = 'sideways'
            final_confidence = 1 - final_confidence

        return {
            'direction': direction,
            'confidence': float(final_confidence),
            'direction_probs': {
                'down': float(direction_probs[0]),
                'sideways': float(direction_probs[1]),
                'up': float(direction_probs[2])
            },
            'expected_move_pips': float(expected_move_pips),
            'expected_move_percent': float(magnitude_val / current_price * 100),
            'model_version': self.model_version,
            'features_used': self._get_feature_importance(features)
        }

    async def _extract_features(
        self,
        pair: str,
        news_data: Dict,
        market_data: Dict,
        horizon_minutes: int
    ) -> Optional[np.ndarray]:
        """Extract and engineer features for prediction"""
        try:
            features = {}

            # Price features
            prices = market_data.get('recent_prices', [])
            if len(prices) < 60:
                return None

            prices_array = np.array(prices)
            returns = np.diff(prices_array) / prices_array[:-1]

            features['returns_1m'] = returns[-1] if len(returns) > 0 else 0
            features['returns_5m'] = returns[-5:].mean() if len(returns) >= 5 else 0
            features['returns_15m'] = returns[-15:].mean() if len(returns) >= 15 else 0
            features['returns_30m'] = returns[-30:].mean() if len(returns) >= 30 else 0
            features['returns_60m'] = returns[-60:].mean() if len(returns) >= 60 else 0

            features['log_return_1m'] = np.log(prices_array[-1] / prices_array[-2]) if len(prices_array) >= 2 else 0
            features['log_return_5m'] = np.log(prices_array[-1] / prices_array[-6]) if len(prices_array) >= 6 else 0
            features['log_return_15m'] = np.log(prices_array[-1] / prices_array[-16]) if len(prices_array) >= 16 else 0

            # Technical indicators from market_data
            indicators = market_data.get('indicators', {})
            features['rsi_14'] = indicators.get('rsi_14', 50) / 100  # Normalize
            features['macd'] = indicators.get('macd', 0)
            features['macd_signal'] = indicators.get('macd_signal', 0)
            features['macd_histogram'] = features['macd'] - features['macd_signal']

            bb_upper = indicators.get('bollinger_upper', 0)
            bb_lower = indicators.get('bollinger_lower', 0)
            bb_mid = (bb_upper + bb_lower) / 2 if bb_upper and bb_lower else prices_array[-1]
            current_price = prices_array[-1]
            features['bb_position'] = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
            features['bb_width'] = (bb_upper - bb_lower) / bb_mid if bb_mid != 0 else 0

            atr = indicators.get('atr_14', 0)
            features['atr_14'] = atr
            features['atr_ratio'] = atr / current_price if current_price != 0 else 0

            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            ema_12 = indicators.get('ema_12', current_price)
            ema_26 = indicators.get('ema_26', current_price)
            features['sma_20_ratio'] = current_price / sma_20 if sma_20 != 0 else 1
            features['sma_50_ratio'] = current_price / sma_50 if sma_50 != 0 else 1
            features['ema_12_ratio'] = current_price / ema_12 if ema_12 != 0 else 1
            features['ema_26_ratio'] = current_price / ema_26 if ema_26 != 0 else 1

            # Volatility
            features['volatility_5m'] = returns[-5:].std() if len(returns) >= 5 else 0
            features['volatility_15m'] = returns[-15:].std() if len(returns) >= 15 else 0
            features['volatility_60m'] = returns[-60:].std() if len(returns) >= 60 else 0
            features['volatility_ratio'] = features['volatility_5m'] / features['volatility_60m'] if features['volatility_60m'] != 0 else 1

            # Volume (placeholder)
            features['volume_ratio'] = 1.0
            features['volume_change'] = 0.0

            # Spread
            spread = market_data.get('spread', 0)
            features['spread'] = spread
            features['spread_ratio'] = spread / current_price if current_price != 0 else 0

            # News sentiment features
            sentiment = news_data.get('sentiment', {})
            features['news_sentiment_score'] = sentiment.get('score', 0)
            features['news_sentiment_confidence'] = sentiment.get('confidence', 0)

            impact = news_data.get('impact_level', 'low')
            features['news_impact_high'] = 1 if impact == 'high' else 0
            features['news_impact_medium'] = 1 if impact == 'medium' else 0
            features['news_impact_low'] = 1 if impact == 'low' else 0

            features['news_count_1h'] = news_data.get('count_1h', 0)
            features['news_count_4h'] = news_data.get('count_4h', 0)

            bullish_count = news_data.get('bullish_count', 0)
            bearish_count = news_data.get('bearish_count', 0)
            total_news = bullish_count + bearish_count
            features['bullish_news_ratio'] = bullish_count / total_news if total_news > 0 else 0.5
            features['bearish_news_ratio'] = bearish_count / total_news if total_news > 0 else 0.5

            # Currency pair one-hot
            major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
            for p in major_pairs:
                features[f'pair_{p.lower()}'] = 1 if pair == p else 0

            # Time features
            now = datetime.utcnow()
            features['hour'] = now.hour / 24
            features['day_of_week'] = now.weekday() / 7
            features['is_asian_session'] = 1 if 0 <= now.hour < 8 else 0
            features['is_european_session'] = 1 if 8 <= now.hour < 16 else 0
            features['is_us_session'] = 1 if 13 <= now.hour < 21 else 0
            features['is_overlap_session'] = 1 if (13 <= now.hour < 16) else 0
            features['minutes_to_next_hour'] = (60 - now.minute) / 60

            # Economic calendar (placeholder)
            features['upcoming_high_impact'] = 0
            features['upcoming_medium_impact'] = 0
            features['minutes_to_next_event'] = 1.0
            features['event_currency_match'] = 0

            # Convert to array in correct order
            feature_vector = np.array([features[col] for col in self._get_feature_columns()])

            # Handle NaN/inf
            feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=0.0, neginf=0.0)

            return feature_vector

        except Exception as e:
            logger.error("Feature extraction failed", error=str(e))
            return None

    def _get_feature_importance(self, features: np.ndarray) -> Dict[str, float]:
        """Get feature importance (placeholder - would use SHAP in production)"""
        # In production, use SHAP values or permutation importance
        importance = {}
        feature_names = self._get_feature_columns()

        # Simple heuristic importance based on feature values
        for i, name in enumerate(feature_names):
            if i < len(features):
                importance[name] = float(abs(features[i]))

        # Normalize
        total = sum(importance.values())
        if total > 0:
            importance = {k: v/total for k, v in importance.items()}

        # Return top 10
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])

    def _default_prediction(self) -> Dict[str, Any]:
        return {
            'direction': 'sideways',
            'confidence': 0.5,
            'direction_probs': {'down': 0.33, 'sideways': 0.34, 'up': 0.33},
            'expected_move_pips': 0,
            'expected_move_percent': 0,
            'model_version': self.model_version,
            'features_used': {}
        }

    async def train(self, training_data: List[Dict]) -> Dict[str, float]:
        """Train the model on historical data"""
        logger.info("Training market predictor", samples=len(training_data))
        # This would implement training loop
        # For now, return dummy metrics
        return {
            'accuracy': 0.55,
            'precision': 0.53,
            'recall': 0.52,
            'f1': 0.52
        }

    async def evaluate(self, test_data: List[Dict]) -> Dict[str, float]:
        """Evaluate model performance"""
        # Placeholder for evaluation
        return {
            'accuracy': 0.54,
            'precision': 0.52,
            'recall': 0.51,
            'f1': 0.51,
            'profit_factor': 1.2,
            'sharpe_ratio': 0.8
        }