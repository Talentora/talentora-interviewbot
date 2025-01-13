from typing import Dict, Any
import asyncio
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator,
)
from app.core.config import settings
from app.core.logger import logger

class InterviewBot:
    def __init__(self, config: Dict[str, Any]):
        logger.info("Initializing Interview Bot")
        logger.debug(f"Bot configuration: {config}")
        self.config = config
        self.voice_id = config["voice_id"]
        self.interview_config = config["interview_config"]
        
    async def start(self, room_url: str, token: str):
        logger.info(f"Starting interview session in room: {room_url}")
        try:
            # Setup Daily transport
            logger.debug("Initializing Daily transport")
            transport = DailyTransport(
                room_url=room_url,
                token=token,
                bot_name=self.interview_config["bot_name"],
                params=DailyParams(
                    audio_out_enabled=True,
                    transcription_enabled=True,
                    vad_enabled=True,
                    vad_analyzer=SileroVADAnalyzer(
                        sample_rate=16000,
                        params=VADParams(
                            threshold=0.5,
                            min_speech_duration_ms=250,
                            min_silence_duration_ms=100
                        )
                    ),
                    vad_audio_passthrough=True
                )
            )

            logger.debug("Initializing Cartesia TTS")
            tts = CartesiaTTSService(
                api_key=settings.CARTESIA_API_KEY,
                voice_id=self.voice_id,
            )

            logger.info("Setting up interview pipeline")
            pipeline = self._setup_pipeline(transport, tts)
            
            logger.debug("Starting pipeline runner")
            runner = PipelineRunner()
            task = PipelineTask(pipeline, PipelineParams(
                allow_interruptions=True,
                max_duration=self.config.get("max_duration", 300)
            ))
            await runner.run(task)
            
        except Exception as e:
            logger.error(f"Error during interview session: {str(e)}")
            raise

    def _setup_pipeline(self, transport: DailyTransport, tts: CartesiaTTSService) -> Pipeline:
        """
        Set up the interview pipeline with all necessary components
        """
        # Setup response aggregators
        user_response_aggregator = LLMUserResponseAggregator()
        assistant_response_aggregator = LLMAssistantResponseAggregator()

        # Create the pipeline
        pipeline = Pipeline([
            transport.input(),
            user_response_aggregator,
            # Add LLM processor here
            tts,
            transport.output(),
            assistant_response_aggregator,
        ])

        return pipeline 