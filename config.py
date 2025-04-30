import logging
from logger_config import setup_logging
from livekit.agents import llm, metrics
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import (
    cartesia,
    openai,
    deepgram,
    noise_cancellation,
    turn_detector,
)

# Use the centralized logger configuration
logger = logging.getLogger("voice-agent")

def create_voice_agent(ctx, system_prompt, voice_id = None):
    """Create and configure the VoicePipelineAgent."""
    
    logger.info("Creating voice agent pipeline")
    
    # Create the chat context with the system prompt
    logger.debug("Initializing chat context with system prompt")
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=system_prompt,
    )

    # Create the agent with all plugins
    logger.info("Configuring voice pipeline agent with plugins")
    try:
        logger.debug("Setting up deepgram STT")
        stt = deepgram.STT()
        
        logger.debug("Setting up OpenAI LLM with gpt-4o-mini model")
        llm_engine = openai.LLM(model="gpt-4o-mini")
        
        logger.debug("Setting up Cartesia TTS")
        if voice_id:
            tts = cartesia.TTS(voice=voice_id)
        else:
            tts = cartesia.TTS()
        
        logger.debug("Setting up turn detector and noise cancellation")
        # For compatibility with _TurnDetector, use directly from turn_detector without our own variable
        noise_canceler = noise_cancellation.BVC()
        
        logger.info("Creating VoicePipelineAgent with all components")
        agent = VoicePipelineAgent(
            vad=ctx.proc.userdata["vad"],
            stt=stt,
            llm=llm_engine,
            tts=tts,
            # use LiveKit's transformer-based turn detector
            turn_detector=turn_detector.EOUModel(),  # Create directly inline
            # minimum delay for endpointing, used when turn detector believes the user is done with their turn
            min_endpointing_delay=0.5,
            # maximum delay for endpointing, used when turn detector does not believe the user is done with their turn
            max_endpointing_delay=5.0,
            # enable background voice & noise cancellation, powered by Krisp
            # included at no additional cost with LiveKit Cloud
            noise_cancellation=noise_canceler,
            chat_ctx=initial_ctx,
        )
        logger.info("Voice pipeline agent created successfully")
    except Exception as e:
        logger.error(f"Failed to create voice pipeline agent: {str(e)}", exc_info=True)
        raise

    # Set up metrics collection
    logger.debug("Setting up metrics collection")
    usage_collector = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
        logger.debug(f"Metrics collected: {type(agent_metrics).__name__}")
        metrics.log_metrics(agent_metrics)
        usage_collector.collect(agent_metrics)
        
    return agent, usage_collector 