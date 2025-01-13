from fastapi import APIRouter, HTTPException
from app.api.models import BotRequest, RoomResponse
from app.services.daily import DailyService
from app.services.bot import BotService
from app.core.logger import logger

router = APIRouter()

@router.post("/", response_model=RoomResponse)
async def create_room(request: BotRequest):
    """Creates a new interview room and initializes the interview bot."""
    logger.info("Received request to create new interview room")
    
    try:
        # Create room using Daily service
        daily_service = DailyService()
        room_data = await daily_service.create_room()
        logger.info(f"Room created successfully: {room_data['room_url']}")
        
        # Initialize and start bot
        bot_service = BotService()
        await bot_service.start_bot(
            room_url=room_data["room_url"],
            token=room_data["token"],
            config=request
        )
        logger.info(f"Bot started successfully in room: {room_data['room_url']}")
        
        return RoomResponse(**room_data).model_dump()
        
    except Exception as e:
        logger.error(f"Error creating interview room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 