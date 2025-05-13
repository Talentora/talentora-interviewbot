import asyncio
from typing import Annotated, AsyncIterable
from livekit.agents import Agent, function_tool, RunContext, ModelSettings
from context import UserData, build_system_prompt
import logging
from flow import Node, NodeType
from logger_config import setup_logging
import json

logger = setup_logging()
rubric = """[Evaluation Rubric]
                        Score 3 - Excellent: fully answers every part; gives concrete, role-relevant examples; concise
                        Score 2 - Adequate: addresses question but lacks examples
                        Score 1 - Weak: vague, generic, off-topic, or contradicts itself
                        Score 0 - No answer / "I don't know"
                        If Score ≤ 1, call follow_up(...)"""



@function_tool(description=f"Evaluate the candidate's answer using this rubric: {rubric}, if the answer scores less than a 2, call this function. This function also provides a rationale parameter for you to state why the answer was too weak.")
async def follow_up(rationale: Annotated[str, "Why the answer was weak?"], context: RunContext[UserData]):
    logger.info(f"FlowQuestionAgent asking follow-up question...")
    await context.session.generate_reply(instructions=f"ask a follow-up question since the user's answer is not good enough, dive deeper into their response or the question, the rationale for the follow-up question is: {rationale}", tool_choice="none") 

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
        super().__init__(instructions=f"Keeping the following criteria for the question in mind: {self.node.criteria}, Please ask the applicant this question: {self.node.content}. Ensure the question is asked in a friendly and natural manner, and keep the flow of the conversation smooth and natural.", tools=[follow_up] if node.follow_up_toggle else [])
        
        
    async def on_enter(self): 
        await super().on_enter()
        logger.info(f"FlowQuestionAgent will ask predefined question: {self.node.content}")
        await self.session.generate_reply(instructions=f"Ask the applicant the following question: {self.node.content}")
    
    
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
        flow = self.session.userdata.flow
        
        if current_node.type == NodeType.END:
            logger.info("FlowBranchingAgent is at the end of the interview. handing off to EndInterviewAgent...")
            context.userdata.prev_agent = self
            return EndInterviewAgent()
        elif current_node.type == NodeType.START:
            logger.info("FlowBranchingAgent is at the start of the interview. handing off to FlowQuestionAgent...")
            #again, we know a question node will follow the start node
            context.userdata.prev_agent = self
            next_node = flow.get_node(flow.get_next_node_ids(current_node.id))
            return FlowQuestionAgent(next_node)
        elif current_node.type == NodeType.QUESTION:
            logger.info("FlowBranchingAgent is at a question node.")
            next_id = flow.get_next_node_ids(current_node.id)
            next_node = flow.get_node(next_id)
            if next_node.type == NodeType.QUESTION:
                logger.info("Next node is a question node. handing off to FlowQuestionAgent...")
                context.userdata.prev_agent = self
                return FlowQuestionAgent(next_node)
            else:
                logger.info("Next node is not a question node. handing off to FlowBranchingAgent...")
                context.userdata.prev_agent = self
                return FlowBranchingAgent(next_node)
    
        else: #node must be a branching node, handle choosing next node
            logger.info("FlowBranchingAgent is at a branching node.")
            next_node_ids = self.session.userdata.flow.get_next_node_ids(current_node.id)
            node_options = []
            valid_ids = []
            for node_id in next_node_ids:
                node = self.session.userdata.flow.get_node(node_id)
                if node is None:
                    logger.warning(f"Node with id {node_id} is None. Skipping.")
                    continue  # Skip invalid nodes
                node_options.append({
                    "id": node_id,
                    "content": node.content,
                    "type": node.type
                })
                valid_ids.append(node_id)
            logger.info(f"Node options: {node_options}")
            
            # Format the options in a numbered list to make IDs more visually distinct
            formatted_options = "\n".join([
                f"OPTION {i+1}:\n  ID: {option['id']}\n  Content: {option['content']}\n  Type: {option['type']}"
                for i, option in enumerate(node_options)
            ])
            
            result = await self.session.generate_reply(instructions = (
                "Based on the context of the conversation, select ONE node from the following options:\n\n"
                f"{formatted_options}\n\n"
                "YOUR TASK: Output ONLY the ID of the chosen node. Nothing else. No explanations.\n"
                "Return ONLY a UUID string like: '7607d4b6-0f29-49a6-84be-b8042be1556e'\n"
                "DO NOT return the content text or any other information.\n"
                "VALID OUTPUT EXAMPLE: 7607d4b6-0f29-49a6-84be-b8042be1556e\n"
                "INVALID OUTPUT EXAMPLE: I choose option 1 with content 'Why do you want to work at this company?'\n"
                "Return ONLY the ID."
            ), tool_choice="none")
            
            msg = result.chat_message
            fall_back_node = self.session.userdata.flow.get_node(node_options[0]["id"])
            
            if not msg or not msg.text_content:
                logger.warning("No message or empty content returned from LLM. Using fallback node.")
                logger.info(f"Fallback question selected...")
                context.userdata.prev_agent = self
                return FlowQuestionAgent(fall_back_node)
            
            # Get the raw response and try to extract a valid ID
            raw_response = msg.text_content.strip()
            logger.info(f"Raw LLM response: {raw_response}")
            
            # Try to extract just the ID by checking if any valid ID is present in the response
            chosen_id = None
            
            # First check if the exact response matches a valid ID
            if raw_response in valid_ids:
                chosen_id = raw_response
            else:
                # Try to find any valid ID in the response
                for node_id in valid_ids:
                    if node_id in raw_response:
                        chosen_id = node_id
                        logger.info(f"Extracted ID '{node_id}' from response")
                        break
            
            if not chosen_id:
                # Check for UUID pattern as a last resort
                import re
                uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                match = re.search(uuid_pattern, raw_response)
                if match and match.group(0) in valid_ids:
                    chosen_id = match.group(0)
                    logger.info(f"Extracted UUID '{chosen_id}' from response")
            
            if chosen_id and chosen_id in valid_ids:
                logger.info(f"LLM selected next node ID: {chosen_id}")
                next_node = self.session.userdata.flow.get_node(chosen_id)
                if next_node:
                    logger.info(f"LLM selected next question: {next_node.content}, handing off to FlowQuestionAgent...")
                    context.userdata.prev_agent = self
                    return FlowQuestionAgent(next_node)
            
            # If we get here, we couldn't extract a valid ID
            logger.warning(f"Could not extract valid node ID from LLM response: {raw_response}")
            logger.info(f"Fallback question selected...")
            context.userdata.prev_agent = self
            return FlowQuestionAgent(fall_back_node)
    
        
        
        
        
        
        
        
        
        
        
        
    
            
        
        # Get information about each possible next nod
 
        

    
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
        super().__init__(instructions="")
    
    async def on_enter(self):
        await super().on_enter()
        logger.info("EndInterviewAgent thanking candidate and disconnecting...")
        await self.session.generate_reply(instructions="", tool_choice={"type": "function", "function": {"name": "finish"}})
        
    @function_tool(description="Call this function to end the interview.")
    async def finish(self, context: RunContext[UserData]):
        logger.info("EndInterviewAgent ending interview...")
        await self.session.generate_reply(instructions="Continuing the flow of the conversation smoothly, thank candidate for their time, handle ending the interview in a natural and smooth manner.", allow_interruptions=False)
        await asyncio.sleep(5)
        await self.session.aclose()

