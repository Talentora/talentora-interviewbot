import os
import sys
# Add the parent directory to Python path so we can import from app package
# This fixes the ModuleNotFoundError: No module named 'app' by making the app module importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 

import asyncio
import types
from app.bot.services.language_model import init_language_model
from pipecat.frames.frames import (
    LLMMessagesFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
    TextFrame
)
from pipecat.processors.frame_processor import FrameDirection

async def process_message(processor, user_input: str, session_id: str):
    # Create a messages frame with the user input
    messages_frame = LLMMessagesFrame([{
        "role": "user",
        "content": user_input
    }])
    
    # Override push_frame to stream output frames
    async def push_frame_override(self, frame, direction=None):
        if isinstance(frame, TextFrame):
            print(frame.text, end="", flush=True)
        elif isinstance(frame, LLMFullResponseEndFrame):
            print()  # New line after response ends

    processor.push_frame = types.MethodType(push_frame_override, processor)
    
    # Process the frame
    await processor.process_frame(messages_frame, direction=FrameDirection.DOWNSTREAM)


async def main():
    # Define a dummy configuration for the language model
    interview_config = {
        "bot_name": "TestBot",
        "company_name": "Test Company",
        "job_title": "Test Position",
        "company_context": "This is a test context.",
        "job_description": "This is a test job description.",
        "interview_questions": [
            "What is your favorite programming language?",
            "How do you approach problem-solving?"
        ]
    }

    # Initialize the language model (chain) with the test config
    processor, user_aggregator, assistant_aggregator = init_language_model(interview_config)

    # Use a fixed session id for testing purposes
    session_id = "test_session"

    # Test the processor with a sample user input
    print("Type your messages below (type 'exit' to quit):")
    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        print("Assistant: ", end="", flush=True)
        await process_message(processor, user_input, session_id)

if __name__ == "__main__":
    asyncio.run(main())