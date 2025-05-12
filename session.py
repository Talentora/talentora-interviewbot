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
from livekit.plugins import (
    cartesia,
    openai,
    deepgram,
    noise_cancellation,
    turn_detector,
)

from agents import GreeterAgent
from context import UserData, extract_context_data, build_system_prompt, create_greeting
from config import create_voice_agent
from flow import FlowGraph
from logger_config import setup_logging
from recording import setup_recording
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
        
        # sample_flow_data = {
        #     "edges": [
        #         {
        #         "id": "e-start-intro",
        #         "type": "smoothstep",
        #         "source": "start",
        #         "target": "intro",
        #         "sourceHandle": "right",
        #         "targetHandle": "left"
        #         },
        #         {
        #         "id": "e-intro-question1",
        #         "type": "smoothstep",
        #         "source": "intro",
        #         "target": "question1",
        #         "sourceHandle": "bottom",
        #         "targetHandle": "top"
        #         },
        #         {
        #         "id": "e-question1-question2",
        #         "type": "smoothstep",
        #         "source": "question1",
        #         "target": "question2",
        #         "sourceHandle": "bottom",
        #         "targetHandle": "top"
        #         },
        #         {
        #         "id": "e-question2-technical",
        #         "type": "smoothstep",
        #         "source": "question2",
        #         "target": "technical",
        #         "sourceHandle": "right",
        #         "targetHandle": "left"
        #         },
        #         {
        #         "id": "e-technical-question3",
        #         "type": "smoothstep",
        #         "source": "technical",
        #         "target": "question3",
        #         "sourceHandle": "bottom",
        #         "targetHandle": "top"
        #         },
        #         {
        #         "id": "e-question3-question4",
        #         "type": "smoothstep",
        #         "source": "question3",
        #         "target": "question4",
        #         "sourceHandle": "bottom",
        #         "targetHandle": "top"
        #         },
        #         {
        #         "id": "e-question4-question5",
        #         "type": "smoothstep",
        #         "source": "question4",
        #         "target": "question5",
        #         "sourceHandle": "right",
        #         "targetHandle": "left"
        #         },
        #         {
        #         "id": "e-question5-cultural",
        #         "type": "smoothstep",
        #         "source": "question5",
        #         "target": "cultural",
        #         "sourceHandle": "left",
        #         "targetHandle": "right"
        #         },
        #         {
        #         "id": "e-cultural-question6",
        #         "type": "smoothstep",
        #         "source": "cultural",
        #         "target": "question6",
        #         "sourceHandle": "bottom",
        #         "targetHandle": "top"
        #         },
        #         {
        #         "id": "e-question6-question7",
        #         "type": "smoothstep",
        #         "source": "question6",
        #         "target": "question7",
        #         "sourceHandle": "bottom",
        #         "targetHandle": "top"
        #         },
        #         {
        #         "id": "e-question7-conclusion",
        #         "type": "smoothstep",
        #         "source": "question7",
        #         "target": "conclusion",
        #         "sourceHandle": "right",
        #         "targetHandle": "left"
        #         }
        #     ],
        #     "nodes": [
        #         {
        #         "id": "start",
        #         "data": {
        #             "label": "Interview Start",
        #             "content": "Welcome the candidate and introduce yourself. Explain the interview process and set expectations."
        #         },
        #         "type": "input",
        #         "width": 150,
        #         "height": 164,
        #         "position": {
        #             "x": 100,
        #             "y": 150
        #         }
        #         },
        #         {
        #         "id": "intro",
        #         "data": {
        #             "label": "Background Section",
        #             "content": "This section covers the candidate's background and experience."
        #         },
        #         "type": "section",
        #         "width": 256,
        #         "height": 128,
        #         "position": {
        #             "x": 350,
        #             "y": 150
        #         }
        #         },
        #         {
        #         "id": "question1",
        #         "data": {
        #             "label": "Experience Question",
        #             "content": "Tell me about your most recent role and your key responsibilities.",
        #             "criteria": "Look for relevant experience and clear communication."
        #         },
        #         "type": "question",
        #         "width": 256,
        #         "height": 180,
        #         "position": {
        #             "x": 350,
        #             "y": 300
        #         }
        #         },
        #         {
        #         "id": "question2",
        #         "data": {
        #             "label": "Challenge Question",
        #             "content": "Describe a challenging situation you faced in your previous role and how you resolved it.",
        #             "criteria": "Assess problem-solving skills and resilience."
        #         },
        #         "type": "question",
        #         "width": 256,
        #         "height": 184,
        #         "dragging": False,
        #         "position": {
        #             "x": 350,
        #             "y": 500
        #         },
        #         "selected": False,
        #         "positionAbsolute": {
        #             "x": 795,
        #             "y": 345
        #         }
        #         },
        #         {
        #         "id": "technical",
        #         "data": {
        #             "label": "Technical Skills",
        #             "content": "This section evaluates the candidate's technical knowledge and skills."
        #         },
        #         "type": "section",
        #         "width": 256,
        #         "height": 128,
        #         "position": {
        #             "x": 750,
        #             "y": 150
        #         }
        #         },
        #         {
        #         "id": "question3",
        #         "data": {
        #             "label": "Technical Question 1",
        #             "content": "Explain how you would design a scalable system for handling high traffic loads.",
        #             "criteria": "Evaluate system design knowledge and scalability concepts."
        #         },
        #         "type": "question",
        #         "width": 256,
        #         "height": 200,
        #         "position": {
        #             "x": 750,
        #             "y": 300
        #         }
        #         },
        #         {
        #         "id": "question4",
        #         "data": {
        #             "label": "Technical Question 2",
        #             "content": "Describe your experience with CI/CD pipelines and how you've implemented them.",
        #             "criteria": "Check for DevOps knowledge and automation experience."
        #         },
        #         "type": "question",
        #         "width": 256,
        #         "height": 200,
        #         "dragging": False,
        #         "position": {
        #             "x": 750,
        #             "y": 500
        #         },
        #         "selected": False,
        #         "positionAbsolute": {
        #             "x": 780,
        #             "y": 570
        #         }
        #         },
        #         {
        #         "id": "question5",
        #         "data": {
        #             "label": "Technical Question 3",
        #             "content": "How do you ensure code quality in your projects?",
        #             "criteria": "Look for testing strategies, code reviews, and quality assurance practices."
        #         },
        #         "type": "question",
        #         "width": 256,
        #         "height": 180,
        #         "dragging": False,
        #         "position": {
        #             "x": 1680,
        #             "y": 375
        #         },
        #         "selected": True,
        #         "positionAbsolute": {
        #             "x": 1680,
        #             "y": 375
        #         }
        #         },
        #         {
        #         "id": "cultural",
        #         "data": {
        #             "label": "Cultural Fit",
        #             "content": "This section assesses how well the candidate aligns with company values and culture."
        #         },
        #         "type": "section",
        #         "width": 256,
        #         "height": 128,
        #         "dragging": False,
        #         "position": {
        #             "x": 1150,
        #             "y": 150
        #         },
        #         "selected": False,
        #         "positionAbsolute": {
        #             "x": 1095,
        #             "y": 45
        #         }
        #         },
        #         {
        #         "id": "question6",
        #         "data": {
        #             "label": "Teamwork Question",
        #             "content": "How do you approach collaborating with team members who have different working styles?",
        #             "criteria": "Assess adaptability, empathy, and collaboration skills."
        #         },
        #         "type": "question",
        #         "width": 256,
        #         "height": 204,
        #         "dragging": False,
        #         "position": {
        #             "x": 1150,
        #             "y": 300
        #         },
        #         "selected": False,
        #         "positionAbsolute": {
        #             "x": 1350,
        #             "y": 405
        #         }
        #         },
        #         {
        #         "id": "question7",
        #         "data": {
        #             "label": "Growth Question",
        #             "content": "Where do you see yourself professionally in 3-5 years?",
        #             "criteria": "Evaluate ambition, career planning, and alignment with company growth."
        #         },
        #         "type": "question",
        #         "width": 256,
        #         "height": 180,
        #         "dragging": False,
        #         "position": {
        #             "x": 1150,
        #             "y": 500
        #         },
        #         "selected": False,
        #         "positionAbsolute": {
        #             "x": 1395,
        #             "y": 600
        #         }
        #         },
        #         {
        #         "id": "conclusion",
        #         "data": {
        #             "label": "Interview Conclusion",
        #             "content": "Thank the candidate for their time. Ask if they have any questions about the role or company. Explain next steps in the hiring process."
        #         },
        #         "type": "conclusion",
        #         "width": 256,
        #         "height": 168,
        #         "dragging": False,
        #         "position": {
        #             "x": 1850,
        #             "y": 150
        #         },
        #         "selected": False,
        #         "positionAbsolute": {
        #             "x": 1890,
        #             "y": 240
        #         }
        #         }
        #     ]
        # }
        
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
        
        # Register event listeners for logging #TODO: handle adding logging to room on startup
        # @agent_session.on("user_input_transcribed")
        # def on_user_speech_committed(transcript):
        #     logger.info(f"User transcript: {transcript}")
            
        # @agent_session.on("agent_started_speaking")
        # def on_agent_started_speaking():
        #     logger.info("Agent started speaking")
            
        # @agent_session.on("agent_stopped_speaking")
        # def on_agent_stopped_speaking():
        #     logger.info("Agent stopped speaking")
            
        # @agent_session.on("metrics_collected")
        # def on_metrics_logged(metrics_data):
        #     logger.debug(f"Metrics collected: {type(metrics_data).__name__}")

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
