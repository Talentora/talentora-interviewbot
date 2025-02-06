import asyncio
import types
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app.bot.services.language_model import init_language_model
from app.bot.services.llm.types import InterviewConfig
from typing import Dict, Any

async def process_message(graph, user_input: str, state: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process a message through the interview graph."""
    try:
        # Create initial state if none exists
        if state is None:
            state = {}
        
        # Add input to state
        state["input"] = user_input
        
        # Process through graph
        result = graph.invoke(state)
        
        # Print the assistant's responses from the state
        messages = result.get("messages", [])
        if messages:
            # Only print messages that haven't been printed before
            new_messages = messages[len(state.get("messages", [])):] 
            for message in new_messages:
                if message["role"] == "assistant":
                    print(f"\nAssistant: {message['content']}")
        
        return result
    except Exception as e:
        print(f"\nError processing message: {str(e)}")
        return state


async def main():
    # Define a dummy configuration for the language model
    interview_config: InterviewConfig = {
        "bot_name": "TechRecruiter",
        "company_name": "Quantum Dynamics Software",
        "job_title": "Senior Backend Engineer",
        "company_context": "Quantum Dynamics Software is a rapidly growing tech company specializing in distributed systems and cloud infrastructure. Founded in 2019, we've grown to over 200 employees across 3 continents. Our core values emphasize innovation, technical excellence, and work-life balance. We're known for our microservices architecture platform that helps enterprises modernize their legacy systems.",
        "job_description": "We are seeking a Senior Backend Engineer to join our Core Platform team. The ideal candidate will have strong experience with Python, distributed systems, and cloud technologies (AWS/GCP). Key responsibilities include: designing and implementing scalable microservices, optimizing system performance, mentoring junior developers, and contributing to architectural decisions. Must have 5+ years of experience with backend development and a deep understanding of API design, database optimization, and container orchestration.",
        "interview_questions": [
            "Can you describe a challenging distributed systems problem you've solved?",
            "How do you approach API design for scalability?",
            "What strategies do you use for optimizing database performance?",
            "Tell me about your experience with microservices architecture",
            "How do you handle technical mentorship of junior developers?"
        ]
    }

    # Initialize the interview graph with the test config
    graph = init_language_model(interview_config)
    
    # Initialize state with the interview config
    current_state: Dict[str, Any] = {
        "messages": [],
        "next_question_index": 0,
        "interview_config": interview_config,
        "current_topic": None
    }

    # Test the graph with interactive input
    print("\nStarting technical interview. Type your responses below (type 'exit' to quit):")
    
    # Add initial greeting to messages
    greeting = f"Hello! I'm {interview_config['bot_name']} and I'll be conducting your technical interview today for {interview_config['company_name']} for the {interview_config['job_title']} position."
    print(f"\nAssistant: {greeting}")
    current_state["messages"].append({
        "role": "assistant",
        "content": greeting
    })
    
    # Start with the first question
    first_question = f"Let's begin. {interview_config['interview_questions'][0]}"
    print(f"\nAssistant: {first_question}")
    current_state["messages"].append({
        "role": "assistant",
        "content": first_question
    })

    while True:
        user_input = input("\nUser: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("\nAssistant: Thank you for participating in this interview. Have a great day!")
            break

        current_state = await process_message(graph, user_input, current_state)

if __name__ == "__main__":
    asyncio.run(main())