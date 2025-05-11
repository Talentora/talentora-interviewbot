from typing import Annotated, AsyncIterable
from livekit.agents import Agent, function_tool, RunContext, ModelSettings
from context import UserData, build_system_prompt
import logging
from flow import Node
from logger_config import setup_logging
import json

logger = setup_logging()
rubric = """[Evaluation Rubric]
                        Score 3 - Excellent: fully answers every part; gives concrete, role-relevant examples; concise
                        Score 2 - Adequate: addresses question but lacks examples
                        Score 1 - Weak: vague, generic, off-topic, or contradicts itself
                        Score 0 - No answer / "I don't know"
                        If Score ≤ 1, call follow_up(...)"""

class BaseAgent(Agent):
    async def on_enter(self) -> None:
        agent_name = self.__class__.__name__
        logger.info(f"Entering {agent_name}")

        userdata: UserData = self.session.userdata

        chat_ctx = self.chat_ctx.copy()

        if userdata.prev_agent:
            items_copy = self._truncate_chat_ctx(
                userdata.prev_agent.chat_ctx.items, keep_function_call=True
            )
            existing_ids = {item.id for item in chat_ctx.items}
            items_copy = [item for item in items_copy if item.id not in existing_ids]
            chat_ctx.items.extend(items_copy)

        chat_ctx.add_message(role="system", content=self.instructions)

        await self.update_chat_ctx(chat_ctx)

    def _truncate_chat_ctx(
        self,
        items: list,
        keep_last_n_messages: int = 6,
        keep_system_message: bool = False,
        keep_function_call: bool = False,
    ) -> list:
        """Truncate the chat context to keep the last n messages."""
        def _valid_item(item) -> bool:
            if not keep_system_message and item.type == "message" and item.role == "system":
                return False
            if not keep_function_call and item.type in ["function_call", "function_call_output"]:
                return False
            return True

        new_items = []
        for item in reversed(items):
            if _valid_item(item):
                new_items.append(item)
            if len(new_items) >= keep_last_n_messages:
                break
        new_items = new_items[::-1]

        while new_items and new_items[0].type in ["function_call", "function_call_output"]:
            new_items.pop(0)

        return new_items



class GreeterAgent(BaseAgent):
    def __init__(
        self, 
        context_data: dict,
        initial_node: Node
    ):
        instructions = build_system_prompt(context_data) 
        super().__init__(instructions=instructions)
        logger.info(f"GreeterAgent initialized")
        self.initial_node = initial_node
        
    async def on_enter(self):
        await super().on_enter()
        await self.session.generate_reply(instructions="Introduce yourself, and ask the user if they are ready to start the interview.")
    
    @function_tool(description="Call this function if the user confirms they are ready to start the interview.",)
    async def confirm_ready(self, context: RunContext[UserData]):
        logger.info(f"GreeterAgent handing off to FlowBranchingAgent...")
        context.userdata.prev_agent = self
        return FlowBranchingAgent(self.initial_node)
    
    @function_tool(description="Call this function if the user confirms they want to cancel the interview, or if they are not ready to start the interview.")
    async def confirm_cancel(self, context: RunContext[UserData]):
        logger.info(f"GreeterAgent handing off to EndInterviewAgent...")
        context.userdata.prev_agent = self
        return EndInterviewAgent()
    

class FlowQuestionAgent(BaseAgent):
    def __init__(self, node: Node):
        logger.info(f"FlowQuestionAgent initialized...")
        self.node = node
        super().__init__(instructions=f"")
        
        
    async def on_enter(self): 
        await super().on_enter()
        logger.info(f"FlowQuestionAgent will ask predefined question: {self.node.content}")
        await self.session.generate_reply(instructions=f"Ask the applicant the following question: {self.node.content}, with the following criteria: {self.node.criteria}, remember to stay friendly, and answer questions if you know the answer")
    
 
    @function_tool(description=f"Evaluate the candidate's answer using this rubric: {rubric}, if the answer scores less than a 2, call this function. This function also provides a rationale parameter for you to state why the answer was too weak.")
    async def follow_up(self, rationale: Annotated[str, "Why the answer was weak?"], context: RunContext[UserData]):
        logger.info(f"FlowQuestionAgent asking follow-up question...")
        await self.session.generate_reply(instructions=f"ask a follow-up question since the user's answer is not good enough, dive deeper into their response or the question, the rationale for the follow-up question is: {rationale}", tool_choice="none") 

    
    @function_tool(description="Call this function if the user's answer is satisfactory, transition to the next node, only use this function if the user did answer the question, but their answer was satisfactory")
    async def transition(self, context: RunContext[UserData]):
        logger.info(f"FlowQuestionAgent handing off to FlowBranchingAgent...")
        context.userdata.prev_agent = self
        return FlowBranchingAgent(self.node)  # transfer

