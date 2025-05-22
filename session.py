import os
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import (
    noise_cancellation,
)
import requests
import json

from agents import GreeterAgent
from context import UserData, extract_context_data, build_system_prompt, create_greeting
from config import create_voice_agent
from flow import FlowGraph
from logger_config import setup_logging
from recording import setup_recording, save_transcript
from livekit.agents.voice.room_io import RoomInputOptions


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

        # Extract metadata from participant
        metadata = json.loads(participant.metadata)
        user_id = metadata.get("user_id")
        job_id = metadata.get("job_id")
        applicant_name = metadata.get("applicant_name")
        scout_name = metadata.get("scout_name")
        
        flow_data = context_data.get("flow", {})
        flow_graph = FlowGraph.from_dict(flow_data)
        initial_node = flow_graph.get_initial_node()
        if initial_node is None:
            raise ValueError("Flow graph must have an initial node")
        userdata = UserData(context_data=context_data, flow=flow_graph, current_node=initial_node)
        logger.debug(f"Context data extracted: {context_data}")
        
        logger.info("Building system prompt from context")

        
        # Create and start the agent
        voice_data = context_data.get('voice', {})

        # logger.info(f"Creating voice agent, setting voice to: {voice_data.get('id', '')}")
        agent_session, usage_collector = create_voice_agent(ctx, userdata, voice_data.get("id", ""))
        
        # Create a list to store all transcripts
        conversation_transcripts = []

        @agent_session.on("conversation_item_added")
        def on_conversation_item_added(event):
            if event.item.role == "user":
                conversation_transcripts.append({
                    "speaker": f"applicant({applicant_name})", 
                    "text": event.item.text_content
                })
            elif event.item.role == "assistant":
                conversation_transcripts.append({
                    "speaker": f"scout({scout_name})", 
                    "text": event.item.text_content
                })


        async def notify_analysis_bot():
            logger.info("Interview finished - notifying analysis bot")
            try:
                # Skip notification if recording wasn't successful
                if not egress_id:
                    logger.warning("No recording egress ID available - skipping analysis notification")
                    return
                
                # Save transcript if we have any
                if conversation_transcripts:
                    logger.info(f"Saving {len(conversation_transcripts)} transcript segments")
                    save_result = save_transcript(conversation_transcripts, room_name, user_id, job_id)
                    if save_result:
                        logger.info("Transcript saved successfully")
                    else:
                        logger.warning("Failed to save transcript")
                    
                # Skip notification for demo interviews
                is_demo = False
                application_id = None
                
                if participant and participant.metadata:
                    try:
                        metadata = json.loads(participant.metadata)
                        is_demo = metadata.get("is_demo", False)
                        application_id = metadata.get("application_id")
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse participant metadata as JSON")
                
                if is_demo:
                    logger.info("Demo interview - skipping analysis notification")
                    return
                    
                if not user_id or not job_id:
                    logger.warning("Missing user_id or job_id - skipping analysis notification")
                    return
                    
                # Prepare minimal payload
                payload = {
                    "recording_id": egress_id,
                    "user_id": user_id,
                    "job_id": job_id,
                    "application_id": application_id
                }
                print("reaches here")
                # Get the analysis bot endpoint from environment variables
                analysis_endpoint = os.environ.get("ANALYSIS_BOT_ENDPOINT")
                if not analysis_endpoint:
                    logger.error("Missing ANALYSIS_BOT_ENDPOINT environment variable")
                    return

                # Send notification to analysis bot
                headers = {
                    "Content-Type": "application/json",
                    # "Authorization": f"Bearer {os.environ.get('ANALYSIS_BOT_API_KEY', '')}"
                }
                
                response = requests.post(
                    analysis_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=10  # 10 second timeout
                )
                
                if response.status_code == 200:
                    logger.info(f"Analysis bot notification successful")
                else:
                    logger.error(f"Analysis bot notification failed: {response.status_code} - {response.text}")
                        
            except Exception as e:
                logger.error(f"Error notifying analysis bot: {str(e)}", exc_info=True)
        

        # Register the shutdown callback
        ctx.add_shutdown_callback(notify_analysis_bot)
        
        logger.info(f"Starting voice agent for participant {participant.identity}")
        
        # Greet the user
        logger.info("Creating greeting")
        
        await agent_session.start(
            agent= GreeterAgent(initial_node=initial_node, context_data=context_data),
            room=ctx.room,
            room_input_options=RoomInputOptions(
                noise_cancellation=  noise_cancellation.BVC())
        )
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
