from pipecat.processors.idle_frame_processor import IdleFrameProcessor
from pipecat.frames.frames import LLMMessagesFrame, TextFrame
from pipecat.processors.frame_processor import FrameDirection

# Maximum number of times to check in with an idle user
MAX_IDLE_RETRIES = 3
# Counter to track number of idle retries
idle_retry_count = 0

async def user_idle_callback(user_idle: IdleFrameProcessor):
    global idle_retry_count
    
    if idle_retry_count >= MAX_IDLE_RETRIES:
        # Stop checking in after max retries
        return
        
    messages = [{
        "role": "system",
        "content": "<instruction>If there has been no response from the interviewee, ask them if they are still there.</instruction>"
    }]
    idle_retry_count += 1
    await user_idle.push_frame(LLMMessagesFrame(messages))

def init_idle_processor() -> IdleFrameProcessor:
    """Initialize and configure the idle processor to detect user inactivity."""
    global idle_retry_count
    
    async def reset_counter(processor: IdleFrameProcessor, frame: TextFrame, direction: FrameDirection):
        global idle_retry_count
        if direction == FrameDirection.DOWNSTREAM:
            idle_retry_count = 0
    
    idle_processor = IdleFrameProcessor(
        callback=user_idle_callback,
        timeout=5.0
    )
    
    # Reset counter when user speaks
    idle_processor.on_frame(TextFrame, reset_counter)
    
    return idle_processor