class FlowBranchingAgent(BaseAgent):
    def __init__(self, node: Node):
        self.node = node
        super().__init__(instructions=f"You are a transtioning agent. You have access to a function tool that will allow you to transition to the next agent based on the conversation flow and candidate's response. Please call the transition function to determine which agent & question to transition to next.")
    
    async def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings):  
        """Override the default TTS node to skip audio generation."""  
        # This is an empty generator that doesn't produce any audio frames  
        # but still consumes the text input to prevent blocking  
        async for _ in text:  
            pass  
        # Empty generator that yields nothing  
        if False:  # This never executes but defines return type  
            yield rtc.AudioFrame()
            
            
    async def on_enter(self):
        await super().on_enter()
        logger.info(f"FlowBranchingAgent initialized...")
        await self.session.generate_reply(instructions="Call the transition function to determine which agent & question to transition to next.", tool_choice={"type": "function", "function": {"name": "transition"}})
        
        
    
    @function_tool(description="Immediately call this function after your initialization to determine which agent to transition to next.", name="transition")
    async def transition(self, context: RunContext[UserData]):
        current_node = self.node
        next_node_ids = self.session.userdata.flow.get_next_node_ids(current_node.id)
        
        # If no next nodes, end the interview
        if not next_node_ids:
            logger.info("No next nodes found. Ending interview.")
            context.userdata.prev_agent = self
            return EndInterviewAgent()
            
        # If only one next node, no need for LLM decision
        if len(next_node_ids) == 1:
            next_node = self.session.userdata.flow.get_node(next_node_ids[0])
            if next_node is None:
                logger.warning("Next node is None. Ending interview.")
                context.userdata.prev_agent = self
                return  EndInterviewAgent()  # Handle case where node doesn't exist
            logger.info(f"Only one next node available. handing off to FlowQuestionAgent...")
            context.userdata.prev_agent = self
            return  FlowQuestionAgent(next_node)
        
        # Get information about each possible next node
        node_options = []
        for node_id in next_node_ids:
            node = self.session.userdata.flow.get_node(node_id)
            if node is None:
                logger.warning(f"Node with id {node_id} is None. Skipping.")
                continue  # Skip invalid nodes
            node_options.append({
                "id": node_id,
                "content": node.content,
                "criteria": node.criteria
            })
            
        if not node_options:
            logger.warning("No valid node options for branching. Ending interview.")
            context.userdata.prev_agent = self
            return EndInterviewAgent()
        
        result = await self.session.generate_reply(instructions=f"Based on the following node options: {node_options}, which question should be asked next? output ONLY the ID of the node that should be asked next", tool_choice="none")
        msg = result.chat_message
        fall_back_node = self.session.userdata.flow.get_node(node_options[0]["id"]) # use this node if the LLM doesn't return a valid node id
        
        if not msg: #no message at all - handle this case 
            logger.warning("No message returned from LLM. Using fallback node.")
            logger.info(f"Fallback question selected...")
            context.userdata.prev_agent = self
            return FlowQuestionAgent(fall_back_node)
        elif not msg.text_content: #no text content - handle this case 
            logger.warning("No text content in LLM message. Using fallback node.")
            logger.info(f"Fallback question selected...")
            context.userdata.prev_agent = self
            return FlowQuestionAgent(fall_back_node)
        else:
            chosen_id = msg.text_content.strip()
            next_node = self.session.userdata.flow.get_node(chosen_id)
            if next_node:
                logger.info(f"LLM selected next question: {next_node.content}, handing off to FlowQuestionAgent...")
                context.userdata.prev_agent = self
                return FlowQuestionAgent(next_node)

        # fallback…
        logger.warning("LLM chose invalid node id. Using fallback node.")
        logger.info(f"Fallback question selected...")
        context.userdata.prev_agent = self
        return FlowQuestionAgent(fall_back_node)
    
#TODO: implement custom question agent
# class CustomQuestionAgent(BaseAgent):
#     def __init__(self, tts):
#         super().__init__(instructions="Generate and ask a custom question based on resume, job, and prior answers.", tts=tts)

#     @function_tool()
#     async def ask_custom(self, _, context: RunContext[UserData]):
#         # use LLM + userdata.answers + userdata.context_data to craft a tailored question
#         return userdata.agents["end_interview"]


class EndInterviewAgent(BaseAgent):
    def __init__(self):
        super().__init__(instructions="Thank candidate, based on chat history the session could have ended due to reaching the end of the interview, or the user decided to end the interview. Thank them for their time, and disconnect.")
    
    async def on_enter(self):
        await super().on_enter()
        logger.info("EndInterviewAgent thanking candidate and disconnecting...")
        await self.session.generate_reply(instructions="End the interview, thank the candidate for their time, and disconnect.")
    @function_tool()
    async def finish(self, context: RunContext[UserData]):
        logger.info("EndInterviewAgent ending interview...")
        await self.session.say("Thank you for your time. We'll be in touch shortly.")
        return None  # no further agent