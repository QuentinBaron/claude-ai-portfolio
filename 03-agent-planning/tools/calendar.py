"""
Google Calendar tool — fetches today's events for the authenticated user.

Authentication uses a service-account JSON key or OAuth2 credentials file.
Set one of:
  GOOGLE_SERVICE_ACCOUNT_FILE  — path to service-account JSON (server-to-server)
  GOOGLE_CREDENTIALS_FILE      — path to OAuth2 credentials JSON (user auth)

The google-auth and google-api-python-client packages must be installed:
  pip install google-auth google-auth-oauthlib google-api-python-client
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Anthropic tool definition
# ---------------------------------------------------------------------------

TOOL_DEFINITION: dict[str, Any] = {
    "name": "get_calendar_events",
    "description": (
        "Retrieve Google Calendar events scheduled for today. "
        "Returns event title, start time, end time, location, and attendees."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "calendar_id": {
                "type": "string",
                "description": (
                    "Calendar ID to query. Defaults to 'primary' (the user's main calendar)."
                ),
            },
            "include_all_day": {
                "type": "boolean",
                "description": "Include all-day events (no specific time). Defaults to true.",
            },
        },
        "required": [],
    },
}

# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

def _build_service():
    """Build and return a Google Calendar API service object."""
    # Import lazily so the module loads even without google packages installed
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        import google.auth
    except ImportError as exc:
        raise ImportError(
            "Install Google client libraries: "
            "pip install google-auth google-api-python-client"
        ) from exc

    sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if sa_file:
        creds = service_account.Credentials.from_service_account_file(
            sa_file,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )
    else:
        # Fall back to application default credentials (gcloud auth / OAuth2 file)
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        )

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_calendar_events(
    calendar_id: str = "primary",
    include_all_day: bool = True,
) -> dict[str, Any]:
    """
    Fetch today's Google Calendar events.

    Returns a dict with keys:
      - events: list of simplified event objects
      - error: str | None
    """
    try:
        service = _build_service()
    except (ImportError, Exception) as exc:
        return {"events": [], "error": str(exc)}

    # Time bounds for today in UTC
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

    try:
        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_of_day.isoformat(),
                timeMax=end_of_day.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        return {"events": [], "error": str(exc)}

    events: list[dict[str, Any]] = []
    for item in result.get("items", []):
        start = item["start"].get("dateTime") or item["start"].get("date")
        end = item["end"].get("dateTime") or item["end"].get("date")

        is_all_day = "date" in item["start"] and "dateTime" not in item["start"]
        if is_all_day and not include_all_day:
            continue

        attendees = [
            a.get("email", "") for a in item.get("attendees", []) if not a.get("self")
        ]

        events.append(
            {
                "title": item.get("summary", "(no title)"),
                "start": start,
                "end": end,
                "all_day": is_all_day,
                "location": item.get("location"),
                "attendees": attendees,
                "meet_link": item.get("hangoutLink"),
                "description": (item.get("description") or "")[:200],  # truncate
            }
        )

    return {"events": events, "error": None}


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def run(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Entry point called by the agent loop with Claude's parsed tool input."""
    return get_calendar_events(
        calendar_id=tool_input.get("calendar_id", "primary"),
        include_all_day=tool_input.get("include_all_day", True),
    )
