from typing import Dict
import aiohttp
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomParams, DailyRoomProperties
from app.core.config import settings
from app.core.logger import logger

class DailyService:
    def __init__(self):
        self.api_key = settings.DAILY_API_KEY
        self.api_url = "https://api.daily.co/v1"  # Use the standard Daily.co API URL
        
    async def create_room(self) -> Dict[str, str]:
        """Creates a Daily room and returns room URL and token."""
        logger.debug("Creating Daily room")
        
        async with aiohttp.ClientSession() as session:
            helper = DailyRESTHelper(
                daily_api_key=self.api_key,
                daily_api_url=self.api_url,
                aiohttp_session=session
            )
            
            logger.info(f"Helper: {helper}")
           
            room = await helper.create_room(
                DailyRoomParams(
                    properties=DailyRoomProperties(
                        enable_chat=True,
                        enable_knocking=False,
                        start_audio_off=False,
                        start_video_off=True,
                        max_participants=2,
                        enable_transcription=True
                    )
                )
            )

            logger.info(f"Room created: {room}")
            
            token = await helper.get_token(room.url, 3600)
            logger.info(f"Created room: {room.url}")
            
            return {
                "room_url": room.url,
                "token": token
            } 