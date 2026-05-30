# Job & Uni Agent

An AI agent to navigate the chaos of final semester — job applications, university deadlines, interview prep, and stress management. Built with LangGraph, Claude / GPT-4o, and Streamlit.

## Features (Phase 1)
- **Job tracker** — add applications, update statuses, track deadlines
- **Planner** — unified task list across uni and job search, priority-ordered

Coming in Phase 2: resume tailoring (RAG), mock interview coach, stress check-ins.

## Tech stack
- **LangGraph** — agent orchestration and tool calling loop
- **Claude Sonnet / GPT-4o** — LLM backbone (swap with one env var)
- **SQLite** — lightweight local database for applications and tasks
- **ChromaDB** — vector store for resume RAG (Phase 2)
- **Streamlit** — chat UI with live sidebar dashboard

## Setup

### 1. Clone and install
```bash
git clone <your-repo>
cd job_agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your API key(s)
```

### 3. Run
```bash
streamlit run app.py
```

## Project structure
```
job_agent/
├── app.py                 # Streamlit frontend
├── agent/
│   ├── orchestrator.py    # LangGraph agent graph
│   ├── llm.py             # LLM wrapper (Anthropic + OpenAI)
│   ├── tools.py           # LangGraph tools (job tracker, planner)
│   └── database.py        # SQLite data layer
├── data/                  # Auto-created, stores agent.db
├── requirements.txt
├── .env.example
└── README.md
```

## Switching between Claude and GPT-4o
In your `.env`:
```
LLM_PROVIDER=anthropic   # uses Claude Sonnet
LLM_PROVIDER=openai      # uses GPT-4o
```

## Example conversations
```
You: I just applied to Anthropic for a ML Engineer role
Agent: [calls track_application tool] Added application #1: ML Engineer at Anthropic (status: applied). 
       Want me to add a task to follow up in a week?

You: What should I focus on this week?
Agent: [calls get_applications and get_tasks] Here's your priority breakdown...

You: Move my Anthropic app to interview stage
Agent: [calls update_application_status] Done! Updated to INTERVIEW. Want me to add interview prep tasks?
```
