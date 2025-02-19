from pipecat.processors.idle_frame_processor import IdleFrameProcessor
from pipecat.frames.frames import LLMMessagesFrame

GLOBAL_IDLE_COUNT = 0
MAX_IDLE_COUNT = 3

async def user_idle_callback(user_idle: IdleFrameProcessor):
    global GLOBAL_IDLE_COUNT
    messages = [{
        "role": "system",
        "content": f"<instruction>This is attempt {GLOBAL_IDLE_COUNT + 1} to check on the interviewee. If there has been no response from the interviewee, ask them if they are still there.</instruction>"
    }]
    GLOBAL_IDLE_COUNT += 1
    if GLOBAL_IDLE_COUNT >= MAX_IDLE_COUNT:
        return
    await user_idle.push_frame(LLMMessagesFrame(messages))

def init_idle_processor() -> IdleFrameProcessor:
    """Initialize and configure the idle processor to detect user inactivity."""
    idle_processor = IdleFrameProcessor(
        callback=user_idle_callback,
        timeout=5.0
    )
    return idle_processor
