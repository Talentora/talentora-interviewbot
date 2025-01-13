from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting Interview Bot API")
        settings.validate_required_settings()
        logger.info(f"DAILY_API_KEY: {settings.DAILY_API_KEY}")
        logger.info("Configuration validated successfully")
        yield
        logger.info("Shutting down Interview Bot API")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

def create_app() -> FastAPI:
    app = FastAPI(
        title="Interview Bot API",
        description="API for managing interview bot sessions",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(api_router, prefix="/api")
    
    return app

app = create_app()  