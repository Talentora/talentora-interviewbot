from typing import Annotated
from typing_extensions import TypedDict
import os
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
from IPython.display import Image, display
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("TkAgg")  # or 'Qt5Agg'

load_dotenv()

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

api_key = os.getenv("ANTHROPIC_API_KEY")
print("API KEY", api_key)
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    api_key=api_key,
)


def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}


# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()

# graph.run()

try:
    img_data = graph.get_graph().draw_mermaid_png()
    plt.imshow(plt.imread(img_data))  # Read and display the image
    plt.axis('off')  # Hide axes
    plt.show()       # Show the plot
except Exception:
    # This requires some extra dependencies and is optional
    pass