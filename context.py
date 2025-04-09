import json
import logging

logger = logging.getLogger("voice-agent")

def extract_context_data(participant):
    """Extract context data from participant metadata if it exists."""
    context_data = {}
    if participant.metadata:
        try:
            metadata = json.loads(participant.metadata)
            if metadata.get("type") == "interview_context":
                context_data = metadata
                logger.info(f"Received interview context data: {context_data}")
        except json.JSONDecodeError:
            logger.warning("Failed to parse participant metadata as JSON")
    return context_data

def build_system_prompt(context_data):
    """Build system prompt based on the context data."""
    system_prompt = "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
    
    if context_data:
        scout_name = context_data.get("scout_name", "Interviewer")
        scout_role = context_data.get("scout_role", "Recruiter")
        scout_emotion = context_data.get("scout_emotion", "Professional")
        company_name = context_data.get("company_name", "the company")
        company_description = context_data.get("company_description", "")
        company_culture = context_data.get("company_culture", "")
        
        # Create a more detailed interview-specific prompt
        system_prompt = (
            f"You are {scout_name}, a {scout_role} at {company_name}. "
            f"Your tone should be {scout_emotion}. You are conducting a job interview. "
            f"\n\nAbout {company_name}: {company_description} "
            f"\n\nCompany culture: {company_culture} "
            f"\n\nYour interface with users will be voice. Use short and concise responses, "
            f"avoiding usage of unpronounceable punctuation. Speak naturally as a human interviewer would."
        )
        
        # Add interview questions if available
        interview_questions = context_data.get("interview_questions", [])
        if interview_questions:
            system_prompt += "\n\nYou should ask the following questions during the interview:\n"
            for i, question in enumerate(interview_questions):
                system_prompt += f"{i+1}. {question}\n"
        
        # Additional context from scout prompt if available
        if context_data.get("scout_prompt"):
            system_prompt += f"\n\nAdditional guidance: {context_data.get('scout_prompt')}"
    else:
        # Fall back to the default prompt if no context data is available
        system_prompt += (
            "You should use short and concise responses, and avoiding usage of unpronouncable punctuation. "
            "You were created as a demo to showcase the capabilities of LiveKit's agents framework."
        )
    
    return system_prompt

def create_greeting(context_data):
    """Create a personalized greeting based on context."""
    greeting = "Hey, how can I help you today?"
    if context_data.get("scout_name"):
        greeting = f"Hello, I'm {context_data.get('scout_name')} from {context_data.get('company_name', 'the company')}. Thanks for joining this interview today. How are you doing?"
    return greeting 