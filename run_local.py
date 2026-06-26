"""
Run the agent locally and watch the ReAct loop step by step.

    python run_local.py https://example.com

The streamed Thought -> Action -> Observation trace is also your demo's "wow":
the room watches the agent think and work, not just spit out an answer.
"""

import sys
import json
from agent import build_agent
from summary import compute_summary


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    agent = build_agent()

    print(f"\n=== Auditing {url} ===\n")

    scan_json = {"violations": [], "needs_review": []}

    # stream_mode="updates" emits each node's output as it happens — perfect for
    # showing the loop. Each chunk is {node_name: {messages: [...]}}.
    for chunk in agent.stream(
        {"messages": [("user", f"Audit {url} for accessibility compliance.")]},
        stream_mode="updates",
    ):
        for node, payload in chunk.items():
            for msg in payload.get("messages", []):
                # Tool call (Action)
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        print(f"[ACTION] {tc['name']}({tc['args']})")
                # Tool result (Observation)
                elif msg.__class__.__name__ == "ToolMessage":
                    if getattr(msg, "name", "") == "scan_page":
                        try:
                            scan_json = json.loads(msg.content)
                        except Exception:
                            pass
                    preview = str(msg.content)[:200]
                    print(f"[OBSERVATION] {preview}...\n")
                # Model text (Thought / final report)
                elif getattr(msg, "content", None):
                    print(f"[AGENT]\n{msg.content}\n")

    # Deterministic summary — computed in code, not by the model.
    s = compute_summary(scan_json)
    print("=== SUMMARY (computed in code) ===")
    print(f"  Scanned at:       {s['scanned_at']}")
    print(f"  Score:            {s['score']}%  ({s['status']})")
    print(f"  Rules failed:     {s['rules_failed']}")
    print(f"  Total elements:   {s['total_violations']}")
    print(f"  Critical / Warn:  {s['critical_count']} / {s['warning_count']}")
    print(f"  Needs review:     {s['needs_review']}")


if __name__ == "__main__":
    main()
