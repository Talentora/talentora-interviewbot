from pipecat.processors.idle_frame_processor import IdleFrameProcessor
from pipecat.frames.frames import LLMMessagesFrame

async def user_idle_callback(user_idle: IdleFrameProcessor):
    messages = [{
        "role": "system", 
        "content": "Ask the user if they are still there and try to prompt for some input."
    }]
    await user_idle.push_frame(LLMMessagesFrame(messages))

def init_idle_processor() -> IdleFrameProcessor:
    """Initialize and configure the idle processor to detect user inactivity."""
    idle_processor = IdleFrameProcessor(
        callback=user_idle_callback,
        timeout=5.0
    )
    return idle_processor
