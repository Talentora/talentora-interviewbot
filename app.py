import os
from modal import Secret, App, Image, web_endpoint, enter, method
from fastapi import HTTPException
from typing import Dict

MAX_SESSION_TIME = 5 * 60  # 5 minutes

# This function downloads and caches the Silero VAD model to reduce cold start time
def download_models():
    import torch
    torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=True)

# Define the Docker image for the application
image = (
    Image
    .debian_slim(python_version="3.12")
    .pip_install(
        "pydantic==2.8.2",
        "pipecat-ai[daily,openai,cartesia,silero]==0.0.39",
        "httpx",
        "requests",
        "loguru",
        "websockets")
    .run_function(download_models)
)

# Create a Modal app
app = App("pipecat-example")

# Define the Bot class with Modal decorators
@app.cls(image=image,
           cpu=1.0,
           secrets=[Secret.from_name("rtvi-example-secrets")],
           keep_warm=2,
           enable_memory_snapshot=True,
           timeout=MAX_SESSION_TIME,
           container_idle_timeout=2,
           max_inputs=1,  # Do not reuse instances as the pipeline needs to be restarted
           retries=0)
class Bot:
    # Initialize the Silero VAD analyzer
    @enter()
    async def enter(self):
        from pipecat.vad.silero import SileroVADAnalyzer
        self.vad = SileroVADAnalyzer()
    
    # Main method to run the bot
    @method()
    async def run(self, room_url: str, token: str, config: Dict):
        # Import necessary modules
        import aiohttp
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.processors.frameworks.rtvi import (
            RTVIConfig,
            RTVIProcessor,
            RTVISetup)
        from pipecat.frames.frames import EndFrame
        from pipecat.transports.services.daily import DailyParams, DailyTransport
        
        # Set up the Daily transport and RTVI processor
        async with aiohttp.ClientSession() as session:
            transport = DailyTransport(
                room_url,
                token,
                "Realtime AI",
                DailyParams(
                    audio_out_enabled=True,
                    transcription_enabled=True,
                    vad_enabled=True,
                    vad_analyzer=self.vad
                ))

            rtai = RTVIProcessor(
                transport=transport,
                setup=RTVISetup(config=RTVIConfig(**config)),
                llm_api_key=os.getenv("OPENAI_API_KEY", ""),
                tts_api_key=os.getenv("CARTESIA_API_KEY", ""))

            # Set up the pipeline and task
            runner = PipelineRunner()
            pipeline = Pipeline([transport.input(), rtai])
            task = PipelineTask(
                pipeline,
                params=PipelineParams(
                    allow_interruptions=True,
                    enable_metrics=True,
                    send_initial_empty_metrics=False,
                ))

            # Define event handlers for the transport
            @transport.event_handler("on_first_participant_joined")
            async def on_first_participant_joined(transport, participant):
                transport.capture_participant_transcription(participant["id"])

            @transport.event_handler("on_participant_left")
            async def on_participant_left(transport, participant, reason):
                await task.queue_frame(EndFrame())

            @transport.event_handler("on_call_state_updated")
            async def on_call_state_updated(transport, state):
                if state == "left":
                    await task.queue_frame(EndFrame())

            # Run the pipeline
            await runner.run(task)

# Define the server function as a web endpoint
@app.function(image=image,
              secrets=[Secret.from_name("rtvi-example-secrets")],
              keep_warm=1)
@web_endpoint(method="POST")
def server(config: Dict):
    # Import Daily REST helper
    from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomObject, DailyRoomProperties, DailyRoomParams

    # Set up Daily API parameters
    DAILY_API_URL = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
    DAILY_DOMAIN = os.getenv("DAILY_DOMAIN", "https://rtvi.daily.co")
    DAILY_API_KEY = os.getenv("DAILY_API_KEY", "")

    # Check for valid configuration
    if not config:
        raise Exception("Missing RTVI configuration object for bot")

    # Create a Daily REST helper
    daily_rest_helper = DailyRESTHelper(DAILY_API_KEY, DAILY_API_URL)

    # Check if we should use an existing room or create a new one
    debug_room = os.getenv("USE_DEBUG_ROOM", None)
    if debug_room:
        # Use existing debug room
        try:
            room: DailyRoomObject = daily_rest_helper.get_room_from_url(
                f"{DAILY_DOMAIN}/{debug_room}")
        except Exception:
            raise HTTPException(
                status_code=500, detail=f"Room not found: {debug_room}")
    else:
        # Create a new room
        try:
            params = DailyRoomParams(
                properties=DailyRoomProperties()
            )
            room: DailyRoomObject = daily_rest_helper.create_room(params=params)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"{e}")

    # Generate a token for the bot to join the session
    token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token for room: {room.name}")

    # Launch the bot in a new VM
    try:
        Bot().run.spawn(room.url, token, config)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start subprocess: {e}")

    # Generate a token for the user to join the session
    user_token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    # Return room information and user token
    return {
        "room_name": room.name,
        "room_url": room.url,
        "token": user_token
    }
