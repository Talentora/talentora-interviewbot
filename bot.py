import asyncio
import os
import sys
import json
from typing import Dict, Any
from pathlib import Path

import aiohttp
from loguru import logger
from dotenv import load_dotenv

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator,
)
from pipecat.processors.frameworks.langchain import LangchainProcessor
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_anthropic import ChatAnthropic

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

message_store = {}

class ConfigurationError(Exception):
    """Raised when there are configuration-related errors."""
    pass

class InterviewBot:
    DEFAULT_CONFIG = {
        'voice_id': '79a125e8-cd45-4c13-8a67-188112f4dd22',  # Default voice
        'max_duration': 300,
        'interview_config': {
            'bot_name': 'Interview Bot',
            'job_title': 'Software Engineer',
            'company_name': 'Tech Company',
            'job_description': 'General software engineering position',
            'company_context': 'Technology company',
            'interview_questions': ['Tell me about yourself']
        }
    }
    
    REQUIRED_ENV_VARS = {
        'DAILY_ROOM_URL': 'Daily.co room URL',
        'DAILY_TOKEN': 'Daily.co API token',
        'CARTESIA_API_KEY': 'Cartesia API key',
        'ANTHROPIC_API_KEY': 'Anthropic API key'
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = self._merge_config(self.DEFAULT_CONFIG, config)
        self.voice_id = self.config.get('voice_id')
        self.bot_profile = self.config.get('bot_profile')
        self.interview_config = self.config.get('interview_config', {})
        
    @staticmethod
    def _merge_config(default: Dict, custom: Dict) -> Dict:
        """Recursively merge custom config with default config."""
        merged = default.copy()
        for key, value in custom.items():
            if isinstance(value, dict) and key in merged:
                merged[key] = InterviewBot._merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    @classmethod
    def validate_environment(cls) -> None:
        """Validate that all required environment variables are set."""
        missing_vars = []
        for var, description in cls.REQUIRED_ENV_VARS.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            raise ConfigurationError(
                "Missing required environment variables:\n" + 
                "\n".join(f"- {var}" for var in missing_vars)
            )

    def get_system_prompt(self) -> str:
        return (
            f"You are {self.interview_config.get('bot_name')}, an AI interviewer conducting "
            f"an interview for the {self.interview_config.get('job_title')} position at "
            f"{self.interview_config.get('company_name')}.\n\n"
            f"Job Description: {self.interview_config.get('job_description')}\n\n"
            f"Company Context: {self.interview_config.get('company_context')}\n\n"
            "Interview Guidelines:\n"
            "- Be authentic and present like a human interviewer\n"
            "- If you don't know something or need clarification, ask the candidate\n"
            "- Focus on understanding the candidate's skills, motivations, and potential\n"
            "- Use the prepared questions as a guide, but be flexible\n"
            "- Pay attention to not just what is said, but how it is said\n\n"
            f"Prepared Interview Questions: {self.interview_config.get('interview_questions')}"
        )

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in message_store:
            message_store[session_id] = ChatMessageHistory()
        return message_store[session_id]

    async def run(self):
        async with aiohttp.ClientSession() as session:
            transport = DailyTransport(
                room_url=os.getenv("DAILY_ROOM_URL"),
                token=os.getenv("DAILY_TOKEN"),
                bot_name=self.interview_config.get('bot_name', 'Interview Bot'),
                params=DailyParams(
                    audio_out_enabled=True,
                    transcription_enabled=True,
                    vad_enabled=True,
                    vad_analyzer=SileroVADAnalyzer(),
                ),
            )

            tts = CartesiaTTSService(
                api_key=os.getenv("CARTESIA_API_KEY"),
                voice_id=self.voice_id,
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", self.get_system_prompt()),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ])

            # Use Anthropic's Claude model as specified in the config
            chain = prompt | ChatAnthropic(
                model="claude-3-sonnet-20240229",
                temperature=0.7,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
            )

            history_chain = RunnableWithMessageHistory(
                chain,
                self.get_session_history,
                history_messages_key="chat_history",
                input_messages_key="input",
            )
            
            lc = LangchainProcessor(history_chain)
            tma_in = LLMUserResponseAggregator()
            tma_out = LLMAssistantResponseAggregator()

            pipeline = Pipeline([
                transport.input(),
                tma_in,
                lc,
                tts,
                transport.output(),
                tma_out,
            ])

            task = PipelineTask(pipeline, PipelineParams(
                allow_interruptions=True,
                max_duration=self.config.get('max_duration', 300)
            ))

            @transport.event_handler("on_first_participant_joined")
            async def on_first_participant_joined(transport, participant):
                lc.set_participant_id(participant["id"])
                messages = [({"content": "Hello! I'll be conducting your interview today. Could you please introduce yourself?"})]
                await task.queue_frames([LLMMessagesFrame(messages)])

            runner = PipelineRunner()
            await runner.run(task)

async def load_config() -> Dict[str, Any]:
    """Load configuration from file with fallback to default."""
    config_path = Path('interview_config.json')
    
    try:
        if config_path.exists():
            logger.info(f"Loading configuration from {config_path}")
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Configuration file {config_path} not found, using default configuration")
            return {}
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {config_path}: {e}")
        raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        raise ConfigurationError(f"Failed to load configuration: {e}")

async def main():
    try:
        # Load environment variables
        load_dotenv(override=True)
        
        # Validate environment variables
        InterviewBot.validate_environment()
        
        # Load configuration with fallback to defaults
        config = await load_config()
        
        # Initialize and run the bot
        bot = InterviewBot(config)
        await bot.run()
        
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
