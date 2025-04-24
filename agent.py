import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    metrics,
)

from context import extract_context_data, build_system_prompt, create_greeting
from config import create_voice_agent
from logger_config import setup_logging
from recording import setup_recording

load_dotenv(dotenv_path=".env")
                                                                                                                                    
# Set up enhanced logging
logger = setup_logging()
logger.info("Voice agent application starting")


def prewarm(proc: JobProcess):
    logger.info("Prewarming model - loading VAD")
    try:
        from livekit.plugins import silero
        proc.userdata["vad"] = silero.VAD.load()
        logger.info("VAD loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load VAD: {str(e)}", exc_info=True)
        raise


async def entrypoint(ctx: JobContext):
    room_name = ctx.room.name
    logger.info(f"Connecting to room: {room_name}")
    
    try:
        # Connect to the room 
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        logger.info(f"Successfully connected to room: {room_name}")
        
        # Wait for the first participant to connect
        logger.info("Waiting for participant to join...")
        participant = await ctx.wait_for_participant()
        logger.info(f"Participant joined - identity: {participant.identity}, sid: {participant.sid}")
        
        # Set up recording with participant metadata
        logger.info("Setting up reccording for this session")
        egress_id = await setup_recording(room_name, participant)
        if egress_id:
            logger.info(f"Recording set up with egress ID: {egress_id}")
        else:
            logger.warning("Failed to set up recording, continuing without recording")

        # Extract context data and build prompt
        logger.info("Extracting context data from participant metadata")
        context_data = extract_context_data(participant)
        logger.debug(f"Context data extracted: {context_data}")
        
        logger.info("Building system prompt from context")
        system_prompt = build_system_prompt(context_data)
        logger.debug(f"System prompt built: {system_prompt[:100]}...")
        
        # Create and start the agent
        logger.info("Creating voice agent")
        agent, usage_collector = create_voice_agent(ctx, system_prompt)
        
        # Register event listeners for logging
        @agent.on("user_speech_committed")
        def on_user_speech_committed(transcript):
            logger.info(f"User transcript: {transcript}")
            
        @agent.on("agent_started_speaking")
        def on_agent_started_speaking():
            logger.info("Agent started speaking")
            
        @agent.on("agent_stopped_speaking")
        def on_agent_stopped_speaking():
            logger.info("Agent stopped speaking")
            
        @agent.on("metrics_collected")
        def on_metrics_logged(metrics_data):
            logger.debug(f"Metrics collected: {type(metrics_data).__name__}")
        
        logger.info(f"Starting voice agent for participant {participant.identity}")
        agent.start(ctx.room, participant)
        
        # Greet the user
        logger.info("Creating greeting")
        greeting = create_greeting(context_data)
        logger.info(f"Sending greeting: {greeting}")
        await agent.say(greeting, allow_interruptions=True)
        logger.info("Greeting sent, agent is now listening")
        
    except Exception as e:
        logger.error(f"Error in entrypoint: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("Starting voice agent application via CLI")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
    logger.info("Voice agent application shutting down")
