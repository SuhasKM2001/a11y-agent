"""
Tools the ReAct agent can call — now with REAL detection.

scan_page launches a headless Chromium (via Playwright), loads the URL, runs
axe-core against the rendered DOM, and returns violations + "needs_review"
(axe's "incomplete") items as JSON. It also embeds the surrounding HTML for each
flagged element in the SAME browser session, so the agent gets context without
relaunching the browser per element.

The JSON shape is identical to the old stub, so the agent is unchanged.
"""

import json
from langchain_core.tools import tool
from playwright.sync_api import sync_playwright
from axe_playwright_python.sync_playwright import Axe

_axe = Axe()
# Ask axe for BOTH violations and incomplete items. "incomplete" = the things
# axe flags but can't decide on its own — that's your judgment-call layer.
_AXE_OPTS = {"resultTypes": ["violations", "incomplete"]}

# Be tolerant of slow / JS-rendered pages without hanging forever.
_NAV_TIMEOUT_MS = 30000
_SETTLE_MS = 1500          # let client-side JS render after load
_CONTEXT_CHARS = 1200      # cap embedded context so we don't flood the model


def _selector(target) -> str:
    """axe `target` is a list (nested lists for iframes). Flatten to one CSS string."""
    parts = []
    for t in (target or []):
        parts.append(t if isinstance(t, str) else " ".join(t))
    return " ".join(parts)


def _context_for(page, selector: str) -> str:
    """Return the parent element's outerHTML for `selector`, for contextual fixes."""
    if not selector:
        return ""
    try:
        el = page.query_selector(selector)
        if not el:
            return ""
        html = el.evaluate("e => (e.parentElement || e).outerHTML")
        return (html or "")[:_CONTEXT_CHARS]
    except Exception:
        return ""


@tool
def scan_page(url: str) -> str:
    """Run a real accessibility scan on the page at `url`.

    Loads the page in a headless browser, runs axe-core (WCAG 2.x / Section 508),
    and returns a JSON string with:
      - "violations": detected failures, each node has html, target, and context.
      - "needs_review": items axe flagged but couldn't decide (your judgment layer).
    Call this FIRST.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="load", timeout=_NAV_TIMEOUT_MS)
            page.wait_for_timeout(_SETTLE_MS)
            resp = _axe.run(page, options=_AXE_OPTS).response

            def node_obj(n):
                sel = _selector(n.get("target"))
                return {"html": n.get("html"), "target": sel,
                        "context": _context_for(page, sel)}

            violations = [{
                "id": v.get("id"),
                "impact": v.get("impact"),
                "help": v.get("help"),
                "nodes": [node_obj(n) for n in v.get("nodes", [])],
            } for v in resp.get("violations", [])]

            needs_review = []
            for inc in resp.get("incomplete", []):
                for n in inc.get("nodes", []):
                    obj = node_obj(n)
                    needs_review.append({"id": inc.get("id"), "note": inc.get("help"),
                                         **obj})
            browser.close()

        return json.dumps({"url": url, "violations": violations,
                           "needs_review": needs_review})
    except Exception as e:
        # Never crash the agent — return a structured error it can report.
        return json.dumps({"url": url, "error": str(e),
                           "violations": [], "needs_review": []})


@tool
def get_element_context(url: str, target: str) -> str:
    """Fallback: fetch surrounding HTML for CSS selector `target` on `url`.
    Usually unnecessary because scan_page already embeds context per violation.
    Use only when a violation's "context" came back empty.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="load", timeout=_NAV_TIMEOUT_MS)
            page.wait_for_timeout(1000)
            ctx = _context_for(page, target) or "<context unavailable>"
            browser.close()
        return json.dumps({"target": target, "context": ctx})
    except Exception as e:
        return json.dumps({"target": target, "context": "<context unavailable>",
                           "error": str(e)})


TOOLS = [scan_page, get_element_context]
