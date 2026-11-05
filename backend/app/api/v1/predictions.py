from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.config import settings
from app.db.session import get_db
from app.db.models import Prediction, PredictionDirection
from app.schemas import (
    PredictionResponse, PredictionList, PredictionFilter,
    PredictionDirection as PredDirEnum
)
from app.core.state import prediction_engine

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", response_model=PredictionList)
async def get_predictions(
    pair: Optional[List[str]] = Query(None),
    horizon_minutes: Optional[List[int]] = Query(None),
    direction: Optional[List[PredDirEnum]] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    max_confidence: Optional[float] = Query(None, ge=0, le=1),
    outcome: Optional[List[str]] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("predicted_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db)
):
    """Get predictions with filtering and pagination"""

    query = select(Prediction)

    if pair:
        query = query.where(Prediction.pair.in_(pair))

    if horizon_minutes:
        query = query.where(Prediction.horizon_minutes.in_(horizon_minutes))

    if direction:
        query = query.where(Prediction.direction.in_(direction))

    if min_confidence is not None:
        query = query.where(Prediction.confidence >= min_confidence)

    if max_confidence is not None:
        query = query.where(Prediction.confidence <= max_confidence)

    if outcome:
        query = query.where(Prediction.outcome.in_(outcome))

    if start_date:
        query = query.where(Prediction.predicted_at >= start_date)

    if end_date:
        query = query.where(Prediction.predicted_at <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(Prediction, sort_by, Prediction.predicted_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    result = await db.execute(query)
    predictions = result.scalars().all()

    items = [
        PredictionResponse(
            id=p.id,
            news_id=p.news_id,
            pair=p.pair,
            horizon_minutes=p.horizon_minutes,
            direction=p.direction,
            confidence=p.confidence,
            expected_move_pips=p.expected_move_pips,
            expected_move_percent=p.expected_move_percent,
            entry_price=p.entry_price,
            target_price=p.target_price,
            stop_loss=p.stop_loss,
            risk_reward_ratio=p.risk_reward_ratio,
            model_version=p.model_version,
            features_used=p.features_used,
            feature_importance=p.feature_importance,
            predicted_at=p.predicted_at,
            expires_at=p.expires_at,
            resolved_at=p.resolved_at,
            actual_direction=p.actual_direction,
            actual_move_pips=p.actual_move_pips,
            actual_move_percent=p.actual_move_percent,
            outcome=p.outcome,
            profit_loss_pips=p.profit_loss_pips,
        )
        for p in predictions
    ]

    return PredictionList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + page_size < total
    )


@router.get("/active", response_model=List[PredictionResponse])
async def get_active_predictions(
    limit: int = Query(50, ge=1, le=200),
    pair: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get currently active (unresolved) predictions"""

    query = select(Prediction).where(
        and_(
            Prediction.resolved_at.is_(None),
            Prediction.expires_at > datetime.utcnow()
        )
    ).order_by(desc(Prediction.predicted_at)).limit(limit)

    if pair:
        query = query.where(Prediction.pair == pair.upper())

    result = await db.execute(query)
    predictions = result.scalars().all()

    return [
        PredictionResponse(
            id=p.id,
            news_id=p.news_id,
            pair=p.pair,
            horizon_minutes=p.horizon_minutes,
            direction=p.direction,
            confidence=p.confidence,
            expected_move_pips=p.expected_move_pips,
            expected_move_percent=p.expected_move_percent,
            entry_price=p.entry_price,
            target_price=p.target_price,
            stop_loss=p.stop_loss,
            risk_reward_ratio=p.risk_reward_ratio,
            model_version=p.model_version,
            features_used=p.features_used,
            feature_importance=p.feature_importance,
            predicted_at=p.predicted_at,
            expires_at=p.expires_at,
            resolved_at=p.resolved_at,
            actual_direction=p.actual_direction,
            actual_move_pips=p.actual_move_pips,
            actual_move_percent=p.actual_move_percent,
            outcome=p.outcome,
            profit_loss_pips=p.profit_loss_pips,
        )
        for p in predictions
    ]


@router.get("/latest", response_model=List[PredictionResponse])
async def get_latest_predictions(
    limit: int = Query(50, ge=1, le=200)
):
    """Get latest predictions from prediction engine"""

    if not prediction_engine:
        raise HTTPException(status_code=503, detail="Prediction engine not available")

    predictions = await prediction_engine.get_latest_predictions(limit)
    return predictions


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific prediction by ID"""

    result = await db.execute(
        select(Prediction).where(Prediction.id == prediction_id)
    )
    prediction = result.scalar_one_or_none()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    return PredictionResponse(
        id=prediction.id,
        news_id=prediction.news_id,
        pair=prediction.pair,
        horizon_minutes=prediction.horizon_minutes,
        direction=prediction.direction,
        confidence=prediction.confidence,
        expected_move_pips=prediction.expected_move_pips,
        expected_move_percent=prediction.expected_move_percent,
        entry_price=prediction.entry_price,
        target_price=prediction.target_price,
        stop_loss=prediction.stop_loss,
        risk_reward_ratio=prediction.risk_reward_ratio,
        model_version=prediction.model_version,
        features_used=prediction.features_used,
        feature_importance=prediction.feature_importance,
        predicted_at=prediction.predicted_at,
        expires_at=prediction.expires_at,
        resolved_at=prediction.resolved_at,
        actual_direction=prediction.actual_direction,
        actual_move_pips=prediction.actual_move_pips,
        actual_move_percent=prediction.actual_move_percent,
        outcome=prediction.outcome,
        profit_loss_pips=prediction.profit_loss_pips,
    )


@router.get("/stats/performance")
async def get_prediction_performance(
    hours: int = Query(24, ge=1, le=720),
    pair: Optional[str] = Query(None),
    horizon_minutes: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get prediction performance statistics"""

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    query = select(Prediction).where(
        and_(
            Prediction.predicted_at >= cutoff,
            Prediction.resolved_at.isnot(None)
        )
    )

    if pair:
        query = query.where(Prediction.pair == pair.upper())

    if horizon_minutes:
        query = query.where(Prediction.horizon_minutes == horizon_minutes)

    # Overall stats
    result = await db.execute(
        select(
            func.count(Prediction.id),
            func.avg(Prediction.confidence),
            func.sum(func.case((Prediction.outcome == 'correct', 1), else_=0)),
            func.sum(func.case((Prediction.outcome == 'incorrect', 1), else_=0)),
            func.sum(func.case((Prediction.outcome == 'partial', 1), else_=0)),
            func.avg(Prediction.profit_loss_pips),
            func.sum(Prediction.profit_loss_pips),
        )
        .select_from(query.subquery())
    )
    total, avg_conf, correct, incorrect, partial, avg_pips, total_pips = result.one()

    # By direction
    dir_result = await db.execute(
        select(
            Prediction.direction,
            func.count(Prediction.id),
            func.sum(func.case((Prediction.outcome == 'correct', 1), else_=0)),
            func.avg(Prediction.profit_loss_pips),
        )
        .select_from(query.subquery())
        .group_by(Prediction.direction)
    )
    by_direction = {
        str(row[0]): {
            'count': row[1],
            'correct': row[2],
            'accuracy': row[2] / row[1] if row[1] > 0 else 0,
            'avg_pips': float(row[3]) if row[3] else 0
        }
        for row in dir_result.fetchall()
    }

    # By horizon
    horizon_result = await db.execute(
        select(
            Prediction.horizon_minutes,
            func.count(Prediction.id),
            func.sum(func.case((Prediction.outcome == 'correct', 1), else_=0)),
            func.avg(Prediction.profit_loss_pips),
        )
        .select_from(query.subquery())
        .group_by(Prediction.horizon_minutes)
    )
    by_horizon = {
        row[0]: {
            'count': row[1],
            'correct': row[2],
            'accuracy': row[2] / row[1] if row[1] > 0 else 0,
            'avg_pips': float(row[3]) if row[3] else 0
        }
        for row in horizon_result.fetchall()
    }

    accuracy = correct / (correct + incorrect) if (correct + incorrect) > 0 else None

    return {
        "period_hours": hours,
        "total_predictions": total or 0,
        "correct": correct or 0,
        "incorrect": incorrect or 0,
        "partial": partial or 0,
        "accuracy": float(accuracy) if accuracy else None,
        "avg_confidence": float(avg_conf) if avg_conf else 0,
        "avg_pips_per_trade": float(avg_pips) if avg_pips else 0,
        "total_pips": float(total_pips) if total_pips else 0,
        "by_direction": by_direction,
        "by_horizon": by_horizon,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats/model-performance")
async def get_model_performance(
    db: AsyncSession = Depends(get_db)
):
    """Get model performance metrics"""

    from app.db.models import ModelPerformance

    result = await db.execute(
        select(ModelPerformance)
        .order_by(desc(ModelPerformance.calculated_at))
        .limit(50)
    )
    performances = result.scalars().all()

    return [
        {
            "model_name": p.model_name,
            "model_version": p.model_version,
            "pair": p.pair,
            "horizon_minutes": p.horizon_minutes,
            "total_predictions": p.total_predictions,
            "correct_predictions": p.correct_predictions,
            "accuracy": p.accuracy,
            "precision": p.precision,
            "recall": p.recall,
            "f1_score": p.f1_score,
            "total_pips": p.total_pips,
            "avg_pips_per_trade": p.avg_pips_per_trade,
            "win_rate": p.win_rate,
            "profit_factor": p.profit_factor,
            "max_drawdown": p.max_drawdown,
            "sharpe_ratio": p.sharpe_ratio,
            "period_start": p.period_start.isoformat() if p.period_start else None,
            "period_end": p.period_end.isoformat() if p.period_end else None,
        }
        for p in performances
    ]