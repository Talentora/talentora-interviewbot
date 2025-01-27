from loguru import logger
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.aws import PollyTTSService, Language
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter
from app.core.config import settings
from typing import Union


def init_cartesia_tts(voice_id: str) -> CartesiaTTSService:
    """Initialize the text-to-speech service using Cartesia."""
    logger.debug("Initializing Cartesia TTS")
    
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

def init_polly_tts(voice_id: str = "Joanna") -> PollyTTSService:
    """Initialize the text-to-speech service using AWS Polly."""
    logger.debug("Initializing AWS Polly TTS")
    
    return PollyTTSService(
        api_key=settings.AWS_SECRET_KEY,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        region="us-east-1",
        voice_id=voice_id,
        params=PollyTTSService.InputParams(
            engine="generative",
            language=Language.EN,
            rate="medium",
        )
    )

def init_tts_service(voice_id: str) -> Union[CartesiaTTSService, PollyTTSService]:
    """Initialize the default text-to-speech service (Polly by default)."""
    # return init_polly_tts()
    return init_cartesia_tts(voice_id)