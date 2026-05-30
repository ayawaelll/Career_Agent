from typing import Annotated, TypedDict, Literal
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode

from agent.llm import get_llm
from agent.tools import (
    track_application, update_application_status, get_applications,
    add_planner_task, get_tasks, mark_task_done,
    add_to_google_calendar, schedule_interview_on_calendar,
    tailor_resume_to_jd,
)

# ── Tool sets ─────────────────────────────────────────────────────────────────
RESUME_TOOLS  = [tailor_resume_to_jd, add_to_google_calendar]
JOB_TOOLS     = [track_application, update_application_status, get_applications]
PLANNER_TOOLS = [add_planner_task, get_tasks, mark_task_done,
                 add_to_google_calendar, schedule_interview_on_calendar,
                 get_applications]

# ── Routing schema ────────────────────────────────────────────────────────────
class Route(BaseModel):
    next: Literal["resume", "jobs", "planner", "general"]

# ── System prompts ────────────────────────────────────────────────────────────
_TODAY = datetime.now().strftime("%B %d, %Y")

SUPERVISOR_PROMPT = f"Today's date is {_TODAY}.\n\n" + \
"""You are a routing supervisor for a personal AI assistant used by a \
final-year Computer Engineering student who is also actively job hunting.

Based on the user's latest message, decide which specialist agent should handle it:

- "resume"  — resume tailoring, writing bullets, matching experience to a job description
- "jobs"    — tracking job applications, updating pipeline status, listing companies applied to
- "planner" — managing tasks, uni deadlines, weekly planning, Google Calendar, stress or overwhelm
- "general" — greetings, meta questions, or anything that doesn't clearly fit the above

Return only the routing decision. Do not answer the user's question."""

RESUME_PROMPT = """You are a resume specialist for a final-year Computer Engineering student \
applying to AI engineering roles. Help tailor resume bullet points to specific job descriptions \
using the user's uploaded master resume. Use tailor_resume_to_jd to retrieve and rewrite \
relevant bullets. Be concise and output-focused."""

JOB_PROMPT = f"Today's date is {_TODAY}.\n\n" + \
"""You are a job application tracker assistant. Help the user add, update, and \
review their job applications. Never assume which application a user is referring to. If the \
user mentions an interview, task, or update without specifying the company and role, always ask \
for clarification before calling any tool. Always confirm what you've done after using a tool."""

PLANNER_PROMPT = f"Today's date is {_TODAY}.\n\n" + \
"""You are a planner for a student juggling their final semester and an active \
job search. Help manage tasks, university deadlines, and weekly priorities. You can add tasks, \
list pending work, mark tasks done, and push events to Google Calendar. You can also pull the \
current job application list to factor open applications, upcoming interviews, and pending \
follow-ups into the user's weekly plan. When the user seems overwhelmed, acknowledge it first \
before jumping to solutions."""

GENERAL_PROMPT = f"Today's date is {_TODAY}.\n\n" + \
"""You are a helpful personal AI assistant for a final-year Computer Engineering \
student applying to AI engineering roles. Answer helpfully and concisely."""

# ── State ─────────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_feature: str  # set by supervisor: "resume" | "jobs" | "planner" | "general"

# ── Supervisor node ───────────────────────────────────────────────────────────
def supervisor_node(state: AgentState) -> AgentState:
    llm = get_llm().with_structured_output(Route)
    result = llm.invoke([SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"])
    return {"current_feature": result.next}

def route_from_supervisor(state: AgentState) -> str:
    return state["current_feature"]

# ── Specialist node factories ─────────────────────────────────────────────────
def _call_agent(prompt: str, tools: list):
    """Return a node function: LLM with the given tools bound."""
    def node(state: AgentState) -> AgentState:
        llm = get_llm().bind_tools(tools)
        response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
        return {"messages": [response]}
    return node

def _should_continue(tools_node: str):
    """Return a conditional-edge function that loops through tools_node or exits."""
    def fn(state: AgentState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "end"
    return fn

# ── General node (no tools) ───────────────────────────────────────────────────
def general_node(state: AgentState) -> AgentState:
    response = get_llm().invoke([SystemMessage(content=GENERAL_PROMPT)] + state["messages"])
    return {"messages": [response]}

# ── Graph ─────────────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor",    supervisor_node)
    graph.add_node("resume_agent",  _call_agent(RESUME_PROMPT,  RESUME_TOOLS))
    graph.add_node("resume_tools",  ToolNode(RESUME_TOOLS))
    graph.add_node("job_agent",     _call_agent(JOB_PROMPT,     JOB_TOOLS))
    graph.add_node("job_tools",     ToolNode(JOB_TOOLS))
    graph.add_node("planner_agent", _call_agent(PLANNER_PROMPT, PLANNER_TOOLS))
    graph.add_node("planner_tools", ToolNode(PLANNER_TOOLS))
    graph.add_node("general",       general_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", route_from_supervisor, {
        "resume":  "resume_agent",
        "jobs":    "job_agent",
        "planner": "planner_agent",
        "general": "general",
    })

    # Each specialist loops through its own tool node, then ends
    for agent_node, tools_node in [
        ("resume_agent",  "resume_tools"),
        ("job_agent",     "job_tools"),
        ("planner_agent", "planner_tools"),
    ]:
        graph.add_conditional_edges(agent_node, _should_continue(tools_node), {
            "tools": tools_node,
            "end":   END,
        })
        graph.add_edge(tools_node, agent_node)

    graph.add_edge("general", END)

    return graph.compile()


agent = build_graph()
