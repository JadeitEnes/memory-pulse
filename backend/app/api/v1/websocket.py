from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger

router = APIRouter(tags=["WebSocket"])
logger = get_logger(__name__)


class ConnectionManager:
  
    def __init__(self) -> None:
        self._active_connections: list[WebSocket] = []

    @property
    def has_connections(self) -> bool:
        return len(self._active_connections) > 0

    @property
    def connection_count(self) -> int:
        return len(self._active_connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active_connections.append(websocket)
        logger.info("websocket_connected", total_connections=self.connection_count)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)
        logger.info("websocket_disconnected", total_connections=self.connection_count)

    async def broadcast(self, message: dict) -> None:      
        dead_connections = []
        for connection in self._active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


manager = ConnectionManager()


@router.websocket("/ws/prices")
async def websocket_price_stream(websocket: WebSocket): 
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)