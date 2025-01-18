import asyncio
import json
from loguru import logger
from app.bot.interview_bot import InterviewBot
from app.services.daily import DailyService
from app.core.config import settings

async def test_interview_bot():
    try:
        # Test configuration
        config = {
            "voice_id": "79a125e8-cd45-4c13-8a67-188112f4dd22",
            "max_duration": 300,
            "interview_config": {
                "bot_name": "Sarah",
                "company_name": "TechCorp",
                "job_title": "Senior Software Engineer",
                "job_description": "We are looking for a Senior Software Engineer with strong experience in AI/ML...",
                "company_context": "TechCorp is a leading technology company...",
                "interview_questions": [
                    "Can you tell me about your most challenging project?",
                    "How do you approach problem-solving?",
                    "What interests you about this role?"
                ]
            }
        }

        # Create a new Daily room
        logger.info("Creating Daily room...")
        daily_service = DailyService()
        room_data = await daily_service.create_room()
        room_url = room_data["room_url"]
        token = room_data["token"]
        logger.info(f"Room created: {room_url}")

        # Initialize the bot
        logger.info("Initializing bot...")
        bot = InterviewBot(config)

        # Start the bot in the room
        logger.info("Starting bot...")
        await bot.start(room_url=room_url, token=token)

        # Keep the script running to maintain the connection
        logger.info("Bot is running. Press Ctrl+C to exit...")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received exit signal. Shutting down...")
    except Exception as e:
        logger.error(f"Error during test: {e}")
    finally:
        logger.info("Test complete")

if __name__ == "__main__":
    # Run the test
    logger.info("Starting manual bot test...")
    asyncio.run(test_interview_bot())