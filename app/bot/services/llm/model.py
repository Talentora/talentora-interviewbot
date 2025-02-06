from loguru import logger
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from app.core.config import settings

def init_groq_processor() -> BaseChatModel:
    """Initialize the Groq processor for handling the interview conversation."""
    logger.debug("Initializing Groq processor")
    model = "llama-3.3-70b-versatile"
    model = ChatGroq(
        model_name=model,
        temperature=0.7,
        max_tokens=1000,
        groq_api_key=settings.GROQ_API_KEY,
        timeout=25
    )
    logger.debug("Groq processor initialized")
    return model 