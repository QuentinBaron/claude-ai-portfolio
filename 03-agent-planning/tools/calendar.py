"""
Google Calendar tool — Agent Planning Matinal.

Lit les événements du jour depuis tous les agendas pertinents.
Utilise httpx pour les appels API (évite les problèmes httplib2 sur Windows).

Auth : OAuth 2.0 Desktop via InstalledAppFlow.
  1ère exécution : ouvre le navigateur → enregistre google_token.json
  Exécutions suivantes : recharge le token automatiquement.

Variables d'environnement :
  GOOGLE_CREDENTIALS_FILE  — chemin vers le fichier OAuth JSON (depuis GCP)
  GOOGLE_TOKEN_FILE        — (optionnel) chemin pour le token, défaut : même dossier
"""

import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

# ---------------------------------------------------------------------------
# Mapping agendas → comportement
# ---------------------------------------------------------------------------

CALENDAR_CONFIG: list[dict[str, str]] = [
    {
        "id": "qb.baron@gmail.com",
        "name": "Pro & autres",
        "behavior": "mandatory",
    },
    {
        "id": "m8iem642uehslto4b4vusq8a40@group.calendar.google.com",
        "name": "Voyages & Sport",
        "behavior": "mandatory",
    },
    {
        "id": "b762r2e9otckhpujriotu7o4kg@group.calendar.google.com",
        "name": "Perso",
        "behavior": "important",
    },
    {
        "id": "dl9ohu6rmet7b416lv9e90m5bk@group.calendar.google.com",
        "name": "Mathilde",
        "behavior": "indirect",
    },
]

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3/calendars"

# ---------------------------------------------------------------------------
# Définition de l'outil Anthropic
# ---------------------------------------------------------------------------

TOOL_DEFINITION: dict[str, Any] = {
    "name": "get_calendar_events",
    "description": (
        "Récupère les événements Google Calendar du jour pour tous les agendas pertinents. "
        "Retourne pour chaque événement : titre, heure de début/fin, agenda, "
        "comportement (mandatory/important/indirect) et opportunité Deep Work "
        "(quand Mathilde est à la pharmacie)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "include_all_day": {
                "type": "boolean",
                "description": "Inclure les événements sur toute la journée. Défaut : true.",
            }
        },
        "required": [],
    },
}

# ---------------------------------------------------------------------------
# Auth OAuth 2.0
# ---------------------------------------------------------------------------

def _get_credentials():
    """
    Charge ou crée les credentials OAuth.
    Ouvre le navigateur uniquement à la 1ère exécution.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise ImportError(
            "pip install google-auth google-auth-oauthlib"
        ) from exc

    credentials_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    if not credentials_file or not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"Fichier credentials introuvable : {credentials_file}\n"
            "Configure GOOGLE_CREDENTIALS_FILE."
        )

    token_file = os.environ.get(
        "GOOGLE_TOKEN_FILE",
        os.path.join(os.path.dirname(credentials_file), "google_token.json"),
    )

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return creds


def _get_token() -> str:
    """Retourne un access token valide."""
    from google.auth.transport.requests import Request
    creds = _get_credentials()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        credentials_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "")
        token_file = os.environ.get(
            "GOOGLE_TOKEN_FILE",
            os.path.join(os.path.dirname(credentials_file), "google_token.json"),
        )
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return creds.token


# ---------------------------------------------------------------------------
# Lecture des événements via httpx
# ---------------------------------------------------------------------------

def _is_pharmacie(event: dict) -> bool:
    keywords = ["pharmacie", "pharma", "pharmacy"]
    text = (
        (event.get("summary") or "") + " " + (event.get("description") or "")
    ).lower()
    return any(kw in text for kw in keywords)


def _format_event(event: dict, calendar_config: dict, include_all_day: bool) -> dict | None:
    start_raw = event["start"].get("dateTime") or event["start"].get("date")
    end_raw = event["end"].get("dateTime") or event["end"].get("date")

    is_all_day = "dateTime" not in event["start"]
    if is_all_day and not include_all_day:
        return None

    result = {
        "title": event.get("summary", "(sans titre)"),
        "start": start_raw,
        "end": end_raw,
        "all_day": is_all_day,
        "calendar": calendar_config["name"],
        "behavior": calendar_config["behavior"],
        "location": event.get("location"),
        "meet_link": event.get("hangoutLink"),
    }

    if calendar_config["behavior"] == "indirect":
        result["deep_work_opportunity"] = _is_pharmacie(event)

    return result


def get_calendar_events(include_all_day: bool = True) -> dict[str, Any]:
    try:
        token = _get_token()
    except Exception as exc:
        return {"events": [], "error": f"Auth error: {exc}"}

    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

    params = {
        "timeMin": start_of_day.isoformat(),
        "timeMax": end_of_day.isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
    }

    events: list[dict] = []
    errors: list[str] = []

    with httpx.Client(timeout=30) as client:
        for cal in CALENDAR_CONFIG:
            try:
                cal_id_encoded = quote(cal["id"], safe="")
                url = f"{CALENDAR_API_BASE}/{cal_id_encoded}/events"
                resp = client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    formatted = _format_event(item, cal, include_all_day)
                    if formatted:
                        events.append(formatted)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{cal['name']}: {exc}")

    events.sort(key=lambda e: e["start"] or "")

    return {
        "events": events,
        "error": "; ".join(errors) if errors else None,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def run(tool_input: dict[str, Any]) -> dict[str, Any]:
    return get_calendar_events(
        include_all_day=tool_input.get("include_all_day", True)
    )
