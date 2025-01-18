import asyncio
from typing import AsyncGenerator
import sys

from pipecat.frames.frames import Frame, TextFrame
from pipecat.pipeline.pipeline import Pipeline
from app.bot.services.language_model import init_langchain_processor
async def get_user_input() -> AsyncGenerator[Frame, None]:
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit']:
                break
            yield TextFrame(user_input)
        except KeyboardInterrupt:
            break

async def handle_assistant_response(frame: Frame):
    if isinstance(frame, TextFrame):
        print(f"Assistant: {frame.text}")

async def main():
    # Initialize LLM service and aggregators using the function from language_model.py
    system_prompt = "You are a helpful assistant."
    interview_config = {
        'bot_name': 'Assistant',
        'company_name': 'Demo Company',
        'job_title': 'Chatbot',
        'company_context': 'This is a demo chatbot.',
        'job_description': 'Having conversations with users.',
        'interview_questions': []
    }
    
    llm_service, user_aggregator, assistant_aggregator = init_langchain_processor(interview_config)

    # Create pipeline
    pipeline = Pipeline([
        get_user_input(),
        user_aggregator,
        llm_service,
        assistant_aggregator,
        handle_assistant_response
    ])
    

    try:
        await pipeline.run()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("\nGoodbye!")

if __name__ == "__main__":
    asyncio.run(main())

