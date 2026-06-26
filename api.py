"""
FastAPI wrapper around the accessibility agent.

This is what AgentBox runs and what your frontend calls.

Run locally:
    uv run uvicorn api:app --reload --port 8000

Then:
    curl -X POST localhost:8000/audit -H "Content-Type: application/json" \
         -d '{"url":"https://suhaskm.tech"}'

NOTE on async: the endpoints are plain `def` (not `async def`) on purpose.
FastAPI runs sync endpoints in a worker thread, and Playwright's sync API must
NOT run inside an asyncio event loop. Plain `def` keeps Playwright happy.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import build_agent
from summary import extract_scan_from_messages, compute_summary

app = FastAPI(title="Accessibility Remediation Agent")

# Allow the separate frontend to call this. Lock origins down for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build the agent once at startup and reuse it across requests (it's stateless
# per call — we pass fresh messages each time).
agent = build_agent()


class AuditRequest(BaseModel):
    url: str


@app.get("/health")
def health():
    """Liveness check — handy for AgentBox and for confirming the server is up."""
    return {"status": "ok"}


@app.post("/audit")
def audit(req: AuditRequest):
    """Run the full agent on a URL and return the remediation report plus
    deterministic counts (computed in code, not by the model)."""
    result = agent.invoke(
        {"messages": [("user", f"Audit {req.url} for accessibility compliance.")]}
    )
    messages = result["messages"]
    report = messages[-1].content

    # Authoritative numbers from the real scan data — never the model's prose.
    scan = extract_scan_from_messages(messages)
    summary = compute_summary(scan)

    return {
        "url": req.url,
        "summary": summary,             # score, counts, status, scanned_at
        "report": report,               # the model's per-violation reasoning + fixes
        "violations": scan.get("violations", []),   # raw, for structured UI rendering
        "needs_review": scan.get("needs_review", []),
    }
