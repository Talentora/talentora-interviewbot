import logging
import json

from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import (
    cartesia,
    openai,
    deepgram,
    noise_cancellation,
    silero,
    turn_detector,
)


load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")
    
    # Extract context data from participant metadata if it exists
    context_data = {}
    if participant.metadata:
        try:
            metadata = json.loads(participant.metadata)
            if metadata.get("type") == "interview_context":
                context_data = metadata
                logger.info(f"Received interview context data: {context_data}")
        except json.JSONDecodeError:
            logger.warning("Failed to parse participant metadata as JSON")
    
    # Build system prompt based on the context data
    system_prompt = "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
    
    if context_data:
        scout_name = context_data.get("scout_name", "Interviewer")
        scout_role = context_data.get("scout_role", "Recruiter")
        scout_emotion = context_data.get("scout_emotion", "Professional")
        company_name = context_data.get("company_name", "the company")
        company_description = context_data.get("company_description", "")
        company_culture = context_data.get("company_culture", "")
        
        # Create a more detailed interview-specific prompt
        system_prompt = (
            f"You are {scout_name}, a {scout_role} at {company_name}. "
            f"Your tone should be {scout_emotion}. You are conducting a job interview. "
            f"\n\nAbout {company_name}: {company_description} "
            f"\n\nCompany culture: {company_culture} "
            f"\n\nYour interface with users will be voice. Use short and concise responses, "
            f"avoiding usage of unpronounceable punctuation. Speak naturally as a human interviewer would."
        )
        
        # Add interview questions if available
        interview_questions = context_data.get("interview_questions", [])
        if interview_questions:
            system_prompt += "\n\nYou should ask the following questions during the interview:\n"
            for i, question in enumerate(interview_questions):
                system_prompt += f"{i+1}. {question}\n"
        
        # Additional context from scout prompt if available
        if context_data.get("scout_prompt"):
            system_prompt += f"\n\nAdditional guidance: {context_data.get('scout_prompt')}"
    else:
        # Fall back to the default prompt if no context data is available
        system_prompt += (
            "You should use short and concise responses, and avoiding usage of unpronouncable punctuation. "
            "You were created as a demo to showcase the capabilities of LiveKit's agents framework."
        )
    
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=system_prompt,
    )

    # This project is configured to use Deepgram STT, OpenAI LLM and Cartesia TTS plugins
    # Other great providers exist like Cerebras, ElevenLabs, Groq, Play.ht, Rime, and more
    # Learn more and pick the best one for your app:
    # https://docs.livekit.io/agents/plugins
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(),
        # use LiveKit's transformer-based turn detector
        turn_detector=turn_detector.EOUModel(),
        # minimum delay for endpointing, used when turn detector believes the user is done with their turn
        min_endpointing_delay=0.5,
        # maximum delay for endpointing, used when turn detector does not believe the user is done with their turn
        max_endpointing_delay=5.0,
        # enable background voice & noise cancellation, powered by Krisp
        # included at no additional cost with LiveKit Cloud
        noise_cancellation=noise_cancellation.BVC(),
        chat_ctx=initial_ctx,
    )

    usage_collector = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
        metrics.log_metrics(agent_metrics)
        usage_collector.collect(agent_metrics)

    agent.start(ctx.room, participant)

    # Personalized greeting based on context
    greeting = "Hey, how can I help you today?"
    if context_data.get("scout_name"):
        greeting = f"Hello, I'm {context_data.get('scout_name')} from {context_data.get('company_name', 'the company')}. Thanks for joining this interview today. How are you doing?"
    
    await agent.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
