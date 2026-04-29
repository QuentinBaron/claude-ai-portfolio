"""
Gmail tool — fetches unread threads that likely require action.

Uses the same Google auth setup as calendar.py:
  GOOGLE_SERVICE_ACCOUNT_FILE  or  GOOGLE_CREDENTIALS_FILE

For Gmail with a service account, domain-wide delegation must be enabled and
the service account must impersonate a user via:
  GMAIL_IMPERSONATE_EMAIL  — the user email to impersonate

pip install google-auth google-api-python-client
"""

import os
from typing import Any

# ---------------------------------------------------------------------------
# Anthropic tool definition
# ---------------------------------------------------------------------------

TOOL_DEFINITION: dict[str, Any] = {
    "name": "get_gmail_threads",
    "description": (
        "Retrieve unread Gmail threads that require action. "
        "Returns thread subject, sender, snippet, and received date."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Maximum number of threads to return. Defaults to 10.",
            },
            "label": {
                "type": "string",
                "description": (
                    "Gmail label to filter by (e.g. 'INBOX', 'IMPORTANT'). "
                    "Defaults to 'INBOX'."
                ),
            },
        },
        "required": [],
    },
}

# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

def _build_service(impersonate: str | None = None):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        import google.auth
    except ImportError as exc:
        raise ImportError(
            "Install Google client libraries: "
            "pip install google-auth google-api-python-client"
        ) from exc

    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")

    if sa_file:
        creds = service_account.Credentials.from_service_account_file(
            sa_file, scopes=scopes
        )
        if impersonate:
            creds = creds.with_subject(impersonate)
    else:
        creds, _ = google.auth.default(scopes=scopes)

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _get_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def get_gmail_threads(
    max_results: int = 10,
    label: str = "INBOX",
) -> dict[str, Any]:
    """
    Fetch unread Gmail threads.

    Returns a dict with keys:
      - threads: list of simplified thread objects
      - error: str | None
    """
    impersonate = os.environ.get("GMAIL_IMPERSONATE_EMAIL")

    try:
        service = _build_service(impersonate)
    except (ImportError, Exception) as exc:
        return {"threads": [], "error": str(exc)}

    try:
        # List unread threads in the requested label
        result = (
            service.users()
            .threads()
            .list(
                userId="me",
                q=f"is:unread label:{label}",
                maxResults=max_results,
            )
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        return {"threads": [], "error": str(exc)}

    raw_threads = result.get("threads", [])
    threads: list[dict[str, Any]] = []

    for t in raw_threads:
        try:
            thread_data = (
                service.users()
                .threads()
                .get(userId="me", id=t["id"], format="metadata",
                     metadataHeaders=["Subject", "From", "Date"])
                .execute()
            )
        except Exception:  # noqa: BLE001
            continue

        # Use the first message in the thread for metadata
        messages = thread_data.get("messages", [])
        if not messages:
            continue
        first_msg = messages[0]
        headers = first_msg.get("payload", {}).get("headers", [])

        threads.append(
            {
                "id": t["id"],
                "subject": _get_header(headers, "Subject") or "(no subject)",
                "from": _get_header(headers, "From"),
                "date": _get_header(headers, "Date"),
                "snippet": thread_data.get("snippet", ""),
                "message_count": len(messages),
                "url": f"https://mail.google.com/mail/u/0/#inbox/{t['id']}",
            }
        )

    return {"threads": threads, "error": None}


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def run(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Entry point called by the agent loop with Claude's parsed tool input."""
    return get_gmail_threads(
        max_results=tool_input.get("max_results", 10),
        label=tool_input.get("label", "INBOX"),
    )
