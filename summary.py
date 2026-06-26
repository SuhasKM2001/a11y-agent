"""
Deterministic post-processing of an agent run.

The model is great at reasoning (impact, fixes, judgment) but unreliable at
bookkeeping (counting nodes, knowing today's date). So we do the bookkeeping
here, in code, from the real scan data — the model never touches the numbers.
"""

import json
from datetime import datetime, timezone


def extract_scan_from_messages(messages) -> dict:
    """Pull the raw scan_page JSON out of the agent's message history.
    Returns the last scan_page result (in case it scanned more than once).
    """
    for m in reversed(messages):
        if m.__class__.__name__ == "ToolMessage" and getattr(m, "name", "") == "scan_page":
            try:
                return json.loads(m.content)
            except Exception:
                break
    return {"violations": [], "needs_review": []}


# axe impact levels, weighted for a transparent score.
_WEIGHTS = {"critical": 15, "serious": 8, "moderate": 4, "minor": 2}


def compute_summary(scan: dict) -> dict:
    """Authoritative counts + score + real timestamp, derived from scan data."""
    violations = scan.get("violations", [])
    needs_review = scan.get("needs_review", [])

    by_impact = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    total_nodes = 0
    for v in violations:
        impact = (v.get("impact") or "moderate").lower()
        n = len(v.get("nodes", [])) or 1
        by_impact[impact] = by_impact.get(impact, 0) + n
        total_nodes += n

    nr = len(needs_review)

    # Score reflects CONFIRMED failures only — it's a "how much can we trust this
    # page is accessible" number. needs_review items are NOT folded in (axe
    # couldn't confirm them); they're surfaced as their own signal instead.
    confirmed_penalty = sum(by_impact[k] * w for k, w in _WEIGHTS.items())

    if total_nodes == 0 and nr == 0:
        score, status = 100, "PASS"            # nothing failed, nothing to review
    elif total_nodes == 0 and nr > 0:
        score, status = None, "REVIEW REQUIRED"  # no confirmed fails, but lots to check
    else:
        score = max(0, 100 - confirmed_penalty)
        status = "NEEDS WORK" if score >= 50 else "FAIL"

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rules_failed": len(violations),       # distinct rules that failed
        "total_violations": total_nodes,       # individual elements affected
        "needs_review": nr,
        "critical_count": by_impact["critical"],
        "warning_count": by_impact["serious"] + by_impact["moderate"] + by_impact["minor"],
        "by_impact": by_impact,
        "score": score,                        # int 0-100, or None when REVIEW REQUIRED
        "status": status,
    }
