"""
Run the agent locally and watch the ReAct loop step by step.

    python run_local.py https://example.com

The streamed Thought -> Action -> Observation trace is also your demo's "wow":
the room watches the agent think and work, not just spit out an answer.
"""

import sys
from agent import build_agent


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    agent = build_agent()

    print(f"\n=== Auditing {url} ===\n")

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
                    preview = str(msg.content)[:200]
                    print(f"[OBSERVATION] {preview}...\n")
                # Model text (Thought / final report)
                elif getattr(msg, "content", None):
                    print(f"[AGENT]\n{msg.content}\n")


if __name__ == "__main__":
    main()
