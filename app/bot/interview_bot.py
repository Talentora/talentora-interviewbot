from typing import Dict, Any
from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator,
)

from app.bot.services.audio import init_daily_transport
from app.bot.services.tts_service import init_tts_service
from app.bot.services.stt_service import init_speech_to_text
from app.bot.services.language_model import init_langchain_processor
from app.bot.services.idle_service import init_idle_processor
from app.bot.handlers.event_handlers import (
    on_joined,
    on_participant_joined,
    on_participant_left,
    on_error,
    on_transcription_message
)

class InterviewBot:
    """A bot that conducts automated interviews using voice interactions."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Interview Bot with the given configuration."""
        logger.info("Initializing Interview Bot")
        logger.debug(f"Bot configuration: {config}")
        self.config = config
        self.voice_id = config["voice_id"]
        self.interview_config = config["interview_config"]
        self.transport = None

    def _setup_pipeline(self, transport) -> Pipeline:
        """Set up the complete interview processing pipeline."""
        try:
            # Initialize processors
            stt = init_speech_to_text()
            langchain_processor = init_langchain_processor()
            tts = init_tts_service(self.voice_id)
            idle = init_idle_processor()
            
            # Initialize aggregators
            user_response_aggregator = LLMUserResponseAggregator()
            assistant_response_aggregator = LLMAssistantResponseAggregator()



            # Create pipeline with user idle monitoring
            pipeline = Pipeline([
                transport.input(),
                stt,
                idle,  # Add idle monitoring after speech recognition
                user_response_aggregator,
                langchain_processor,
                tts,
                transport.output(),
                assistant_response_aggregator,
            ])

            logger.debug("Pipeline setup complete")
            return pipeline

        except Exception as e:
            logger.error(f"Error setting up pipeline: {str(e)}")
            raise

    async def _run_pipeline(self, pipeline: Pipeline):
        """Execute the interview pipeline."""
        logger.debug("Starting pipeline runner")
        runner = PipelineRunner()
        task = PipelineTask(pipeline, PipelineParams(
            allow_interruptions=True,
            max_duration=self.config.get("max_duration", 300)
        ))
        await runner.run(task)

    async def _cleanup_pipeline(self, pipeline: Pipeline):
        """Cleanup and shutdown the pipeline gracefully."""
        logger.debug("Cleaning up pipeline")
        try:
            if hasattr(pipeline, 'cancel'):
                await pipeline.cancel()
            
            if hasattr(pipeline, '_processors'):
                for processor in pipeline._processors:
                    if hasattr(processor, 'cleanup'):
                        await processor.cleanup()
                    
            logger.debug("Pipeline cleanup completed")
        except Exception as e:
            logger.error(f"Error during pipeline cleanup: {str(e)}")

    def _register_event_handlers(self, transport):
        """Register event handlers for the transport."""
        transport.event_handler("on_joined")(on_joined)
        transport.event_handler("on_participant_joined")(on_participant_joined)
        transport.event_handler("on_participant_left")(on_participant_left)
        transport.event_handler("on_error")(on_error)
        transport.event_handler("on_transcription_message")(on_transcription_message)

    async def start(self, room_url: str, token: str):
        """Start an interview session."""
        pipeline = None
        try:
            logger.info(f"Starting interview session in room: {room_url}")
            
            # Initialize transport
            self.transport = init_daily_transport(
                room_url, 
                token, 
                self.interview_config["bot_name"]
            )
            
            # Register event handlers
            self._register_event_handlers(self.transport)
            
            logger.debug("Daily transport is now active")

            pipeline = self._setup_pipeline(self.transport)
            await self._run_pipeline(pipeline)
            
        except Exception as e:
            logger.error(f"Error during interview session: {str(e)}")
            raise
        finally:
            if pipeline:
                await self._cleanup_pipeline(pipeline)