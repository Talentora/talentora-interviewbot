from deepgram import LiveOptions
from pipecat.services.deepgram import DeepgramSTTService
from app.core.config import settings

def init_speech_to_text() -> DeepgramSTTService:
    """Initialize the speech-to-text service using Deepgram."""
    return DeepgramSTTService(
        api_key=settings.DEEPGRAM_API_KEY,
        live_options=LiveOptions(
            model="nova-2-general",
            language="en-US",
            smart_format=True,
            interim_results=True,
            punctuate=True
        )
    ) 