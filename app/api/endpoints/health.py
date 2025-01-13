from fastapi import APIRouter
from app.core.logger import logger

router = APIRouter()

@router.get("/")
async def health_check():
    """Hello World endpoint"""
    logger.info("Hello World endpoint called")
    return {"message": "Hello World"} 