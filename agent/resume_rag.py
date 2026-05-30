import os
import re
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

CHROMA_PATH = os.getenv("CHROMA_PATH", "data/resume_store")
COLLECTION_NAME = "master_resume"

# Matches common resume section headers on their own line
_SECTION_RE = re.compile(
    r"^(EDUCATION|EXPERIENCE|WORK EXPERIENCE|PROFESSIONAL EXPERIENCE|PROJECTS?"
    r"|SKILLS?|TECHNICAL SKILLS|SUMMARY|OBJECTIVE|CERTIFICATIONS?"
    r"|PUBLICATIONS?|AWARDS?|ACTIVITIES|LEADERSHIP|VOLUNTEERING|LANGUAGES?|RESEARCH)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _vectorstore() -> Chroma:
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
    )


def _extract_text(pdf_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _chunk_by_section(text: str) -> list[dict]:
    positions = [(m.start(), m.group().strip()) for m in _SECTION_RE.finditer(text)]

    if not positions:
        # Non-standard resume — fall back to fixed-size chunks
        chunks = []
        for i in range(0, len(text), 800):
            chunk = text[i : i + 800].strip()
            if chunk:
                chunks.append({"section": "resume", "content": chunk})
        return chunks

    chunks = []
    for i, (start, header) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        content = text[start:end].strip()
        if len(content) > 50:
            chunks.append({"section": header, "content": content})
    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_resume(pdf_path: str) -> int:
    """Parse PDF, chunk by section, embed and store in ChromaDB. Returns chunk count."""
    text = _extract_text(pdf_path)
    chunks = _chunk_by_section(text)

    vs = _vectorstore()
    # Wipe any previous version before re-ingesting
    try:
        vs.delete_collection()
        vs = _vectorstore()
    except Exception:
        pass

    vs.add_texts(
        texts=[c["content"] for c in chunks],
        metadatas=[{"section": c["section"]} for c in chunks],
    )
    return len(chunks)


def resume_is_ingested() -> bool:
    try:
        return _vectorstore()._collection.count() > 0
    except Exception:
        return False


def retrieve_relevant_chunks(query: str, n_results: int = 5) -> list[dict]:
    """Return top-n chunks as dicts with 'content' and 'section' keys."""
    docs = _vectorstore().similarity_search(query, k=n_results)
    return [
        {"content": doc.page_content, "section": doc.metadata.get("section", "resume")}
        for doc in docs
    ]


@traceable(name="resume-tailoring-pipeline")
def run_tailoring_pipeline(jd_text: str) -> str:
    """Extract JD skills → retrieve resume chunks → rewrite bullets grouped by source."""
    from agent.llm import get_llm
    llm = get_llm()

    # Step 1: extract required skills from the JD
    skill_resp = llm.invoke([
        SystemMessage(content=(
            "You are a job description parser. "
            "Extract the key required technical skills, tools, and experience areas. "
            "Return a concise bullet list only — no intro text."
        )),
        HumanMessage(content=f"Job description:\n{jd_text}"),
    ])
    skills_text = skill_resp.content

    # Step 2: retrieve most relevant resume sections (with metadata)
    chunks = retrieve_relevant_chunks(jd_text, n_results=5)

    # Label each chunk with its index and broad section type so the LLM
    # can reference them by number and identify the specific role/project
    # from the content itself
    labeled_chunks = ""
    for i, chunk in enumerate(chunks, 1):
        labeled_chunks += (
            f"[CHUNK {i} — {chunk['section']}]\n"
            f"{chunk['content']}\n\n"
            "---\n\n"
        )

    # Step 3: rewrite bullets grouped by source role/project
    tailor_prompt = f"""You are an expert resume writer. Using the candidate's resume excerpts and the job description below, rewrite the most relevant bullet points so they naturally mirror the JD's required skills and keywords.

Rules:
- ONLY use facts, tools, and experiences explicitly mentioned in the resume excerpts below.
  If a skill appears in the JD but NOT in the excerpts, do not include it. No exceptions.
- Use strong action verbs; quantify impact wherever the original resume does.
- Mirror the EXACT terminology from the JD where the candidate's experience supports it.
  If the JD mentions patterns like "evaluation harnesses", "guardrails", "observability",
  or "multi-agent orchestration", use those exact phrases when the candidate's experience
  genuinely covers them.
- Be specific about tools, metrics, and outcomes — avoid vague phrases like "enhancing efficiency".

Output format — group bullets by their source role or project, using this structure:

## [Role Title or Project Name] — [Company or Context]
• bullet
• bullet

## [Next Role or Project] — [Company or Context]
• bullet

Instructions:
- Read each chunk and identify the specific job title, project name, and company/context
  from the content itself (not just the section label).
- Only create a heading for a chunk if you have at least one bullet to write for it.
- Use the exact role/project name as it appears in the resume.
- Aim for 2–3 bullets per heading, 5–8 bullets total.

REQUIRED SKILLS EXTRACTED FROM JD:
{skills_text}

CANDIDATE'S RESUME EXCERPTS:
{labeled_chunks}

JOB DESCRIPTION (truncated):
{jd_text[:2000]}"""

    response = llm.invoke([
        SystemMessage(content="You are an expert resume tailoring assistant."),
        HumanMessage(content=tailor_prompt),
    ])
    return response.content
