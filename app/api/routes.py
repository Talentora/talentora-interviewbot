from fastapi import APIRouter, HTTPException
from app.api.models import BotRequest, RoomResponse
from app.bot.interview_bot import InterviewBot
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper
from app.core.config import settings
from app.core.logger import logger

router = APIRouter()

@router.get("/")
async def hello_world():
    logger.info("Hello world endpoint called")
    return {
        "message": "Hello, World!"
    }

@router.post("/create-room", response_model=RoomResponse)
async def create_room(request: BotRequest):
    logger.info("Received request to create new interview room")
    logger.debug(f"Request details: {request}")
    
    try:
        logger.debug("Initializing Daily REST helper")
        daily_helper = DailyRESTHelper(settings.DAILY_API_KEY)
        
        logger.info("Creating new Daily room")
        room = await daily_helper.create_room(
            expiry=3600,  # 1 hour
            properties={
                "enable_chat": True,
                "enable_knocking": False,
                "start_audio_off": False,
                "start_video_off": True,
                "max_participants": 2
            }
        )
        
        room_url = room["url"]
        logger.info(f"Room created successfully: {room_url}")
        
        logger.debug("Generating room token")
        token = await daily_helper.get_token(room_url, 3600)
        
        logger.info("Initializing interview bot")
        bot_config = {
            "voice_id": request.voice_id,
            "max_duration": request.max_duration,
            "interview_config": request.interview_config.dict()
        }
        
        bot = InterviewBot(bot_config)
        logger.info("Starting bot in background")
        await bot.start(room_url, token)
        
        return RoomResponse(
            room_url=room_url,
            token=token
        )
    except Exception as e:
        logger.error(f"Error creating interview room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 