from loguru import logger
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter
from app.core.config import settings

def init_tts_service(voice_id: str) -> CartesiaTTSService:
    """Initialize the text-to-speech service using Cartesia."""
    logger.debug("Initializing Cartesia TTS")
    
    # Create markdown text filter
    text_filter = MarkdownTextFilter(
        params=MarkdownTextFilter.InputParams(
            enable_text_filter=True,
            filter_code=True,
            filter_tables=True
        )
    )
    
    return CartesiaTTSService(
        api_key=settings.CARTESIA_API_KEY,
        voice_id=voice_id,
        text_filter=text_filter
    )