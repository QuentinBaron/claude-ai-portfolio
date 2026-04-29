"""
Morning Planning Agent — entry point.

Reads Trello tasks, Google Calendar events, and Gmail threads, then asks
Claude (claude-opus-4-7) to produce a prioritized daily plan.

Usage:
    python main.py

Required environment variables:
    ANTHROPIC_API_KEY
    TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID
    GOOGLE_SERVICE_ACCOUNT_FILE  (or GOOGLE_CREDENTIALS_FILE)
    GMAIL_IMPERSONATE_EMAIL      (if using service-account + domain delegation)

Optional:
    USER_NAME        — e.g. "Alice" (used in the greeting)
    USER_TIMEZONE    — e.g. "Europe/Paris" (defaults to UTC)
"""

import json
import os
from datetime import datetime, timezone

import anthropic

from prompts.system import SYSTEM_PROMPT
from tools import calendar, gmail, trello

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = [
    trello.TOOL_DEFINITION,
    calendar.TOOL_DEFINITION,
    gmail.TOOL_DEFINITION,
]

# Map tool name → run() function
TOOL_RUNNERS = {
    "get_trello_tasks": trello.run,
    "get_calendar_events": calendar.run,
    "get_gmail_threads": gmail.run,
}

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent() -> str:
    """
    Run the morning planning agent and return the final plan as a string.

    Uses a manual agentic loop so we can log each tool call for transparency.
    Streams the final response so the user sees output incrementally.
    """
    client = anthropic.Anthropic()

    user_name = os.environ.get("USER_NAME", "")
    tz_name = os.environ.get("USER_TIMEZONE", "UTC")
    today_str = datetime.now(timezone.utc).strftime("%A, %B %-d %Y")

    greeting = f"Hi{' ' + user_name if user_name else ''}! Today is {today_str} ({tz_name})."
    user_message = (
        f"{greeting}\n\n"
        "Please retrieve my tasks, calendar, and emails, then produce my morning plan."
    )

    messages: list[dict] = [{"role": "user", "content": user_message}]

    print(f"[agent] Starting morning plan for {today_str}\n")

    # The system prompt is stable — cache it to save tokens on repeated runs.
    system_with_cache = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    # Agentic loop: keep calling the model until it stops using tools.
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_with_cache,
            tools=TOOLS,
            messages=messages,
            thinking={"type": "adaptive"},
        )

        # Append the full assistant response to history (preserves tool_use blocks).
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract and return the final text block.
            final_text = next(
                (block.text for block in response.content if block.type == "text"),
                "",
            )
            return final_text

        if response.stop_reason != "tool_use":
            # Unexpected stop reason — bail out gracefully.
            return f"[agent] Unexpected stop_reason: {response.stop_reason}"

        # Execute each tool Claude requested.
        tool_results: list[dict] = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input
            print(f"[tool] {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")

            runner = TOOL_RUNNERS.get(tool_name)
            if runner is None:
                result = {"error": f"Unknown tool: {tool_name}"}
            else:
                try:
                    result = runner(tool_input)
                except Exception as exc:  # noqa: BLE001
                    result = {"error": str(exc)}

            print(f"       → {json.dumps(result, ensure_ascii=False)[:120]}…\n")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

        # Feed tool results back to Claude.
        messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    plan = run_agent()
    print("\n" + "=" * 60)
    print("YOUR MORNING PLAN")
    print("=" * 60)
    print(plan)


if __name__ == "__main__":
    main()
