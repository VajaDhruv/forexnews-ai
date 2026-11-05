from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.config import settings
from app.db.session import get_db
from app.db.models import MarketSentiment, NewsArticle, SentimentLabel
from app.schemas import MarketSentimentResponse, SentimentAnalysisRequest, SentimentAnalysisResponse
from app.main import sentiment_analyzer

router = APIRouter()
logger = structlog.get_logger()


@router.get("/market/{pair}", response_model=MarketSentimentResponse)
async def get_market_sentiment(
    pair: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current market sentiment for a pair"""

    result = await db.execute(
        select(MarketSentiment)
        .where(MarketSentiment.pair == pair.upper())
        .order_by(desc(MarketSentiment.timestamp))
        .limit(1)
    )
    sentiment = result.scalar_one_or_none()

    if not sentiment:
        raise HTTPException(status_code=404, detail=f"No sentiment data for {pair}")

    return MarketSentimentResponse(
        pair=sentiment.pair,
        timestamp=sentiment.timestamp,
        overall_score=sentiment.overall_score,
        overall_label=sentiment.overall_label,
        news_sentiment=sentiment.news_sentiment,
        social_sentiment=sentiment.social_sentiment,
        technical_sentiment=sentiment.technical_sentiment,
        news_count=sentiment.news_count,
        social_mentions=sentiment.social_mentions,
        top_bullish_factors=sentiment.top_bullish_factors,
        top_bearish_factors=sentiment.top_bearish_factors,
    )


@router.get("/market", response_model=List[MarketSentimentResponse])
async def get_all_market_sentiment(
    db: AsyncSession = Depends(get_db)
):
    """Get latest market sentiment for all pairs"""

    # Get latest sentiment for each pair
    subquery = select(
        MarketSentiment.pair,
        func.max(MarketSentiment.timestamp).label('max_ts')
    ).group_by(MarketSentiment.pair).subquery()

    result = await db.execute(
        select(MarketSentiment)
        .join(
            subquery,
            and_(
                MarketSentiment.pair == subquery.c.pair,
                MarketSentiment.timestamp == subquery.c.max_ts
            )
        )
    )
    sentiments = result.scalars().all()

    return [
        MarketSentimentResponse(
            pair=s.pair,
            timestamp=s.timestamp,
            overall_score=s.overall_score,
            overall_label=s.overall_label,
            news_sentiment=s.news_sentiment,
            social_sentiment=s.social_sentiment,
            technical_sentiment=s.technical_sentiment,
            news_count=s.news_count,
            social_mentions=s.social_mentions,
            top_bullish_factors=s.top_bullish_factors,
            top_bearish_factors=s.top_bearish_factors,
        )
        for s in sentiments
    ]


@router.get("/news/{pair}")
async def get_news_sentiment(
    pair: str,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get news sentiment breakdown for a pair"""

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        select(
            NewsArticle.sentiment_label,
            func.count(NewsArticle.id),
            func.avg(NewsArticle.sentiment_score),
            func.avg(NewsArticle.sentiment_confidence),
        )
        .where(
            and_(
                NewsArticle.published_at >= cutoff,
                NewsArticle.related_pairs.overlap([pair.upper()]),
                NewsArticle.sentiment_label.isnot(None)
            )
        )
        .group_by(NewsArticle.sentiment_label)
    )

    breakdown = {}
    for row in result.fetchall():
        breakdown[str(row[0])] = {
            'count': row[1],
            'avg_score': float(row[2]) if row[2] else 0,
            'avg_confidence': float(row[3]) if row[3] else 0,
        }

    # Overall stats
    overall_result = await db.execute(
        select(
            func.count(NewsArticle.id),
            func.avg(NewsArticle.sentiment_score),
        )
        .where(
            and_(
                NewsArticle.published_at >= cutoff,
                NewsArticle.related_pairs.overlap([pair.upper()]),
                NewsArticle.sentiment_score.isnot(None)
            )
        )
    )
    total, avg_score = overall_result.one()

    return {
        'pair': pair.upper(),
        'period_hours': hours,
        'total_articles': total or 0,
        'average_sentiment_score': float(avg_score) if avg_score else 0,
        'breakdown': breakdown,
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/analyze", response_model=SentimentAnalysisResponse)
async def analyze_text_sentiment(
    request: SentimentAnalysisRequest
):
    """Analyze sentiment of arbitrary text"""

    if not sentiment_analyzer:
        raise HTTPException(status_code=503, detail="Sentiment analyzer not available")

    result = await sentiment_analyzer.analyze(request.text, [request.pair] if request.pair else [])

    return SentimentAnalysisResponse(
        text=request.text,
        score=result['score'],
        label=result['label'],
        confidence=result['confidence'],
        details=result['details'],
        pair=request.pair,
        analyzed_at=datetime.utcnow()
    )


@router.get("/history/{pair}")
async def get_sentiment_history(
    pair: str,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get sentiment history for a pair"""

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        select(MarketSentiment)
        .where(
            and_(
                MarketSentiment.pair == pair.upper(),
                MarketSentiment.timestamp >= cutoff
            )
        )
        .order_by(MarketSentiment.timestamp)
    )
    sentiments = result.scalars().all()

    return [
        {
            'timestamp': s.timestamp.isoformat(),
            'overall_score': s.overall_score,
            'overall_label': s.overall_label.value,
            'news_sentiment': s.news_sentiment,
            'social_sentiment': s.social_sentiment,
            'technical_sentiment': s.technical_sentiment,
            'news_count': s.news_count,
        }
        for s in sentiments
    ]