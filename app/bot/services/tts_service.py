from loguru import logger
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.aws import PollyTTSService, Language
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter
from pipecat.services.openai import OpenAITTSService
from app.core.config import settings
from typing import Union, Literal

# Define the allowed voice providers
VoiceProvider = Literal["aws_polly", "cartesia", "openai_tts"]

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

def init_openai_tts(voice_id: str = "ash") -> OpenAITTSService:
    """Initialize the text-to-speech service using OpenAI."""
    logger.debug("Initializing OpenAI TTS")
    
    tts = OpenAITTSService(
        api_key=settings.OPENAI_API_KEY,
        model="tts-1",
        voice_id=voice_id
    )
    logger.debug("OpenAI TTS initialized")
    return tts

def init_tts_service(
    voice_id: str,
    provider: VoiceProvider = "openai_tts"
) -> Union[CartesiaTTSService, PollyTTSService, OpenAITTSService]:
    """Initialize the text-to-speech service based on the specified provider.
    
    Args:
        voice_id: The voice ID to use for the selected provider
        provider: The TTS provider to use (defaults to OpenAI)
    """
    logger.debug(f"Initializing TTS service with provider: {provider}")
    
    if provider == "cartesia":
        return init_cartesia_tts(voice_id)
    elif provider == "aws_polly":
        return init_polly_tts(voice_id)
    else:  # openai_tts is the default
        return init_openai_tts(voice_id)