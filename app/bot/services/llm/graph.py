from typing import Dict, Any, Union
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from .types import InterviewConfig, InterviewState
from .model import init_groq_processor
from .prompt import create_interview_prompt
from loguru import logger

def should_ask_next_question(state: InterviewState) -> bool:
    """Determine if we should move to the next interview question."""
    return (
        state["next_question_index"] < len(state["interview_config"]["interview_questions"]) and
        len(state["messages"]) >= 2  # At least one exchange has happened
    )

def get_next_question(state: InterviewState) -> str:
    """Get the next question from the interview questions list."""
    questions = state["interview_config"]["interview_questions"]
    if state["next_question_index"] < len(questions):
        return questions[state["next_question_index"]]
    return ""

def should_end_interview(state: Dict[str, Any]) -> bool:
    """Check if we should end the interview."""
    # Only end if we've gone through all questions and had at least one exchange
    return (
        state.get("next_question_index", 0) >= len(state["interview_config"]["interview_questions"]) and
        len(state.get("messages", [])) > len(state["interview_config"]["interview_questions"]) * 2
    )

def create_interview_graph(config: InterviewConfig) -> StateGraph:
    """Create the interview graph with states and transitions."""
    
    # Initialize the model and prompt
    model = init_groq_processor()
    prompt = create_interview_prompt(config)
    
    # Create the chain for processing messages
    chain = prompt | model | StrOutputParser()
    
    # Create the graph
    workflow = StateGraph(InterviewState)
    
    # Define the main interview node
    def interview_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and update the interview state."""
        try:
            # Initialize state if needed
            if not state.get("messages"):
                state["messages"] = []
            if "next_question_index" not in state:
                state["next_question_index"] = 0
            if not state.get("interview_config"):
                state["interview_config"] = config
            if "current_topic" not in state:
                state["current_topic"] = None
            
            # Get the input message from state
            input_message = state.get("input", "")
            logger.debug(f"Processing input: {input_message}")
            
            # Add the user message to state
            state["messages"].append({"role": "user", "content": input_message})
            
            # Generate bot response
            messages = [{"role": m["role"], "content": m["content"]} for m in state["messages"]]
            response = chain.invoke({"messages": messages, "input": input_message})
            logger.debug(f"Generated response: {response}")
            
            # Add bot response to state
            state["messages"].append({"role": "assistant", "content": response})
            
            # Check if we should move to next question
            if should_ask_next_question(state):
                state["next_question_index"] += 1
                next_question = get_next_question(state)
                if next_question:
                    state["messages"].append({
                        "role": "assistant",
                        "content": f"\nLet's move on to the next topic. {next_question}"
                    })
            
            return state
        except Exception as e:
            logger.error(f"Error in interview node: {str(e)}")
            raise
    
    # Define conditional edges
    def decide_next(state: Dict[str, Any]) -> str:
        """Decide whether to continue or end the interview."""
        if should_end_interview(state):
            logger.info("Interview complete, ending session")
            return END
        return "interview"
    
    # Add nodes and edges
    workflow.add_node("interview", interview_node)
    workflow.set_entry_point("interview")
    workflow.add_conditional_edges("interview", decide_next)
    
    # Compile the graph
    return workflow.compile() 