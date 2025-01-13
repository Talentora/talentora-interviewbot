from typing import Dict
from app.bot.interview_bot import InterviewBot
from app.api.models import BotRequest
from app.core.logger import logger

class BotService:
    async def start_bot(self, room_url: str, token: str, config: BotRequest):
        """Initializes and starts the interview bot."""
        try:
            bot_config = {
                "voice_id": config.voice_id,
                "max_duration": config.max_duration,
                "interview_config": config.interview_config.model_dump()
            }
            
            bot = InterviewBot(bot_config)
            logger.info(f"Created bot: {bot}")

            logger.info(f"Starting bot with room_url: {room_url} and token: {token}")
            await bot.start(room_url, token)
            
        except Exception as e:
            logger.error(f"Failed to start bot: {str(e)}")
            raise 