from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.filters.koala_filter import KoalaFilter
from app.core.config import settings



def create_vad_analyzer() -> SileroVADAnalyzer:
    """Create and configure the Voice Activity Detection analyzer."""
    return SileroVADAnalyzer(
        sample_rate=16000,
        params=VADParams(
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=100
        )
    )

def init_daily_transport(room_url: str, token: str, bot_name: str) -> DailyTransport:
    """Initialize and configure the Daily transport layer for audio communication."""
    # koala_filter = KoalaFilter(access_key=settings.KOALA_FILTER_KEY)

    return DailyTransport(
        room_url=room_url,
        token=token,
        bot_name=bot_name,
        params=DailyParams(
            # audio_in_filter=koala_filter,
            audio_out_enabled=True,
            transcription_enabled=True,
            vad_enabled=True,
            vad_analyzer=create_vad_analyzer(),
            vad_audio_passthrough=True
        )
    ) 