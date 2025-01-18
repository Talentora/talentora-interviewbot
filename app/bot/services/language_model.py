from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_anthropic import ChatAnthropic
from pipecat.processors.frameworks.langchain import LangchainProcessor
from app.core.config import settings
from pipecat.services.anthropic import AnthropicLLMService


def init_langchain_processor(interview_config: Dict[str, Any]) -> LangchainProcessor:
#     """Initialize the LangChain processor for handling the interview conversation."""
#     llm = ChatAnthropic(
#         model="claude-3-haiku-20240307",
#         anthropic_api_key=settings.ANTHROPIC_API_KEY,
#         temperature=0.7,
#         max_tokens=1024
#     )

#     # Create a more detailed system prompt using the interview config
#     system_prompt = f"""You are an AI interviewer named {interview_config['bot_name']} conducting a technical interview for {interview_config['company_name']}.
# Role: {interview_config['job_title']}

# Company Context: {interview_config['company_context']}

# Job Description: {interview_config['job_description']}

# Key Questions to Cover:
# {chr(10).join(f'- {q}' for q in interview_config['interview_questions'])}

# Instructions:
# - Be professional but friendly
# - Ask relevant follow-up questions to dig deeper into the candidate's responses
# - Keep your responses concise and focused
# - Give the candidate time to respond fully
# - Do not provide direct feedback on their answers during the interview
# - Ensure all key questions are covered naturally throughout the conversation
# - Stay focused on technical and professional aspects relevant to the role"""

#     interview_prompt = ChatPromptTemplate.from_messages(
#         messages=[
#             ("system", system_prompt),
#             MessagesPlaceholder(variable_name="history"),
#             ("human", "{input}")
#         ],
#         input_variables=["history", "input"]
#     )

#     chain = interview_prompt | llm
#     processor = LangchainProcessor(chain)
    
#     # Initialize history to empty list to avoid KeyError
#     processor._chain_input = {"history": [], "input": ""}
    
#     return processor

    llm_service = AnthropicLLMService(
        api_key=settings.ANTHROPIC_API_KEY,
        model="claude-3-5-sonnet-20240620",
        params=AnthropicLLMService.InputParams(
            temperature=0.7,
            max_tokens=1000
        )
    )

    return llm_service