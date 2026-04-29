"""
Trello tool — fetches cards due today or flagged as high-priority.

Requires environment variables:
  TRELLO_API_KEY   — your Trello Power-Up API key
  TRELLO_TOKEN     — your Trello user token
  TRELLO_BOARD_ID  — the board to query (or comma-separated list)

Anthropic tool schema is exposed via TOOL_DEFINITION so main.py can
register it without duplicating the JSON schema.
"""

import os
from datetime import date, timezone
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Anthropic tool definition (passed to client.messages.create(tools=[...]))
# ---------------------------------------------------------------------------

TOOL_DEFINITION: dict[str, Any] = {
    "name": "get_trello_tasks",
    "description": (
        "Retrieve Trello cards that are due today or marked as high-priority "
        "(red label). Returns a list of cards with their list name, due date, "
        "labels, and URL."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "include_overdue": {
                "type": "boolean",
                "description": "Also include cards whose due date has already passed.",
            }
        },
        "required": [],
    },
}

# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

TRELLO_BASE = "https://api.trello.com/1"


def _auth_params() -> dict[str, str]:
    return {
        "key": os.environ["TRELLO_API_KEY"],
        "token": os.environ["TRELLO_TOKEN"],
    }


def get_trello_tasks(include_overdue: bool = False) -> dict[str, Any]:
    """
    Fetch Trello cards due today (and optionally overdue) from the configured board.

    Returns a dict with keys:
      - cards: list of simplified card objects
      - error: str | None
    """
    board_ids = os.environ.get("TRELLO_BOARD_ID", "").split(",")
    board_ids = [b.strip() for b in board_ids if b.strip()]

    if not board_ids:
        return {"cards": [], "error": "TRELLO_BOARD_ID is not set"}

    today = date.today().isoformat()
    cards: list[dict[str, Any]] = []

    try:
        with httpx.Client(timeout=10) as client:
            for board_id in board_ids:
                # Fetch all open cards on the board
                resp = client.get(
                    f"{TRELLO_BASE}/boards/{board_id}/cards/open",
                    params={**_auth_params(), "fields": "name,due,labels,url,idList"},
                )
                resp.raise_for_status()
                raw_cards = resp.json()

                # Fetch list names for this board
                lists_resp = client.get(
                    f"{TRELLO_BASE}/boards/{board_id}/lists",
                    params={**_auth_params(), "fields": "name"},
                )
                lists_resp.raise_for_status()
                list_names = {lst["id"]: lst["name"] for lst in lists_resp.json()}

                for card in raw_cards:
                    due = card.get("due")
                    if due:
                        due_date = due[:10]  # YYYY-MM-DD
                        is_today = due_date == today
                        is_overdue = due_date < today
                    else:
                        due_date = None
                        is_today = is_overdue = False

                    label_names = [lbl["name"] or lbl["color"] for lbl in card.get("labels", [])]
                    is_high_priority = "red" in [lbl["color"] for lbl in card.get("labels", [])]

                    if is_today or is_high_priority or (include_overdue and is_overdue):
                        cards.append(
                            {
                                "name": card["name"],
                                "list": list_names.get(card["idList"], "Unknown"),
                                "due": due_date,
                                "overdue": is_overdue,
                                "labels": label_names,
                                "url": card["url"],
                            }
                        )

    except httpx.HTTPStatusError as exc:
        return {"cards": cards, "error": f"Trello API error {exc.response.status_code}"}
    except Exception as exc:  # noqa: BLE001
        return {"cards": cards, "error": str(exc)}

    return {"cards": cards, "error": None}


# ---------------------------------------------------------------------------
# Tool dispatcher — called by main.py when Claude requests this tool
# ---------------------------------------------------------------------------

def run(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Entry point called by the agent loop with Claude's parsed tool input."""
    return get_trello_tasks(include_overdue=tool_input.get("include_overdue", False))
