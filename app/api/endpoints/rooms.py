from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.api.models import BotRequest, RoomResponse
from app.services.daily import DailyService
from app.services.bot import BotService
from app.core.logger import logger
import requests

router = APIRouter()

async def start_bot_background(room_url: str, token: str, config: BotRequest):
    """Start the bot in the background"""
    try:
        bot_service = BotService()
        await bot_service.start_bot(
            room_url=room_url,
            token=token,
            config=config
        )
        logger.info(f"Bot started successfully in room: {room_url}")
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")

@router.post("/", response_model=RoomResponse)
async def create_room(request: BotRequest, background_tasks: BackgroundTasks):
    """Creates a new interview room and initializes the interview bot."""
    logger.info("Received request to create new interview room")
    
    try:
        # Create room using Daily service
        daily_service = DailyService()
        room_data = await daily_service.create_room()
        logger.info(f"Room created successfully: {room_data['room_url']}")
        
        # Start bot initialization in the background
        background_tasks.add_task(
            start_bot_background,
            room_data["room_url"],
            room_data["token"],
            request
        )
        
        return RoomResponse(**room_data).model_dump()
        
    except Exception as e:
        logger.error(f"Error creating interview room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/")
async def meow():
    print("yes")
    logger.info("uyes2")
    headers = {
        "x-api-key": "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",         # Replace with your actual API key
        "anthropic-version": "2023-06-01"      # Use the version required by your API key
    }

    response = requests.get("https://api.anthropic.com/v1/models", headers=headers)

    if response.status_code == 200:
        models_info = response.json()
        print(models_info)  # This will print a list of available models and their details
    else:
        print(f"Error {response.status_code}: {response.text}")