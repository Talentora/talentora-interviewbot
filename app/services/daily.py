from typing import Dict
import aiohttp
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomParams, DailyRoomProperties
from app.core.config import settings
from app.core.logger import logger
import time
class DailyService:
    def __init__(self):
        self.api_key = settings.DAILY_API_KEY
        self.api_url = "https://api.daily.co/v1"  # Use the standard Daily.co API URL
        
    async def handle_participant_leave(self, participant_id: str) -> None:
        """Handle participant leave event gracefully."""
        try:
            logger.info(f"Participant {participant_id} is leaving the room")
            # Add any cleanup logic here
            
        except Exception as e:
            logger.warning(f"Error during participant cleanup: {str(e)}")
            # Don't raise the exception as this is an expected scenario
            pass

    async def create_room(self, enableRecording, demo) -> Dict[str, str]:
        """Creates a Daily room and returns room URL and token."""
        logger.debug("Creating Daily room")
        
        async with aiohttp.ClientSession() as session:
            helper = DailyRESTHelper(
                daily_api_key=self.api_key,
                daily_api_url=self.api_url,
                aiohttp_session=session
            )
            
            try:
                room_properties = DailyRoomProperties(
                    enable_chat=True,
                    enable_knocking=False,
                    start_audio_off=False,
                    start_video_off=True,
                    max_participants=2,
                    enable_transcription=True,
                    exp=time.time() + 1800,
                )
                
                if enableRecording:
                    room_properties.enable_recording = 'cloud'
                
                if demo:
                    room_properties.exp = time.time() + 300

                room = await helper.create_room(
                    DailyRoomParams(properties=room_properties)
                )

                token = await helper.get_token(room.url, 3600)
                logger.info(f"Created room: {room.url}")
                
                return {
                    "room_url": room.url,
                    "token": token
                } 
            except Exception as e:
                logger.error(f"Error creating or managing room: {str(e)}")
                raise 