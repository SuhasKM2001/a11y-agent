"""
Tools the ReAct agent can call.

RIGHT NOW these are STUBS returning realistic fake data, so you can build and
test the whole loop before touching real detection. This is deliberate: the
detection method (hosted scan API vs axe-core CLI in-container) is the riskiest
piece, so we keep it behind a clean JSON boundary and swap it in last.

When you're ready for real detection, replace ONLY the body of `scan_page`.
The agent never changes — it just keeps getting JSON.
"""

import json
from langchain_core.tools import tool


# ---- STUB DATA: looks like real axe-core output -----------------------------
# axe-core returns violations with: id, impact, help, and `nodes` (each node has
# the offending `html` and a CSS `target`). We mimic that shape so swapping in
# real axe-core later requires no changes to the agent.
_FAKE_SCAN = {
    "url": "https://example.com",
    "violations": [
        {
            "id": "image-alt",
            "impact": "critical",
            "help": "Images must have alternate text",
            "nodes": [
                {"html": '<img src="/checkout-cart.png">',
                 "target": ["main > section:nth-child(2) > img"]}
            ],
        },
        {
            "id": "color-contrast",
            "impact": "serious",
            "help": "Elements must meet minimum color contrast ratio thresholds",
            "nodes": [
                {"html": '<a class="cta" style="color:#9bd1ff;background:#ffffff">Buy now</a>',
                 "target": [".cta"]}
            ],
        },
        {
            "id": "link-name",
            "impact": "serious",
            "help": "Links must have discernible text",
            "nodes": [
                {"html": '<a href="/returns">click here</a>',
                 "target": ["footer > a:nth-child(3)"]}
            ],
        },
        {
            "id": "label",
            "impact": "critical",
            "help": "Form elements must have labels",
            "nodes": [
                {"html": '<input type="email" placeholder="Email">',
                 "target": ["#newsletter > input"]}
            ],
        },
    ],
    # Items the scanner can't decide alone — it punts these to a human.
    # THIS is where your agent's judgment layer earns its keep.
    "needs_review": [
        {
            "id": "image-alt-quality",
            "note": "Image has alt='image123' — present but possibly not meaningful.",
            "html": '<img src="/team.jpg" alt="image123">',
            "target": ["section.about > img"],
        }
    ],
}


@tool
def scan_page(url: str) -> str:
    """Run an automated accessibility scan on the page at `url`.

    Returns a JSON string with two parts:
      - "violations": machine-detectable WCAG/508 failures (axe-core style).
      - "needs_review": items the scanner flagged but cannot judge on its own.

    Use this FIRST to find out what's wrong before reasoning about fixes.
    """
    # TODO(real detection): replace this body with one of —
    #   (a) an HTTP call to a hosted scan API that returns axe JSON, or
    #   (b) a subprocess call to the axe-core CLI against a headless browser.
    # Keep the return shape identical and the agent keeps working unchanged.
    result = dict(_FAKE_SCAN)
    result["url"] = url
    return json.dumps(result)


@tool
def get_element_context(url: str, target: str) -> str:
    """Fetch the surrounding HTML/context for the element at CSS selector `target`
    on the page at `url`. Use this when you need nearby content (headings, link
    destinations, neighboring text) to write a *specific, contextual* fix rather
    than a generic one.
    """
    # TODO(real): fetch the page and return the parent/sibling markup for `target`.
    # Stub returns plausible surrounding context per selector.
    contexts = {
        "main > section:nth-child(2) > img":
            '<section><h2>Your shopping cart</h2>'
            '<img src="/checkout-cart.png"><p>3 items ready for checkout.</p></section>',
        "footer > a:nth-child(3)":
            '<footer>... <a href="/returns">click here</a> to read our 30-day '
            'return policy ...</footer>',
        "#newsletter > input":
            '<form id="newsletter"><h3>Get weekly deals</h3>'
            '<input type="email" placeholder="Email"><button>Subscribe</button></form>',
    }
    return json.dumps({"target": target, "context": contexts.get(target, "<context unavailable>")})


# Export the tool list the agent will use
TOOLS = [scan_page, get_element_context]
