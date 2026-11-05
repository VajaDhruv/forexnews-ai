from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import structlog

from app.core.state import manager, prediction_engine, news_service, forex_service, sentiment_analyzer
from app.schemas import WSMessage, WSSubscribeMessage, WSUnsubscribeMessage, WSGetLatestMessage

router = APIRouter()
logger = structlog.get_logger()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time updates"""

    # Generate client ID if not provided
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())[:8]

    await manager.connect(websocket, client_id)

    try:
        # Send welcome message
        await manager.send_personal(websocket, {
            "type": "connected",
            "client_id": client_id,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "available_topics": [
                "predictions", "news", "prices", "sentiment",
                "heartbeat", "all"
            ]
        })

        while True:
            data = await websocket.receive_json()
            await handle_message(websocket, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, client_id)


async def handle_message(websocket: WebSocket, data: dict):
    """Handle incoming WebSocket messages"""
    msg_type = data.get("type")

    if msg_type == "subscribe":
        topics = data.get("topics", [])
        manager.subscribe(websocket, topics)
        await manager.send_personal(websocket, {
            "type": "subscribed",
            "topics": topics,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        })

    elif msg_type == "unsubscribe":
        topics = data.get("topics", [])
        manager.unsubscribe(websocket, topics)
        await manager.send_personal(websocket, {
            "type": "unsubscribed",
            "topics": topics,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        })

    elif msg_type == "get_latest":
        topic = data.get("topic")
        await send_latest_data(websocket, topic)

    elif msg_type == "ping":
        await manager.send_personal(websocket, {
            "type": "pong",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        })

    else:
        await manager.send_personal(websocket, {
            "type": "error",
            "message": f"Unknown message type: {msg_type}",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        })


async def send_latest_data(websocket: WebSocket, topic: str):
    """Send latest data for a topic"""
    try:
        if topic == "predictions" and prediction_engine:
            predictions = await prediction_engine.get_latest_predictions(limit=20)
            await manager.send_personal(websocket, {
                "type": "predictions",
                "data": predictions,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            })

        elif topic == "news" and news_service:
            news = await news_service.get_latest_news(limit=20)
            await manager.send_personal(websocket, {
                "type": "news",
                "data": news,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            })

        elif topic == "prices" and forex_service:
            prices = await forex_service.get_current_prices()
            await manager.send_personal(websocket, {
                "type": "prices",
                "data": prices,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            })

        elif topic == "sentiment" and sentiment_analyzer:
            sentiment = await sentiment_analyzer.get_latest_sentiment()
            await manager.send_personal(websocket, {
                "type": "sentiment",
                "data": sentiment,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            })

        else:
            await manager.send_personal(websocket, {
                "type": "error",
                "message": f"Topic not available: {topic}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            })

    except Exception as e:
        logger.error(f"Failed to send latest data for {topic}: {e}")
        await manager.send_personal(websocket, {
            "type": "error",
            "message": f"Failed to fetch {topic}",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        })


# Functions to broadcast updates (called from services)
async def broadcast_new_prediction(prediction: dict):
    """Broadcast new prediction to subscribed clients"""
    await manager.broadcast("predictions", {
        "type": "new_prediction",
        "data": prediction,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    })


async def broadcast_new_news(news: dict):
    """Broadcast new news to subscribed clients"""
    await manager.broadcast("news", {
        "type": "new_news",
        "data": news,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    })


async def broadcast_price_update(pair: str, price: dict):
    """Broadcast price update to subscribed clients"""
    await manager.broadcast("prices", {
        "type": "price_update",
        "pair": pair,
        "data": price,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    })


async def broadcast_sentiment_update(pair: str, sentiment: dict):
    """Broadcast sentiment update to subscribed clients"""
    await manager.broadcast("sentiment", {
        "type": "sentiment_update",
        "pair": pair,
        "data": sentiment,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    })


async def broadcast_prediction_resolved(prediction: dict):
    """Broadcast resolved prediction to subscribed clients"""
    await manager.broadcast("predictions", {
        "type": "prediction_resolved",
        "data": prediction,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    })