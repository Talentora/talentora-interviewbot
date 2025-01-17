from typing import Dict, Any
from loguru import logger
from pipecat.transports.services.daily import DailyTransport
from pipecat.frames.frames import LLMMessagesFrame

async def on_joined(transport: DailyTransport, data: Dict[str, Any]):
    """Called when the bot successfully joins the room."""
    logger.info(f"Bot joined room with data: {data}")

async def on_participant_joined(transport: DailyTransport, participant: Dict[str, Any]):
    """Called when any participant joins the room."""
    # Don't respond to our own join event
    if participant.get("isLocal", False):
        return
        
    logger.info(f"Participant joined: {participant}")
    
    # Send a welcome message through the pipeline
    welcome_msg = f"Hello! I'm your AI interviewer today. I'll be asking you some technical questions. Are you ready to begin?"
    # await transport.
    await transport.output().push_frame(LLMMessagesFrame([{
        "role": "system",
        "content": welcome_msg
    }]))

async def on_participant_left(transport: DailyTransport, participant: Dict[str, Any], reason: str):
    """Called when a participant leaves the room."""
    logger.info(f"Participant {participant['id']} left: {reason}")

async def on_error(transport: DailyTransport, error: str):
    """Called when a transport error occurs."""
    logger.error(f"Transport error: {error}")

async def on_transcription_message(transport: DailyTransport, message: Dict[str, Any]):
    """Called when a transcription message is received."""
    participant_id = message.get("participantId")
    text = message.get("text")
    is_final = message["rawResponse"]["is_final"]
    logger.debug(f"Transcription from {participant_id}: {text} (final: {is_final})")
