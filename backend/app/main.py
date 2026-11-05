from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
from datetime import datetime

from app.config import settings
from app.db.session import init_db, close_db
from app.api.v1 import news, forex, predictions, sentiment, websocket
from app.services.news_ingestion import NewsIngestionService
from app.services.forex_data import ForexDataService
from app.services.prediction_engine import PredictionEngine
from app.ml.models.sentiment_analyzer import SentimentAnalyzer
from app.ml.models.market_predictor import MarketPredictor
from app.ws.manager import ConnectionManager
from app.core.state import (
    news_service, forex_service, prediction_engine,
    sentiment_analyzer, market_predictor, manager
)

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Use global from state module
    from app.core import state as app_state

    logger.info("Starting ForexNews AI...")

    # Initialize database
    await init_db()

    # Initialize ML models
    app_state.sentiment_analyzer = SentimentAnalyzer()
    await app_state.sentiment_analyzer.load_model()

    app_state.market_predictor = MarketPredictor()
    await app_state.market_predictor.load_models()

    # Initialize services
    app_state.news_service = NewsIngestionService(app_state.sentiment_analyzer)
    app_state.forex_service = ForexDataService()
    app_state.prediction_engine = PredictionEngine(
        sentiment_analyzer=app_state.sentiment_analyzer,
        market_predictor=app_state.market_predictor,
        forex_service=app_state.forex_service,
        news_service=app_state.news_service
    )

    # Initialize WebSocket manager
    app_state.manager = ConnectionManager()

    # Start background tasks
    asyncio.create_task(app_state.news_service.start_ingestion_loop())
    asyncio.create_task(app_state.forex_service.start_price_stream())
    asyncio.create_task(app_state.prediction_engine.start_prediction_loop())
    asyncio.create_task(websocket_heartbeat())

    logger.info("ForexNews AI started successfully")

    yield

    logger.info("Shutting down ForexNews AI...")
    await app_state.news_service.stop()
    await app_state.forex_service.stop()
    await app_state.prediction_engine.stop()
    await close_db()
    logger.info("ForexNews AI shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-time Forex Market Reaction Prediction & Analysis System",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(news.router, prefix=settings.API_V1_PREFIX, tags=["news"])
app.include_router(forex.router, prefix=settings.API_V1_PREFIX, tags=["forex"])
app.include_router(predictions.router, prefix=settings.API_V1_PREFIX, tags=["predictions"])
app.include_router(sentiment.router, prefix=settings.API_V1_PREFIX, tags=["sentiment"])
app.include_router(websocket.router, prefix=settings.API_V1_PREFIX, tags=["websocket"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "redis": "connected",
            "ml_models": "loaded",
            "news_ingestion": "running",
            "forex_stream": "running",
            "prediction_engine": "running"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, client_id)


async def handle_websocket_message(websocket: WebSocket, data: dict):
    msg_type = data.get("type")

    if msg_type == "subscribe":
        topics = data.get("topics", [])
        manager.subscribe(websocket, topics)
        await manager.send_personal(websocket, {"type": "subscribed", "topics": topics})

    elif msg_type == "unsubscribe":
        topics = data.get("topics", [])
        manager.unsubscribe(websocket, topics)
        await manager.send_personal(websocket, {"type": "unsubscribed", "topics": topics})

    elif msg_type == "get_latest":
        topic = data.get("topic")
        if topic == "predictions":
            predictions = await prediction_engine.get_latest_predictions()
            await manager.send_personal(websocket, {"type": "predictions", "data": predictions})
        elif topic == "news":
            news = await news_service.get_latest_news(limit=50)
            await manager.send_personal(websocket, {"type": "news", "data": news})
        elif topic == "prices":
            prices = await forex_service.get_current_prices()
            await manager.send_personal(websocket, {"type": "prices", "data": prices})
        elif topic == "sentiment":
            sentiment = await sentiment_analyzer.get_latest_sentiment()
            await manager.send_personal(websocket, {"type": "sentiment", "data": sentiment})

    elif msg_type == "ping":
        await manager.send_personal(websocket, {"type": "pong", "timestamp": datetime.utcnow().isoformat()})


async def websocket_heartbeat():
    while True:
        await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
        await manager.broadcast("heartbeat", {
            "type": "heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
            "connections": sum(len(c) for c in manager.active_connections.values())
        })


# Export manager for use in other modules
def get_connection_manager() -> ConnectionManager:
    return manager


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )# redeploy trigger
