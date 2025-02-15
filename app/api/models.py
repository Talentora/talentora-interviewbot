from pydantic import BaseModel
from typing import List

class InterviewConfig(BaseModel):
    """
    Represents the configuration for an interview session.
    
    Attributes:
    - bot_name (str): The name of the bot conducting the interview.
    - company_name (str): The name of the company conducting the interview.
    - job_title (str): The title of the job being interviewed for.
    - job_description (str): A description of the job being interviewed for.
    - company_context (str): Context about the company conducting the interview.
    - interview_questions (List[str]): A list of questions to be asked during the interview.
    """
    bot_name: str
    company_name: str
    job_title: str
    job_description: str
    company_context: str
    interview_questions: List[str]
    enable_recording: bool
    bot_test: bool
    demo: bool

class BotRequest(BaseModel):
    """
    Represents a request to initiate a bot session.
    
    Attributes:
    - voice_id (str): The ID of the voice to use for the bot.
    - max_duration (int, optional): The maximum duration of the session in seconds. Defaults to 300.
    - interview_config (InterviewConfig): The configuration for the interview session.
    """
    voice_id: str
    max_duration: int = 300
    interview_config: InterviewConfig

class RoomResponse(BaseModel):
    """
    Represents the response to a room creation request.
    
    Attributes:
    - room_url (str): The URL of the created room.
    - token (str): The token for accessing the created room.
    """
    room_url: str
    token: str 