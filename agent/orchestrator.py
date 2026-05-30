from typing import Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agent.llm import get_llm
from agent.tools import get_tools
from langgraph.prebuilt import ToolNode

SYSTEM_PROMPT = """You are a personal AI assistant for a final-year Computer Engineering student 
applying to AI engineering roles. You help manage:

1. Job applications — tracking, tailoring resumes, interview prep, scheduling interviews in Google Calendar
2. University work — assignments, exams, project meetings (can add deadlines to Google Calendar)
3. Weekly planning — balancing both worlds intelligently  
4. Stress & mental load — check-ins, prioritization, reframing

You have access to tools: job tracker (add/update/list applications), planner (add/list tasks and deadlines).

Always be concise, practical, and encouraging. When the user seems overwhelmed, acknowledge it first 
before jumping to solutions. You know they're a Computer Engineering student applying for AI roles.

Today's context: Final semester of university + active job search. High stress period."""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_feature: str  # "job_tracker" | "resume" | "interview" | "planner" | "stress"


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"


def call_model(state: AgentState) -> AgentState:
    llm = get_llm().bind_tools(get_tools())
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def build_graph():
    tool_node = ToolNode(get_tools())

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    return graph.compile()


agent = build_graph()
