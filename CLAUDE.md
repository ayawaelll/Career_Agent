# Project context for Claude Code

## What this is
A personal AI agent built by a final-year Computer Engineering student applying for AI engineering roles.
It serves two purposes: (1) actually useful daily tool to survive final semester + job search, and
(2) a portfolio project to showcase in interviews and on LinkedIn.

## The user
- Final-year Computer Engineering student
- Applying for AI engineering roles
- Intermediate Python, new to agents
- High stress period: last month of uni + active job search simultaneously

## The 5 features (in priority order)
1. **Job tracker** — kanban-style application tracking (status, notes, deadlines) ✅ Phase 1 done
2. **Resume tailoring** — RAG over master resume + JD parsing → tailored bullet points
3. **Mock interview coach** — multi-turn agent loop, role-specific Q&A, STAR feedback
4. **Planner** — unified view of uni deadlines + job tasks, priority-ordered ✅ Phase 1 done
5. **Stress management** — daily brain dump → prioritized action list, reframing

## Tech stack
- **LangGraph** — agent orchestration (StateGraph, ToolNode)
- **LLM** — Claude Sonnet via `langchain-anthropic`, GPT-4o via `langchain-openai` (swappable via LLM_PROVIDER env var)
- **SQLite** — job applications + planner tasks (see `agent/database.py`)
- **ChromaDB** — vector store for resume RAG (Phase 2, not yet built)
- **Streamlit** — chat UI + live sidebar dashboard

## Project structure
```
job_agent/
├── app.py                 # Streamlit frontend + chat loop
├── agent/
│   ├── orchestrator.py    # LangGraph StateGraph — entry point for agent
│   ├── llm.py             # LLM wrapper (swap provider with env var)
│   ├── tools.py           # All LangGraph @tool functions
│   └── database.py        # SQLite CRUD — applications + tasks
├── data/                  # Auto-created, holds agent.db
├── CLAUDE.md              # This file
├── .env.example
└── requirements.txt
```

## Key conventions
- All tools are decorated with `@tool` from `langchain_core.tools` and registered in `get_tools()` in `tools.py`
- Adding a new feature = add DB functions in `database.py` + tools in `tools.py` + register in `get_tools()`
- The system prompt lives in `orchestrator.py` — update it when adding new features so the agent knows about them
- Never hardcode API keys — always use `os.getenv()`
- Keep tools focused and single-purpose — one tool per action, not one giant tool

## What to build next (Phase 2)
Resume tailoring pipeline:
1. User uploads master resume PDF → chunk + embed into Chroma
2. User pastes a job description → agent parses required skills
3. Agent retrieves relevant resume chunks + rewrites bullet points to match JD
4. Output: tailored resume section as text (later: export to .docx)

## Portfolio goals
- Demonstrate: LangGraph agent loops, RAG, tool use, structured LLM output, MCP integration
- The code should be clean enough to walk an interviewer through file by file
- README should have an architecture diagram and example conversations
