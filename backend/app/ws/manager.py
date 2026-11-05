# WebSocket connection manager
from typing import Dict, List, Set
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"Client {client_id} connected. Total connections: {sum(len(c) for c in self.active_connections.values())}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"Client {client_id} disconnected")

    def subscribe(self, websocket: WebSocket, topics: List[str]):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(topics)

    def unsubscribe(self, websocket: WebSocket, topics: List[str]):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].difference_update(topics)

    async def broadcast(self, topic: str, message: dict):
        disconnected = []
        for ws, topics in self.subscriptions.items():
            if topic in topics or "all" in topics:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(ws)

        for ws in disconnected:
            for client_id, conns in self.active_connections.items():
                if ws in conns:
                    self.disconnect(ws, client_id)
                    break

    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            for client_id, conns in self.active_connections.items():
                if ws in conns:
                    self.disconnect(websocket, client_id)
                    break