from typing import Dict, Any, Tuple, Optional, List
from loguru import logger
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pipecat.processors.frameworks.langchain import LangchainProcessor  # type: ignore
from app.core.config import settings
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from pipecat.processors.aggregators.llm_response import ( # type: ignore
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator
)

# Type the message store
from typing import TypedDict
from pydantic import SecretStr

# Use window memory to limit chat history size
from langchain.memory import ConversationBufferWindowMemory

message_store: Dict[str, ChatMessageHistory] = {}

class InterviewConfig(TypedDict):
    bot_name: str
    company_name: str
    job_title: str
    company_context: str
    job_description: str
    interview_questions: List[str]

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in message_store:
        # Only keep last 4 message pairs in memory
        message_store[session_id] = ChatMessageHistory()
    return message_store[session_id]

def init_groq_processor() -> BaseChatModel:
    """Initialize the Groq processor with minimal settings."""
    logger.debug("Initializing Groq processor")
    model = ChatGroq(
        model_name="gemma2-9b-it",
        temperature=0.7,
        max_tokens=500, # Reduced max tokens
        groq_api_key=settings.GROQ_API_KEY,
        timeout=25
    )
    logger.debug("Groq processor initialized")
    return model

def init_anthropic_processor() -> BaseChatModel:
    """Initialize the Anthropic processor."""
    logger.debug("Initializing Anthropic processor")
    model = ChatAnthropic(
        model_name="claude-3-5-sonnet-latest",
        temperature=0.7,
        max_tokens=500,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        timeout=25
    )
    logger.debug("Anthropic processor initialized")
    return model

def init_openai_processor() -> BaseChatModel:
    """Initialize the OpenAI processor."""
    logger.debug("Initializing OpenAI processor")
    model = ChatOpenAI(
        model_name="gpt-4o-mini-2024-07-18",
        temperature=0.7,
        max_tokens=500,
        openai_api_key=settings.OPENAI_API_KEY,
        timeout=25
    )
    logger.debug("OpenAI processor initialized")
    return model

def init_langchain_processor(interview_config: InterviewConfig) -> LangchainProcessor:
    """Initialize LangChain processor with simplified prompt."""
    llm: BaseChatModel = init_openai_processor()

    # Simplified system prompt
    system_prompt: str = f"""You are {interview_config['bot_name']}, interviewing for {interview_config['job_title']} at {interview_config['company_name']}.
    Context: {interview_config['company_context'][:200]}
    Role: {interview_config['job_description'][:300]}
    Questions: {', '.join(interview_config['interview_questions'])}
    
    Be professional, ask one question at a time, and follow up naturally. No action descriptions or LLM references."""

    interview_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])

    chain = interview_prompt | llm
    history_chain = RunnableWithMessageHistory(
        chain,
        get_session_history,
        history_messages_key="chat_history",
        input_messages_key="input",
    )
    processor = LangchainProcessor(history_chain)
    processor.set_participant_id("assistant")
    return processor

def init_language_model(
    interview_config: Optional[InterviewConfig] = None
) -> Tuple[LangchainProcessor, LLMUserResponseAggregator, LLMAssistantResponseAggregator]:
    """Initialize language model components with minimal configuration."""
    logger.debug("Initializing language model components")
    
    if interview_config:
        processor = init_langchain_processor(interview_config)
    else:
        llm = init_groq_processor()
        basic_prompt = ChatPromptTemplate.from_messages([
            ("system", "Be helpful and concise."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        chain = basic_prompt | llm
        history_chain = RunnableWithMessageHistory(
            chain,
            get_session_history,
            history_messages_key="chat_history",
            input_messages_key="input",
        )
        processor = LangchainProcessor(history_chain)
        processor.set_participant_id("assistant")
    
    user_aggregator = LLMUserResponseAggregator()
    assistant_aggregator = LLMAssistantResponseAggregator()
    
    return processor, user_aggregator, assistant_aggregator