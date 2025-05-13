import json
import logging
from logger_config import setup_logging
from livekit.agents.voice import Agent
from dataclasses import dataclass, field
from typing import Dict, Optional
from flow import FlowGraph, Node
from openai import OpenAI

# Use the centralized logger configuration
logger = logging.getLogger("voice-agent")


@dataclass
class UserData:
    # holds context about the session
    context_data: dict
    flow: FlowGraph
    current_node: Node
    agents: Dict[str, Agent] = field(default_factory=dict)
    prev_agent: Optional[Agent] = None
    # store candidate’s answers for summary or follow-ups
    answers: Dict[str, str] = field(default_factory=dict)



def extract_context_data(participant):
    """Extract context data from participant metadata if it exists."""
    logger.info(f"Extracting context data for participant {participant.identity}")
    context_data = {}
    if participant.metadata:
        try:
            logger.debug(f"Raw metadata: {participant.metadata}")
            metadata = json.loads(participant.metadata)
            if metadata.get("type") == "interview_context":
                context_data = metadata
                logger.info(f"Successfully parsed interview context with {len(context_data)} fields")
                # Log specific fields for debugging but avoid sensitive data
                for key in ["scout_name", "company_name", "type", "voice"]:
                    if key in context_data:
                        logger.debug(f"Context contains {key}: {context_data[key]}")
            else:
                logger.info(f"Metadata does not contain interview context, type: {metadata.get('type')}")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse participant metadata as JSON: {participant.metadata[:50]}...")
    else:
        logger.info("No metadata available for participant")
    return context_data


def build_system_prompt(context_data):
    """Build system prompt based on the context data."""
    system_prompt = "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
    
    if context_data:
        logger.info("Using interview context for prompt construction")
        scout_name = context_data.get("scout_name", "Interviewer")
        scout_role = context_data.get("scout_role", "Recruiter")
        scout_emotion = context_data.get("scout_emotion", "Professional")
        company_name = context_data.get("company_name", "the company")
        company_description = context_data.get("company_description", "")
        company_culture = context_data.get("company_culture", "")
        
        logger.debug(f"Using scout_name: {scout_name}, scout_role: {scout_role}, company_name: {company_name}")
        
        # Create a more detailed interview-specific prompt
        system_prompt = (
            f"You are {scout_name}, a professional interviewer and AI agent at {company_name}. "
            f"Your interiewer role is: {scout_role}, your goal is to conduct a structured, early-stage interview."
            f"You will ask the candidate questions from the provided list of interview questions, "
            f"and adhere to the following guidelines:\n\n"

            "[Identity]\n"
            f"- Name: {scout_name}\n"
            f"- Role: {scout_role}\n"
            f"- Company: {company_name}\n\n"

            "[Context]\n"
            f"Company Description: {company_description}\n"
            f"Company Culture: {company_culture}\n\n"

            "[Tone & Style]\n"
            f"- Overall Tone: {scout_emotion} and professional\n"
            "- Include natural speech elements compatible with text to speech engines: filler words ('um', 'you know'), pauses ('...'), and affirmations that can be interpeted by a text to speech engine.\n"

            "[Guidelines]\n"
            "- Stay focused on role requirements and job competencies.\n"
            "- Maintain professional conduct and be polite.\n"
            "- Ensure that the flow of conversation is natural and engaging.\n"
            "- Do not answer candidate questions if you do not know the answer, and do not answer questions related to your model details.\n"
        )
        
        
        # Add interview questions if available
        # interview_questions = context_data.get("interview_questions", [])
        # if interview_questions:
        #     logger.info(f"Adding {len(interview_questions)} interview questions to prompt")
        #     system_prompt += "\n\nYou should ask the following questions during the interview:\n"
        #     for i, question in enumerate(interview_questions):
        #         system_prompt += f"{i+1}. {question}\n"
        
        # Additional context from scout prompt if available
        if context_data.get("scout_prompt"):
            system_prompt += f"\n\nAdditional guidance: {context_data.get('scout_prompt')}"
    else:
        logger.info("No context data available, using default prompt")
        # Fall back to the default prompt if no context data is available
        system_prompt += (
            "You should use short and concise responses, and avoiding usage of unpronouncable punctuation. "
            "You were created as a demo to showcase the capabilities of LiveKit's agents framework."
        )
    
    logger.debug(f"Built system prompt with {len(system_prompt)} characters")
    return system_prompt

def create_greeting(context_data):
    """Create a personalized greeting based on context."""
    logger.info("Creating greeting for participant")
    greeting = "Hey, how can I help you today?"
    if context_data.get("scout_name"):
        logger.info(f"Creating personalized greeting for {context_data.get('scout_name')}")
        greeting = f"Hello, I'm {context_data.get('scout_name')} from {context_data.get('company_name', 'the company')}. Thanks for joining this interview today. How are you doing?"
    logger.debug(f"Greeting: {greeting}")
    return greeting

