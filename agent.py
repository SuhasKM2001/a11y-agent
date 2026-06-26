"""
The accessibility remediation agent — a LangGraph ReAct agent wired to GMI.

The whole "brain" is here: model wiring + the system prompt that turns a generic
ReAct loop into an accessibility worker. Your differentiation lives in the prompt,
not in the plumbing — this is where to spend your time.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

# NOTE on the import: in LangGraph 1.x this still works but is deprecated; the new
# path is `from langchain.agents import create_agent`. Sticking with the prebuilt
# import because it matches existing docs/muscle memory and is stable on the
# pinned version. If you upgrade later, switch to create_agent.
from langgraph.prebuilt import create_react_agent

from tools import TOOLS

load_dotenv()


def build_model() -> ChatOpenAI:
    """GMI is OpenAI-compatible, so this is the standard OpenAI client with two
    things swapped: base_url and api_key.

    Reads from env vars so the SAME code runs locally and on AgentBox:
      - locally, you set these in .env
      - on AgentBox, GMI injects credentials at runtime. CONFIRM the exact
        injected variable names in GMI's docs/dashboard and, if they differ,
        either rename here or map them at container start. Do NOT hardcode keys.
    """
    return ChatOpenAI(
        model=os.environ.get("GMI_MODEL", "meta-llama/Llama-3.3-70B-Instruct"),
        base_url=os.environ.get("GMI_BASE_URL", "https://api.gmi-serving.com/v1"),
        api_key=os.environ["GMI_API_KEY"],
        temperature=0,          # determinism matters for a compliance tool
        timeout=60,
    )


SYSTEM_PROMPT = """You are an accessibility remediation worker. You audit a web \
page for WCAG 2.1 AA / Section 508 compliance and return fixes a developer can \
paste in. You do the job end to end, not just detection.

Your loop:
1. Call scan_page(url) to get detected violations and "needs_review" items.
2. For each violation, if you need surrounding content to write a correct fix \
(e.g. to choose meaningful alt text or descriptive link text), call \
get_element_context. Don't guess context you can fetch.
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
Do not invent violations beyond what scan_page returned."""


def build_agent():
    """Returns a compiled ReAct agent. Invoke with:
        agent.invoke({"messages": [("user", "Audit https://...")]})
    """
    return create_react_agent(
        build_model(),
        tools=TOOLS,
        prompt=SYSTEM_PROMPT,
    )
