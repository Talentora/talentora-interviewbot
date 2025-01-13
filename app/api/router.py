from fastapi import APIRouter
from app.api.endpoints import rooms, health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"]) 