from fastapi import APIRouter

from app.api.v1.endpoints import health, prices

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(health.router)
api_v1_router.include_router(prices.router)