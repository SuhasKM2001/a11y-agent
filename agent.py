"""
The accessibility remediation agent — a LangGraph ReAct agent wired to GMI.

The whole "brain" is here: model wiring + the system prompt that turns a generic
ReAct loop into an accessibility worker. Your differentiation lives in the prompt,
not in the plumbing — this is where to spend your time.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# create_agent is the current (non-deprecated) home of the ReAct agent builder.
# NOTE: the system-prompt arg is named `system_prompt` here (it was `prompt` in
# the old langgraph.prebuilt.create_react_agent). The interface is otherwise the
# same — invoke/stream with {"messages": [...]}.
from langchain.agents import create_agent

from tools import TOOLS

load_dotenv()


def build_model() -> ChatOpenAI:
    """GMI is OpenAI-compatible, so this is the standard OpenAI client with two
    things swapped: base_url and api_key.

    Reads from env vars so the SAME code runs locally and on AgentBox. We accept
    either GMI_* or OPENAI_* names because AgentBox injects credentials at runtime
    and the exact names can vary — this avoids a deploy-time surprise.
    """
    api_key = (os.environ.get("GMI_MAAS_API_KEY")      # AgentBox injects this
               or os.environ.get("GMI_API_KEY")
               or os.environ.get("OPENAI_API_KEY"))
    base_url = (os.environ.get("GMI_MAAS_BASE_URL")    # AgentBox injects this
                or os.environ.get("GMI_BASE_URL")
                or os.environ.get("OPENAI_BASE_URL")
                or "https://api.gmi-serving.com/v1")
    model = (os.environ.get("GMI_MODEL") or os.environ.get("MODEL")
             or "nvidia/nemotron-3-ultra-550b-a55b")

    if not api_key:
        raise RuntimeError(
            "No API key found. Set GMI_API_KEY (or OPENAI_API_KEY) in your "
            "environment or .env file."
        )

    # GMI injects GMI_MAAS_BASE_URL as 'https://api.gmi-serving.com' (no /v1),
    # but the OpenAI-compatible endpoint lives under /v1. Normalize so requests
    # hit /v1/chat/completions whether the suffix is present or not.
    if base_url and not base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0,
        timeout=60,
    )


SYSTEM_PROMPT = """You are an accessibility remediation worker. You audit a web \
page for WCAG 2.1 AA / Section 508 compliance and return fixes a developer can \
paste in. You do the job end to end, not just detection.

Your loop:
1. Call scan_page(url) to get detected violations and "needs_review" items.
2. Each violation already includes a "context" field with the surrounding HTML, \
so use it to write contextual fixes. Only call get_element_context if a \
violation's context is empty and you still need surrounding markup.
3. For EACH violation produce:
   - what's wrong and WHERE (the selector),
   - WHY it matters, named to the human affected (e.g. "a screen-reader user \
hears nothing here"), not just the rule id,
   - the CORRECTED code for THIS specific markup — contextual, not generic,
   - a priority: Critical / Serious / Moderate.
4. For each "needs_review" item, make the judgment call the scanner couldn't \
and explain your reasoning (e.g. is alt='image123' actually meaningful? No — \
propose better).

Stop after you've covered every violation and review item. Then output a single \
final report grouped by priority. Be concrete; every fix must be copy-pasteable.
Do not invent violations beyond what scan_page returned.
Do NOT include a scan date or overall totals/counts in your report — those are \
computed by the system and added separately. Focus on the per-violation detail."""


def build_agent():
    """Returns a compiled ReAct agent. Invoke with:
        agent.invoke({"messages": [("user", "Audit https://...")]})
    """
    return create_agent(
        build_model(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
