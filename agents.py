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
    
    @function_tool(description="Call this function if the interviewee is not being cooperative, or if they are not behaving appropriately, the argument is the rationale for the termination of the interview")
    async def end_interview_prematurely(self, rationale: Annotated[str, "What is the reason for the termination of the interview?"], context: RunContext[UserData]):
        logger.info(f"Shutting down interview for the following reason: {rationale}")
        await context.session.generate_reply(instructions=f"You have chosen to end the interview, inform the candidate of this irreversible decision.", allow_interruptions=False) 
        await context.session.aclose()
        return None



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
        logger.info(f"FlowQuestionAgent will ask predefined question: {self.node.content}, remember not to answer any questions from the user if the information was not explicitly provided to you, make no assumptions if you do not have the information, and do not answer questions that are outside the topic of the interview.")
        await self.session.generate_reply(instructions=f"Ask the applicant the following question: {self.node.content}")
    
    
    @function_tool(description="Call this function if the user's answer is satisfactory, transition to the next node, only use this function if the user did answer the question, but their answer was satisfactory")
    async def transition(self, context: RunContext[UserData]):
        logger.info(f"FlowQuestionAgent handing off to FlowBranchingAgent...")
        context.userdata.prev_agent = self
        return FlowBranchingAgent(self.node)  # transfer

class FlowBranchingAgent(BaseAgent):
    def __init__(self, node: Node):
        self.node = node
        super().__init__(instructions=f"You are a transitioning agent. Your job is to select the next question or step in the interview flow. When presented with multiple options, review each option carefully and select the most appropriate one by providing ONLY the option NUMBER (e.g., 1, 2, 3). Do not provide explanations or additional text with your selection.")
    
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
        await self.session.generate_reply(instructions="Call the transition function to determine which node & question to transition to next. You will be presented with numbered options - select the most appropriate one by its number.", tool_choice={"type": "function", "function": {"name": "transition"}})

        
    
    @function_tool(description="Call this function to determine which question to ask next. You will be given a numbered list of options. Select the most appropriate option by providing ONLY its number (1, 2, 3, etc).", name="transition")
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
            
            # Instead of showing the full node IDs, use numbers for selection
            node_display = ""
            for i, option in enumerate(node_options):
                node_display += f"OPTION {i+1}: {option['content']} (Type: {option['type']})\n"
            
            # Create a mapping from option number to node ID
            option_to_id = {i+1: option["id"] for i, option in enumerate(node_options)}
            
            result = await self.session.generate_reply(instructions = (
                "INSTRUCTIONS:\n"
                "Based on the conversation context, you must select exactly ONE option from the following list.\n\n"
                f"{node_display}\n"
                "1. RESPOND WITH ONLY A SINGLE NUMBER (e.g., 1, 2, 3, etc.)\n"
                "2. DO NOT include any explanation, text, or quotes\n"
                "3. DO NOT repeat the question content\n"
                "4. Example of valid response: 1\n"
                "5. Example of invalid response: 'Option 1 seems best'\n"
                "YOUR RESPONSE:"
            ), tool_choice="none")
            
            msg = result.chat_message
            fall_back_node = self.session.userdata.flow.get_node(node_options[0]["id"])
            
            if not msg or not msg.text_content:
                logger.warning("No message or empty content returned from LLM. Using fallback node.")
                logger.info(f"Fallback question selected...")
                context.userdata.prev_agent = self
                return FlowQuestionAgent(fall_back_node)
            
            # Try to extract an option number from the response
            raw_response = msg.text_content.strip()
            logger.info(f"Raw LLM response: {raw_response}")
            
            # Extract just the number - remove any non-digit characters
            import re
            number_pattern = re.compile(r'\d+')
            matches = number_pattern.findall(raw_response)
            
            if matches:
                selected_number = int(matches[0])
                # Check if the selected number is valid
                if selected_number in option_to_id:
                    chosen_id = option_to_id[selected_number]
                    logger.info(f"LLM selected option {selected_number}, which corresponds to node ID: {chosen_id}")
                    next_node = self.session.userdata.flow.get_node(chosen_id)
                    if next_node:
                        logger.info(f"LLM selected next question: {next_node.content}, handing off to FlowQuestionAgent...")
                        context.userdata.prev_agent = self
                        return FlowQuestionAgent(next_node)
                else:
                    logger.warning(f"Selected number {selected_number} is not a valid option. Using fallback node.")
            else:
                logger.warning(f"Could not extract a number from LLM response: {raw_response}")
            
            # If we get here, we couldn't extract a valid option
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
        super().__init__(instructions="Continuing the flow of the conversation smoothly, thank candidate for their time, handle ending the interview in a natural and smooth manner.")
    
    async def on_enter(self):
        await super().on_enter()
        logger.info("EndInterviewAgent thanking candidate and disconnecting...")
        await self.session.generate_reply(instructions="", tool_choice={"type": "function", "function": {"name": "finish"}})
        
    @function_tool(description="Call this function to end the interview.")
    async def finish(self, context: RunContext[UserData]):
        logger.info("EndInterviewAgent ending interview...")
        await self.session.generate_reply(instructions="end the interview", allow_interruptions=False)
        await self.session.aclose()

