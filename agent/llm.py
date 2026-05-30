import os
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

def get_llm(provider: str = None):
    """
    Returns an LLM instance. Provider auto-detected from environment,
    or pass "anthropic" / "openai" explicitly.

    Set one of these in your .env:
        ANTHROPIC_API_KEY=...
        OPENAI_API_KEY=...

    If both are set, defaults to Anthropic (Claude).
    Override with: LLM_PROVIDER=openai
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "anthropic":
        return ChatAnthropic(
            model="claude-sonnet-4-5",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096,
        )
    elif provider == "openai":
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'anthropic' or 'openai'.")
