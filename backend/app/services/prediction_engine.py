import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
import structlog
import uuid

from app.config import settings
from app.db.session import get_db
from app.db.models import NewsArticle, Prediction, ForexPrice, PredictionDirection, NewsImpact
from app.ml.models.sentiment_analyzer import SentimentAnalyzer
from app.ml.models.market_predictor import MarketPredictorService
from app.services.forex_data import ForexDataService
from app.services.news_ingestion import NewsIngestionService

logger = structlog.get_logger()


class PredictionEngine:
    def __init__(
        self,
        sentiment_analyzer: SentimentAnalyzer,
        market_predictor: MarketPredictorService,
        forex_service: ForexDataService,
        news_service: NewsIngestionService
    ):
        self.sentiment_analyzer = sentiment_analyzer
        self.market_predictor = market_predictor
        self.forex_service = forex_service
        self.news_service = news_service

        self.running = False
        self.prediction_task = None
        self.resolution_task = None

    async def start_prediction_loop(self):
        self.running = True
        self.prediction_task = asyncio.create_task(self._prediction_loop())
        self.resolution_task = asyncio.create_task(self._resolution_loop())
        logger.info("Prediction engine started")

    async def stop(self):
        self.running = False
        for task in [self.prediction_task, self.resolution_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("Prediction engine stopped")

    async def _prediction_loop(self):
        while self.running:
            try:
                await self.process_new_news()
                await self.generate_periodic_predictions()
            except Exception as e:
                logger.error("Error in prediction loop", error=str(e))

            await asyncio.sleep(30)  # Check every 30 seconds

    async def _resolution_loop(self):
        while self.running:
            try:
                await self.resolve_expired_predictions()
            except Exception as e:
                logger.error("Error in resolution loop", error=str(e))

            await asyncio.sleep(60)  # Check every minute

    async def process_new_news(self):
        """Process recent high-impact news and generate predictions"""
        async for db in get_db():
            # Get unprocessed high-impact news from last 10 minutes
            cutoff = datetime.utcnow() - timedelta(minutes=10)
            result = await db.execute(
                select(NewsArticle)
                .where(
                    and_(
                        NewsArticle.published_at >= cutoff,
                        NewsArticle.impact_level.in_([NewsImpact.HIGH, NewsImpact.CRITICAL, NewsImpact.MEDIUM]),
                        NewsArticle.sentiment_label.isnot(None)
                    )
                )
                .order_by(desc(NewsArticle.published_at))
                .limit(20)
            )
            news_articles = result.scalars().all()

            for article in news_articles:
                # Check if already processed
                existing = await db.execute(
                    select(Prediction).where(Prediction.news_id == article.id)
                )
                if existing.scalar_one_or_none():
                    continue

                await self.generate_predictions_for_news(article, db)

    async def generate_predictions_for_news(self, article: NewsArticle, db: AsyncSession):
        """Generate predictions for all related pairs for a news article"""
        if not article.related_pairs:
            return

        # Get market data for each pair
        for pair in article.related_pairs:
            try:
                market_data = await self._get_market_data_for_pair(pair, db)
                if not market_data:
                    continue

                # Prepare news data
                news_data = {
                    'sentiment': {
                        'score': article.sentiment_score or 0,
                        'confidence': article.sentiment_confidence or 0
                    },
                    'impact_level': article.impact_level.value,
                    'count_1h': await self._count_recent_news(pair, 1, db),
                    'count_4h': await self._count_recent_news(pair, 4, db),
                    'bullish_count': await self._count_sentiment_news(pair, 'bullish', db),
                    'bearish_count': await self._count_sentiment_news(pair, 'bearish', db),
                }

                # Generate predictions for each horizon
                for horizon in settings.PREDICTION_HORIZON_MINUTES:
                    prediction_result = await self.market_predictor.predict(
                        pair=pair,
                        news_data=news_data,
                        market_data=market_data,
                        horizon_minutes=horizon
                    )

                    # Only save if confidence meets threshold
                    if prediction_result['confidence'] >= settings.CONFIDENCE_THRESHOLD:
                        await self._save_prediction(
                            db, article, pair, horizon, prediction_result, market_data
                        )

            except Exception as e:
                logger.error(f"Failed to generate predictions for {pair}", error=str(e))

    async def _get_market_data_for_pair(self, pair: str, db: AsyncSession) -> Optional[Dict]:
        """Get current market data for a pair"""
        # Get latest price from cache
        price_data = await self.forex_service.get_latest_price(pair)
        if not price_data:
            return None

        # Get recent prices for indicators
        recent_prices = await self.forex_service.get_price_history(pair, hours=2)
        price_values = [p['close'] for p in recent_prices]

        # Get latest indicators from database
        result = await db.execute(
            select(ForexPrice)
            .where(ForexPrice.pair == pair)
            .order_by(desc(ForexPrice.timestamp))
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        indicators = {}
        if latest:
            indicators = {
                'rsi_14': latest.rsi_14,
                'macd': latest.macd,
                'macd_signal': latest.macd_signal,
                'bollinger_upper': latest.bollinger_upper,
                'bollinger_lower': latest.bollinger_lower,
                'atr_14': latest.atr_14,
                'sma_20': latest.sma_20,
                'sma_50': latest.sma_50,
                'ema_12': latest.ema_12,
                'ema_26': latest.ema_26,
            }

        return {
            'current_price': price_data['mid'],
            'spread': price_data['spread'],
            'recent_prices': price_values,
            'indicators': indicators,
        }

    async def _count_recent_news(self, pair: str, hours: int, db: AsyncSession) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(func.count(NewsArticle.id))
            .where(
                and_(
                    NewsArticle.published_at >= cutoff,
                    NewsArticle.related_pairs.overlap([pair])
                )
            )
        )
        return result.scalar() or 0

    async def _count_sentiment_news(self, pair: str, sentiment: str, db: AsyncSession) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=4)
        labels = ['very_bullish', 'bullish'] if sentiment == 'bullish' else ['very_bearish', 'bearish']
        result = await db.execute(
            select(func.count(NewsArticle.id))
            .where(
                and_(
                    NewsArticle.published_at >= cutoff,
                    NewsArticle.related_pairs.overlap([pair]),
                    NewsArticle.sentiment_label.in_(labels)
                )
            )
        )
        return result.scalar() or 0

    async def _save_prediction(
        self,
        db: AsyncSession,
        article: NewsArticle,
        pair: str,
        horizon: int,
        prediction_result: Dict,
        market_data: Dict
    ):
        """Save prediction to database"""
        current_price = market_data['current_price']
        direction = prediction_result['direction']

        # Calculate price targets
        pip_value = 0.0001 if 'JPY' not in pair else 0.01
        expected_move = prediction_result['expected_move_pips'] * pip_value

        if direction == 'up':
            target_price = current_price + expected_move
            stop_loss = current_price - expected_move * 0.5  # 1:2 risk-reward
        elif direction == 'down':
            target_price = current_price - expected_move
            stop_loss = current_price + expected_move * 0.5
        else:
            target_price = current_price
            stop_loss = current_price

        risk_reward = abs(target_price - current_price) / abs(current_price - stop_loss) if stop_loss != current_price else 0

        prediction = Prediction(
            news_id=article.id,
            pair=pair,
            horizon_minutes=horizon,
            direction=PredictionDirection(direction),
            confidence=prediction_result['confidence'],
            expected_move_pips=prediction_result['expected_move_pips'],
            expected_move_percent=prediction_result['expected_move_percent'],
            entry_price=current_price,
            target_price=target_price,
            stop_loss=stop_loss,
            risk_reward_ratio=risk_reward,
            model_version=prediction_result['model_version'],
            features_used=prediction_result.get('features_used', {}),
            feature_importance=prediction_result.get('features_used', {}),  # Same for now
            expires_at=datetime.utcnow() + timedelta(minutes=horizon),
        )

        db.add(prediction)
        await db.commit()

        logger.info(
            "Prediction generated",
            pair=pair,
            horizon=horizon,
            direction=direction,
            confidence=prediction_result['confidence']
        )

    async def generate_periodic_predictions(self):
        """Generate predictions based on current market state (no news trigger)"""
        # This could generate technical-only predictions
        # For now, skip to avoid noise
        pass

    async def resolve_expired_predictions(self):
        """Resolve expired predictions by checking actual price movement"""
        async for db in get_db():
            # Get expired but unresolved predictions
            result = await db.execute(
                select(Prediction)
                .where(
                    and_(
                        Prediction.expires_at <= datetime.utcnow(),
                        Prediction.resolved_at.is_(None)
                    )
                )
                .limit(100)
            )
            expired = result.scalars().all()

            for pred in expired:
                await self._resolve_prediction(pred, db)

    async def _resolve_prediction(self, prediction: Prediction, db: AsyncSession):
        """Resolve a single prediction"""
        # Get price at expiry
        result = await db.execute(
            select(ForexPrice.close)
            .where(
                and_(
                    ForexPrice.pair == prediction.pair,
                    ForexPrice.timestamp <= prediction.expires_at
                )
            )
            .order_by(desc(ForexPrice.timestamp))
            .limit(1)
        )
        expiry_price = result.scalar_one_or_none()

        if not expiry_price:
            return

        # Calculate actual movement
        actual_move = expiry_price - prediction.entry_price
        pip_value = 0.0001 if 'JPY' not in prediction.pair else 0.01
        actual_move_pips = actual_move / pip_value
        actual_move_percent = (actual_move / prediction.entry_price) * 100

        # Determine actual direction
        if actual_move_pips > 5:  # 5 pip threshold
            actual_direction = PredictionDirection.UP
        elif actual_move_pips < -5:
            actual_direction = PredictionDirection.DOWN
        else:
            actual_direction = PredictionDirection.SIDEWAYS

        # Determine outcome
        if actual_direction == prediction.direction:
            outcome = "correct"
        elif actual_direction == PredictionDirection.SIDEWAYS:
            outcome = "partial"
        else:
            outcome = "incorrect"

        # Calculate P&L
        if prediction.direction == PredictionDirection.UP:
            profit_loss_pips = actual_move_pips
        elif prediction.direction == PredictionDirection.DOWN:
            profit_loss_pips = -actual_move_pips
        else:
            profit_loss_pips = 0

        # Update prediction
        prediction.actual_direction = actual_direction
        prediction.actual_move_pips = actual_move_pips
        prediction.actual_move_percent = actual_move_percent
        prediction.outcome = outcome
        prediction.profit_loss_pips = profit_loss_pips
        prediction.resolved_at = datetime.utcnow()

        await db.commit()

        logger.info(
            "Prediction resolved",
            prediction_id=str(prediction.id),
            outcome=outcome,
            actual_move_pips=actual_move_pips
        )

    async def get_latest_predictions(self, limit: int = 50) -> List[Dict]:
        """Get latest predictions for WebSocket broadcast"""
        async for db in get_db():
            result = await db.execute(
                select(Prediction)
                .where(Prediction.resolved_at.is_(None))
                .order_by(desc(Prediction.predicted_at))
                .limit(limit)
            )
            predictions = result.scalars().all()

            return [
                {
                    'id': str(p.id),
                    'news_id': str(p.news_id),
                    'pair': p.pair,
                    'horizon_minutes': p.horizon_minutes,
                    'direction': p.direction.value,
                    'confidence': p.confidence,
                    'expected_move_pips': p.expected_move_pips,
                    'expected_move_percent': p.expected_move_percent,
                    'entry_price': p.entry_price,
                    'target_price': p.target_price,
                    'stop_loss': p.stop_loss,
                    'risk_reward_ratio': p.risk_reward_ratio,
                    'predicted_at': p.predicted_at.isoformat(),
                    'expires_at': p.expires_at.isoformat(),
                    'model_version': p.model_version,
                }
                for p in predictions
            ]

    async def get_prediction_stats(self) -> Dict:
        """Get prediction performance statistics"""
        async for db in get_db():
            # Last 24 hours
            cutoff = datetime.utcnow() - timedelta(hours=24)

            result = await db.execute(
                select(
                    func.count(Prediction.id),
                    func.avg(Prediction.confidence),
                    func.sum(func.case((Prediction.outcome == 'correct', 1), else_=0)),
                    func.sum(func.case((Prediction.outcome == 'incorrect', 1), else_=0)),
                    func.avg(Prediction.profit_loss_pips),
                )
                .where(
                    and_(
                        Prediction.predicted_at >= cutoff,
                        Prediction.resolved_at.isnot(None)
                    )
                )
            )
            row = result.one()

            total, avg_conf, correct, incorrect, avg_pips = row

            accuracy = correct / (correct + incorrect) if (correct + incorrect) > 0 else None

            return {
                'total_predictions_24h': total or 0,
                'resolved_predictions_24h': (correct or 0) + (incorrect or 0),
                'correct_predictions_24h': correct or 0,
                'incorrect_predictions_24h': incorrect or 0,
                'accuracy_24h': accuracy,
                'avg_confidence_24h': float(avg_conf) if avg_conf else 0,
                'avg_pips_24h': float(avg_pips) if avg_pips else 0,
            }