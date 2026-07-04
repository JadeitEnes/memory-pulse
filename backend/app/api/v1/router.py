from app.api.v1.endpoints import forecasts, health, prices, websocket
from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(health.router)
api_v1_router.include_router(prices.router)
api_v1_router.include_router(forecasts.router)
api_v1_router.include_router(websocket.router)
