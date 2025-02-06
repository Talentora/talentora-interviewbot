from typing import Optional
from app.bot.services.llm.types import InterviewConfig, InterviewState
from app.bot.services.llm.graph import create_interview_graph
from loguru import logger
from langgraph.graph import StateGraph

def init_language_model(
    interview_config: Optional[InterviewConfig] = None
) -> StateGraph:
    """Initialize the language model graph for the interview process.
    
    Args:
        interview_config: Optional configuration for the interview. If not provided,
                        a basic test configuration will be used.
    
    Returns:
        A compiled StateGraph that can process the interview conversation.
    """
    logger.debug("Initializing language model components")
    
    if interview_config:
        logger.debug("Using interview config")
        graph = create_interview_graph(interview_config)
    else:
        # Create a basic conversation graph for testing
        logger.debug("Creating basic processor")
        basic_config = InterviewConfig(
            bot_name="Assistant",
            company_name="Test Company",
            job_title="Test Role",
            company_context="Test context",
            job_description="Test description",
            interview_questions=["How can I help you today?"]
        )
        graph = create_interview_graph(basic_config)
    
    logger.debug("Graph creation completed")
    return graph