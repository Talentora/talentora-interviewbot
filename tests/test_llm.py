import pytest
from app.bot.services.language_model import init_langchain_processor

@pytest.fixture
def interview_config():
    return {
        "bot_name": "TechBot",
        "company_name": "Test Company",
        "job_title": "Senior Software Engineer",
        "company_context": "Leading tech company focused on innovation",
        "job_description": "Looking for experienced software engineers",
        "interview_questions": [
            "Tell me about your experience with Python",
            "What's your approach to testing?",
            "How do you handle technical challenges?"
        ]
    }

async def test_llm_response(interview_config):
    # Initialize the LLM service and aggregators
    llm_service, user_aggregator, assistant_aggregator = init_langchain_processor(interview_config)
    
    # Test messages
    messages = [
        "Hi, I'm here for the interview",
        "I have 5 years of experience with Python",
        "I believe in thorough testing using pytest"
    ]
    
    # Process messages and get responses
    responses = []
    for message in messages:
        # Aggregate user message
        await user_aggregator.process(message)
        
        # Get LLM response
        response = await llm_service.process()
        
        # Aggregate assistant response
        await assistant_aggregator.process(response)
        
        responses.append(response)
    
    # Basic assertions
    assert len(responses) == len(messages)
    assert all(isinstance(response, str) for response in responses)
    assert all(len(response) > 0 for response in responses)


if __name__ == "__main__":
    pytest.main([__file__])