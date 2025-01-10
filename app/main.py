from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.core.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting Interview Bot API")
        settings.validate_required_settings()
        logger.info("Configuration validated successfully")
        yield
        logger.info("Shutting down Interview Bot API")
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during startup: {str(e)}")
        raise

app = FastAPI(title="Interview Bot API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api") 