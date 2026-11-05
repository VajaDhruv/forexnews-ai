from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.config import settings
from app.db.session import get_db
from app.db.models import ForexPrice
from app.schemas import (
    ForexPriceResponse, CurrentPriceResponse, PairStats, SystemStats
)
from app.core.state import forex_service

router = APIRouter()
logger = structlog.get_logger()


@router.get("/prices/current", response_model=List[CurrentPriceResponse])
async def get_current_prices(
    pairs: Optional[List[str]] = Query(None)
):
    """Get current prices for all or specified pairs"""

    if not forex_service:
        raise HTTPException(status_code=503, detail="Forex service not available")

    prices = await forex_service.get_current_prices()

    if pairs:
        prices = [p for p in prices if p['pair'] in pairs]

    return prices


@router.get("/prices/{pair}/current", response_model=CurrentPriceResponse)
async def get_current_price(pair: str):
    """Get current price for a specific pair"""

    if not forex_service:
        raise HTTPException(status_code=503, detail="Forex service not available")

    price = await forex_service.get_latest_price(pair.upper())

    if not price:
        raise HTTPException(status_code=404, detail=f"Price not found for {pair}")

    # Get 24h change
    change_data = await forex_service._get_24h_change(pair.upper())

    return CurrentPriceResponse(
        pair=pair.upper(),
        bid=price['bid'],
        ask=price['ask'],
        spread=price['spread'],
        timestamp=datetime.fromisoformat(price['timestamp']),
        change_24h=change_data['change'],
        change_24h_percent=change_data['change_percent'],
        high_24h=change_data['high'],
        low_24h=change_data['low'],
    )


@router.get("/prices/{pair}/history", response_model=List[ForexPriceResponse])
async def get_price_history(
    pair: str,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get historical price data for a pair"""

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        select(ForexPrice)
        .where(
            and_(
                ForexPrice.pair == pair.upper(),
                ForexPrice.timestamp >= cutoff
            )
        )
        .order_by(ForexPrice.timestamp)
    )
    prices = result.scalars().all()

    if not prices:
        raise HTTPException(status_code=404, detail=f"No price data for {pair}")

    return [
        ForexPriceResponse(
            id=p.id,
            pair=p.pair,
            timestamp=p.timestamp,
            open=p.open,
            high=p.high,
            low=p.low,
            close=p.close,
            volume=p.volume,
            bid=p.bid,
            ask=p.ask,
            spread=p.spread,
            sma_20=p.sma_20,
            sma_50=p.sma_50,
            ema_12=p.ema_12,
            ema_26=p.ema_26,
            rsi_14=p.rsi_14,
            macd=p.macd,
            macd_signal=p.macd_signal,
            bollinger_upper=p.bollinger_upper,
            bollinger_lower=p.bollinger_lower,
            atr_14=p.atr_14,
        )
        for p in prices
    ]


@router.get("/pairs", response_model=List[str])
async def get_available_pairs():
    """Get list of available forex pairs"""
    return settings.FOREX_PAIRS


@router.get("/stats/{pair}", response_model=PairStats)
async def get_pair_stats(
    pair: str,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for a specific pair"""

    pair = pair.upper()
    if pair not in settings.FOREX_PAIRS:
        raise HTTPException(status_code=404, detail=f"Pair {pair} not supported")

    # Get current price
    price_data = await forex_service.get_latest_price(pair) if forex_service else None

    if not price_data:
        raise HTTPException(status_code=503, detail="Price data not available")

    # Get 24h change
    change_data = await forex_service._get_24h_change(pair)

    # Get 24h volume (placeholder)
    volume_24h = 0

    # Get prediction stats
    cutoff = datetime.utcnow() - timedelta(hours=24)
    pred_result = await db.execute(
        select(func.count())
        .select_from(
            select(1).where(
                and_(
                    # This would need Prediction model imported
                )
            ).subquery()
        )
    )
    prediction_count = pred_result.scalar() or 0

    # Get sentiment
    from app.db.models import MarketSentiment
    sentiment_result = await db.execute(
        select(MarketSentiment)
        .where(MarketSentiment.pair == pair)
        .order_by(desc(MarketSentiment.timestamp))
        .limit(1)
    )
    sentiment = sentiment_result.scalar_one_or_none()

    return PairStats(
        pair=pair,
        current_price=price_data['mid'],
        change_24h=change_data['change'],
        change_24h_percent=change_data['change_percent'],
        volume_24h=volume_24h,
        high_24h=change_data['high'],
        low_24h=change_data['low'],
        prediction_count_24h=prediction_count,
        avg_confidence_24h=0.0,
        accuracy_24h=None,
        sentiment=sentiment.overall_label if sentiment else None,
        sentiment_score=sentiment.overall_score if sentiment else 0.0,
    )


@router.get("/stats/system", response_model=SystemStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get overall system statistics"""

    from app.core.state import news_service, prediction_engine, manager
    from app.db.models import NewsArticle, Prediction

    cutoff = datetime.utcnow() - timedelta(hours=24)

    # News count
    news_result = await db.execute(
        select(func.count(NewsArticle.id))
        .where(NewsArticle.published_at >= cutoff)
    )
    total_news = news_result.scalar() or 0

    # Prediction count
    pred_result = await db.execute(
        select(func.count(Prediction.id))
        .where(Prediction.predicted_at >= cutoff)
    )
    total_predictions = pred_result.scalar() or 0

    # Average confidence
    conf_result = await db.execute(
        select(func.avg(Prediction.confidence))
        .where(Prediction.predicted_at >= cutoff)
    )
    avg_confidence = conf_result.scalar() or 0

    # Accuracy
    resolved_result = await db.execute(
        select(
            func.sum(func.case((Prediction.outcome == 'correct', 1), else_=0)),
            func.sum(func.case((Prediction.outcome == 'incorrect', 1), else_=0)),
        )
        .where(
            and_(
                Prediction.predicted_at >= cutoff,
                Prediction.resolved_at.isnot(None)
            )
        )
    )
    correct, incorrect = resolved_result.one()
    accuracy = correct / (correct + incorrect) if (correct + incorrect) > 0 else None

    # Active pairs with recent data
    active_pairs_result = await db.execute(
        select(func.count(func.distinct(ForexPrice.pair)))
        .where(ForexPrice.timestamp >= cutoff)
    )
    active_pairs = active_pairs_result.scalar() or 0

    # WebSocket connections
    ws_connections = sum(len(c) for c in manager.active_connections.values()) if manager else 0

    return SystemStats(
        total_news_24h=total_news,
        total_predictions_24h=total_predictions,
        avg_prediction_confidence=float(avg_confidence),
        overall_accuracy=float(accuracy) if accuracy else None,
        active_pairs=active_pairs,
        ws_connections=ws_connections,
        news_sources_active=len(settings.NEWS_SOURCES),
        last_model_update=None,
        uptime_seconds=0,  # Would track actual uptime
    )