from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_anthropic import ChatAnthropic
from pipecat.processors.frameworks.langchain import LangchainProcessor
from app.core.config import settings

def init_langchain_processor() -> LangchainProcessor:
    """Initialize the LangChain processor for handling the interview conversation."""
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.7,
        max_tokens=1024
    )

    interview_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an AI interviewer conducting a technical interview. 
Be professional but friendly. Ask relevant follow-up questions to dig deeper into the candidate's responses.
Keep your responses concise and focused. Give the candidate time to respond fully.
Do not provide direct feedback on their answers during the interview."""),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])

    chain = interview_prompt | llm
    return LangchainProcessor(chain) 