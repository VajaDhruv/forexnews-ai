from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.config import settings
from app.db.session import get_db
from app.db.models import NewsArticle, NewsSource, NewsImpact, SentimentLabel
from app.schemas import (
    NewsArticleResponse, NewsArticleList, NewsFilter,
    NewsSource as NewsSourceEnum, NewsImpact as NewsImpactEnum,
    SentimentLabel as SentimentLabelEnum
)

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", response_model=NewsArticleList)
async def get_news(
    source: Optional[List[NewsSourceEnum]] = Query(None),
    pairs: Optional[List[str]] = Query(None),
    impact_level: Optional[List[NewsImpactEnum]] = Query(None),
    sentiment_label: Optional[List[SentimentLabelEnum]] = Query(None),
    categories: Optional[List[str]] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("published_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db)
):
    """Get news articles with filtering and pagination"""

    query = select(NewsArticle)

    # Apply filters
    if source:
        query = query.where(NewsArticle.source.in_(source))

    if pairs:
        # Filter by related pairs overlap
        query = query.where(NewsArticle.related_pairs.overlap(pairs))

    if impact_level:
        query = query.where(NewsArticle.impact_level.in_(impact_level))

    if sentiment_label:
        query = query.where(NewsArticle.sentiment_label.in_(sentiment_label))

    if categories:
        # Filter by categories overlap
        query = query.where(NewsArticle.categories.overlap(categories))

    if start_date:
        query = query.where(NewsArticle.published_at >= start_date)

    if end_date:
        query = query.where(NewsArticle.published_at <= end_date)

    if search:
        query = query.where(
            or_(
                NewsArticle.title.ilike(f"%{search}%"),
                NewsArticle.content.ilike(f"%{search}%"),
                NewsArticle.summary.ilike(f"%{search}%")
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(NewsArticle, sort_by, NewsArticle.published_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    result = await db.execute(query)
    articles = result.scalars().all()

    # Convert to response
    items = [
        NewsArticleResponse(
            id=a.id,
            title=a.title,
            content=a.content,
            summary=a.summary,
            url=str(a.url),
            source=a.source,
            published_at=a.published_at,
            fetched_at=a.fetched_at,
            related_pairs=a.related_pairs,
            impact_level=a.impact_level,
            categories=a.categories,
            sentiment_score=a.sentiment_score,
            sentiment_label=a.sentiment_label,
            sentiment_confidence=a.sentiment_confidence,
            sentiment_details=a.sentiment_details,
            embedding=a.embedding,
        )
        for a in articles
    ]

    return NewsArticleList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + page_size < total
    )


@router.get("/latest", response_model=List[NewsArticleResponse])
async def get_latest_news(
    limit: int = Query(50, ge=1, le=200),
    pairs: Optional[List[str]] = Query(None),
    impact_level: Optional[List[NewsImpactEnum]] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get latest news articles"""

    query = select(NewsArticle).order_by(desc(NewsArticle.published_at)).limit(limit)

    if pairs:
        query = query.where(NewsArticle.related_pairs.overlap(pairs))

    if impact_level:
        query = query.where(NewsArticle.impact_level.in_(impact_level))

    result = await db.execute(query)
    articles = result.scalars().all()

    return [
        NewsArticleResponse(
            id=a.id,
            title=a.title,
            content=a.content,
            summary=a.summary,
            url=str(a.url),
            source=a.source,
            published_at=a.published_at,
            fetched_at=a.fetched_at,
            related_pairs=a.related_pairs,
            impact_level=a.impact_level,
            categories=a.categories,
            sentiment_score=a.sentiment_score,
            sentiment_label=a.sentiment_label,
            sentiment_confidence=a.sentiment_confidence,
            sentiment_details=a.sentiment_details,
            embedding=a.embedding,
        )
        for a in articles
    ]


@router.get("/{article_id}", response_model=NewsArticleResponse)
async def get_news_article(
    article_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific news article by ID"""

    result = await db.execute(
        select(NewsArticle).where(NewsArticle.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="News article not found")

    return NewsArticleResponse(
        id=article.id,
        title=article.title,
        content=article.content,
        summary=article.summary,
        url=str(article.url),
        source=article.source,
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        related_pairs=article.related_pairs,
        impact_level=article.impact_level,
        categories=article.categories,
        sentiment_score=article.sentiment_score,
        sentiment_label=article.sentiment_label,
        sentiment_confidence=article.sentiment_confidence,
        sentiment_details=article.sentiment_details,
        embedding=article.embedding,
    )


@router.get("/stats/summary")
async def get_news_stats(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get news statistics for the last N hours"""

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Total count
    total_result = await db.execute(
        select(func.count(NewsArticle.id))
        .where(NewsArticle.published_at >= cutoff)
    )
    total = total_result.scalar() or 0

    # By source
    source_result = await db.execute(
        select(NewsArticle.source, func.count(NewsArticle.id))
        .where(NewsArticle.published_at >= cutoff)
        .group_by(NewsArticle.source)
    )
    by_source = {str(row[0]): row[1] for row in source_result.fetchall()}

    # By impact
    impact_result = await db.execute(
        select(NewsArticle.impact_level, func.count(NewsArticle.id))
        .where(NewsArticle.published_at >= cutoff)
        .group_by(NewsArticle.impact_level)
    )
    by_impact = {str(row[0]): row[1] for row in impact_result.fetchall()}

    # By sentiment
    sentiment_result = await db.execute(
        select(NewsArticle.sentiment_label, func.count(NewsArticle.id))
        .where(
            and_(
                NewsArticle.published_at >= cutoff,
                NewsArticle.sentiment_label.isnot(None)
            )
        )
        .group_by(NewsArticle.sentiment_label)
    )
    by_sentiment = {str(row[0]): row[1] for row in sentiment_result.fetchall()}

    # Top pairs mentioned
    pair_result = await db.execute(
        select(NewsArticle.related_pairs)
        .where(NewsArticle.published_at >= cutoff)
    )
    all_pairs = []
    for row in pair_result.fetchall():
        all_pairs.extend(row[0] or [])

    from collections import Counter
    pair_counts = dict(Counter(all_pairs).most_common(10))

    return {
        "period_hours": hours,
        "total_articles": total,
        "by_source": by_source,
        "by_impact": by_impact,
        "by_sentiment": by_sentiment,
        "top_pairs": pair_counts,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/analyze-sentiment")
async def analyze_sentiment(
    text: str,
    pair: Optional[str] = None
):
    """Analyze sentiment of arbitrary text"""
    from app.main import sentiment_analyzer

    if not sentiment_analyzer:
        raise HTTPException(status_code=503, detail="Sentiment analyzer not available")

    result = await sentiment_analyzer.analyze(text, [pair] if pair else [])
    return result