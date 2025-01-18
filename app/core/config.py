from pydantic_settings import BaseSettings
from typing import Optional
from app.core.logger import logger

class Settings(BaseSettings):
    # Required API Keys
    DAILY_API_KEY: str = None
    CARTESIA_API_KEY: str = None
    ANTHROPIC_API_KEY: str = None
    DEEPGRAM_API_KEY: str = None
    
    # Optional Daily.co Settings
    DAILY_SAMPLE_ROOM_URL: Optional[str] = None
    DAILY_API_URL: Optional[str] = None
    
    # Optional OpenAI Settings
    OPENAI_API_KEY: Optional[str] = None
    
    # AWS Settings
    AWS_ACCESS_KEY_ID: str = None
    AWS_SECRET_KEY: str = None
    AWS_REGION: str = "us-east-1"
    
    # LangChain Settings
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: Optional[str] = None
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: Optional[str] = "interview-bot"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

    def validate_required_settings(self) -> None:
        logger.debug("Validating required settings")
        missing_keys = []
        if not self.DAILY_API_URL:
            missing_keys.append("DAILY_API_URL")
        if not self.CARTESIA_API_KEY:
            missing_keys.append("CARTESIA_API_KEY")
        if not self.ANTHROPIC_API_KEY:
            missing_keys.append("ANTHROPIC_API_KEY")
        if not self.DEEPGRAM_API_KEY:
            missing_keys.append("DEEPGRAM_API_KEY")
        if not self.AWS_ACCESS_KEY_ID:
            missing_keys.append("AWS_ACCESS_KEY_ID")
        if not self.AWS_SECRET_KEY:
            missing_keys.append("AWS_SECRET_KEY")
            
        if missing_keys:
            logger.error(f"Missing required environment variables: {', '.join(missing_keys)}")
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_keys)}"
            )
        logger.info("All required settings validated successfully")


# Initialize settings with validation
settings = Settings()
settings.validate_required_settings()
