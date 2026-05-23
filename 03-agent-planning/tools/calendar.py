"""
Google Calendar tool — Agent Planning Matinal.

Lit les événements du jour depuis tous les agendas pertinents.
Applique la logique de comportement définie dans les specs :
  - Pro & autres (primary)  → impératif
  - Voyages & Sport         → impératif
  - Perso                   → important
  - Mathilde                → indirect (pharmacie → opportunité Deep Work)
  - Optionnel               → ignoré

Auth : OAuth 2.0 Desktop via InstalledAppFlow.
  1ère exécution : ouvre le navigateur pour consentement → enregistre google_token.json
  Exécutions suivantes : recharge le token automatiquement.

Variables d'environnement requises :
  GOOGLE_CREDENTIALS_FILE  — chemin vers le fichier credentials OAuth téléchargé depuis GCP
  GOOGLE_TOKEN_FILE        — (optionnel) chemin pour stocker le token, défaut : google_token.json
"""

import os
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Mapping agendas → comportement
# IDs récupérés via list_calendars (connecteur Cowork, 22/05/2026)
# ---------------------------------------------------------------------------

CALENDAR_CONFIG: list[dict[str, str]] = [
    {
        "id": "qb.baron@gmail.com",
        "name": "Pro & autres",
        "behavior": "mandatory",       # impératif — bloquer les créneaux
    },
    {
        "id": "m8iem642uehslto4b4vusq8a40@group.calendar.google.com",
        "name": "Voyages & Sport",
        "behavior": "mandatory",       # impératif
    },
    {
        "id": "b762r2e9otckhpujriotu7o4kg@group.calendar.google.com",
        "name": "Perso",
        "behavior": "important",       # important / souvent impératif
    },
    {
        "id": "dl9ohu6rmet7b416lv9e90m5bk@group.calendar.google.com",
        "name": "Mathilde",
        "behavior": "indirect",        # si pharmacie → suggérer Deep Work
    },
    # Optionnel (271m8e73oprfak85mtbfifl610) → non inclus (ignoré)
    # Pompiers / Optimhome → non inclus (hors specs)
]

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# ---------------------------------------------------------------------------
# Définition de l'outil Anthropic
# ---------------------------------------------------------------------------

TOOL_DEFINITION: dict[str, Any] = {
    "name": "get_calendar_events",
    "description": (
        "Récupère les événements Google Calendar du jour pour tous les agendas pertinents. "
        "Retourne pour chaque événement : titre, heure de début/fin, agenda d'origine, "
        "comportement (mandatory/important/indirect) et si c'est une opportunité Deep Work "
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
    - Si google_token.json existe et est valide → le recharge.
    - Sinon → ouvre le navigateur pour le consentement (1ère fois uniquement).
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise ImportError(
            "Installe les dépendances Google : "
            "pip install google-auth google-auth-oauthlib google-api-python-client"
        ) from exc

    credentials_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    if not credentials_file or not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"Fichier credentials introuvable : {credentials_file}\n"
            "Configure GOOGLE_CREDENTIALS_FILE avec le chemin vers ton fichier OAuth JSON."
        )

    token_file = os.environ.get(
        "GOOGLE_TOKEN_FILE",
        os.path.join(os.path.dirname(credentials_file), "google_token.json"),
    )

    creds = None

    # Recharger le token existant
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # Rafraîchir si expiré, ou lancer le flow si absent
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Sauvegarder pour les prochaines exécutions
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return creds


def _build_service():
    from googleapiclient.discovery import build
    creds = _get_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Lecture des événements
# ---------------------------------------------------------------------------

def _is_pharmacie(event: dict) -> bool:
    """Détecte si un événement Mathilde est un créneau pharmacie."""
    keywords = ["pharmacie", "pharma", "pharmacy"]
    text = (
        (event.get("summary") or "") + " " + (event.get("description") or "")
    ).lower()
    return any(kw in text for kw in keywords)


def _format_event(event: dict, calendar_config: dict, include_all_day: bool) -> dict | None:
    """Simplifie un événement brut en dict utilisable par Claude."""
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

    # Logique spéciale Mathilde : pharmacie → opportunité Deep Work
    if calendar_config["behavior"] == "indirect":
        result["deep_work_opportunity"] = _is_pharmacie(event)

    return result


def get_calendar_events(include_all_day: bool = True) -> dict[str, Any]:
    """
    Récupère les événements du jour depuis tous les agendas configurés.
    """
    try:
        service = _build_service()
    except Exception as exc:
        return {"events": [], "error": str(exc)}

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

    events: list[dict] = []
    errors: list[str] = []

    for cal in CALENDAR_CONFIG:
        try:
            result = (
                service.events()
                .list(
                    calendarId=cal["id"],
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            for item in result.get("items", []):
                formatted = _format_event(item, cal, include_all_day)
                if formatted:
                    events.append(formatted)

        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cal['name']}: {str(exc)}")

    # Trier par heure de début
    events.sort(key=lambda e: e["start"] or "")

    return {
        "events": events,
        "error": "; ".join(errors) if errors else None,
    }


# ---------------------------------------------------------------------------
# Dispatcher appelé par main.py
# ---------------------------------------------------------------------------

def run(tool_input: dict[str, Any]) -> dict[str, Any]:
    return get_calendar_events(
        include_all_day=tool_input.get("include_all_day", True)
    )
