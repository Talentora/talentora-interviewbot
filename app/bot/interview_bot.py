from typing import Dict, Any
from loguru import logger
import uuid
import sounddevice as sd

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
        """Initialize the Interview Bot with the given configuration.
        
        Args:
            config: Dictionary containing:
                - voice_id: Voice ID for text-to-speech
                - max_duration: Maximum duration of interview in seconds
                - interview_config: Dictionary containing:
                    - bot_name: Name of the interviewer
                    - company_name: Name of the company
                    - job_title: Position being interviewed for
                    - job_description: Description of the role
                    - company_context: Information about the company
                    - interview_questions: List of key questions to cover
                    - enable_recording: toogle Daily's recording
                    - demo: indicate if this is a demo interview
        """
        logger.info("Initializing Interview Bot")
        logger.debug(f"Bot configuration: {config}")
        self.config = config
        self.voice_id = config["voice_id"]
        self.interview_config = config["interview_config"]
        self.transport = None
        self.audio_device = None
        self._init_audio_device()
 
    def _init_audio_device(self):
        """Initialize and validate virtual audio device."""
        try:
            devices = sd.query_devices()
            logger.debug(f"Available audio devices: {devices}")
            
            # Try to find virtual speaker device
            virtual_devices = [
                d for d in devices 
                if any(name in str(d['name']).lower() 
                      for name in ['virtual', 'vb-audio', 'soundflower', 'blackhole'])
            ]
            
            if virtual_devices:
                self.audio_device = virtual_devices[0]['name']
                logger.info(f"Selected virtual audio device: {self.audio_device}")
            else:
                # Fallback to default output device
                default_device = sd.query_devices(kind='output')
                self.audio_device = default_device['name']
                logger.warning(f"No virtual audio device found, using default: {self.audio_device}")
            
            # Test device
            sd.check_output_settings(device=self.audio_device)
            
        except Exception as e:
            logger.error(f"Audio device initialization error: {str(e)}")
            raise RuntimeError(f"Failed to initialize audio device: {str(e)}")

    def _setup_pipeline(self, transport) -> Pipeline:
        """Set up the complete interview processing pipeline."""
        try:
            # Generate a unique session ID for this interview
            session_id = str(uuid.uuid4())
            
            # Initialize processors
            stt = init_speech_to_text()
            llm = init_langchain_processor(self.interview_config, session_id)
            tts = init_tts_service(self.voice_id)
            idle = init_idle_processor()
            
            # Initialize aggregators
            user_response_aggregator = LLMUserResponseAggregator()
            assistant_response_aggregator = LLMAssistantResponseAggregator()

            # Create pipeline
            pipeline = Pipeline([
                transport.input(),
                stt,
                idle,
                user_response_aggregator,
                llm,
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
        # Store reference to bot instance in transport for event handlers
        transport.bot = self
        
        transport.event_handler("on_joined")(on_joined)
        transport.event_handler("on_participant_joined")(on_participant_joined)
        transport.event_handler("on_participant_left")(on_participant_left)
        # transport.event_handler("on_error")(on_error)
        transport.event_handler("on_transcription_message")(on_transcription_message)

    async def start(self, room_url: str, token: str):
        """Start an interview session."""
        pipeline = None
        try:
            if not self.audio_device:
                raise RuntimeError("No audio device available")
            
            logger.info(f"Starting interview with audio device: {self.audio_device}")
            logger.info(f"Starting interview session in room: {room_url}")
            
            # Initialize transport
            self.transport = init_daily_transport(
                room_url, 
                token, 
                self.interview_config["bot_name"]
            )
            
            # Register event handlers BEFORE creating the pipeline
            self._register_event_handlers(self.transport)
            logger.debug("Event handlers registered")
            
            # Create and start pipeline
            pipeline = self._setup_pipeline(self.transport)
            logger.debug("Daily transport is now active")
            await self._run_pipeline(pipeline)
            
        except Exception as e:
            logger.error(f"Error during interview session: {str(e)}")
            raise
        finally:
            if pipeline:
                await self._cleanup_pipeline(pipeline)