"""
Gmail tool — Agent Planning Matinal.

Lit les threads récents de l'inbox (derniers N jours).
Peut envoyer un email (digest matinal).

Utilise httpx pour les appels API + google-auth-oauthlib pour OAuth.
Même pattern que calendar.py — token Gmail séparé (scopes différents).

Variables d'environnement :
  GOOGLE_CREDENTIALS_FILE  — chemin vers le fichier OAuth JSON (depuis GCP)
  GOOGLE_TOKEN_GMAIL_FILE  — (optionnel) chemin pour le token Gmail
"""

import base64
import os
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# ---------------------------------------------------------------------------
# Définitions des outils Anthropic
# ---------------------------------------------------------------------------

TOOL_DEFINITION: dict[str, Any] = {
    "name": "get_gmail_threads",
    "description": (
        "Lit les threads Gmail récents de l'inbox (2 derniers jours par défaut). "
        "Retourne pour chaque thread : sujet, expéditeur, extrait, date, labels "
        "(UNREAD, STARRED, IMPORTANT). Utile pour identifier les emails nécessitant "
        "une action ce jour."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "days_back": {
                "type": "integer",
                "description": "Nombre de jours en arrière à lire (défaut : 2).",
            },
            "max_results": {
                "type": "integer",
                "description": "Nombre maximum de threads à retourner (défaut : 15).",
            },
            "unread_only": {
                "type": "boolean",
                "description": "Ne retourner que les threads non lus (défaut : false).",
            },
        },
        "required": [],
    },
}

SEND_EMAIL_TOOL_DEFINITION: dict[str, Any] = {
    "name": "send_email",
    "description": (
        "Envoie un email via Gmail. Utilisé pour envoyer le digest matinal "
        "ou toute autre communication par email."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Adresse email du destinataire.",
            },
            "subject": {
                "type": "string",
                "description": "Sujet de l'email.",
            },
            "body": {
                "type": "string",
                "description": "Corps de l'email (texte brut).",
            },
        },
        "required": ["to", "subject", "body"],
    },
}

# ---------------------------------------------------------------------------
# Auth OAuth 2.0 (même pattern que calendar.py, token séparé)
# ---------------------------------------------------------------------------

def _get_credentials():
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

    # Token Gmail séparé pour ne pas écraser le token calendar
    token_file = os.environ.get(
        "GOOGLE_TOKEN_GMAIL_FILE",
        os.path.join(os.path.dirname(credentials_file), "google_token_gmail.json"),
    )

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return creds


def _get_token() -> str:
    from google.auth.transport.requests import Request
    creds = _get_credentials()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        credentials_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "")
        token_file = os.environ.get(
            "GOOGLE_TOKEN_GMAIL_FILE",
            os.path.join(os.path.dirname(credentials_file), "google_token_gmail.json"),
        )
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return creds.token

# ---------------------------------------------------------------------------
# Filtrage des emails système (alertes de connexion, notifications auto)
# ---------------------------------------------------------------------------

_NOISE_SENDERS = {
    "no-reply@accounts.google.com",
    "noreply@accounts.google.com",
    "noreply@github.com",
    "no-reply@github.com",
    "do-not-reply@trello.com",
    "noreply@trello.com",
}

_NOISE_SUBJECT_KEYWORDS = [
    "alerte de sécurité",
    "security alert",
    "verify your device",
    "please verify",
    "sign-in attempt",
    "sign in attempt",
    "nouvelle connexion",
    "new sign",
    "suspicious sign",
    "nouvelle application autorisée",
    "account alert",
]


def _is_noise(thread_detail: dict) -> bool:
    """Retourne True si le thread est une alerte système à ignorer."""
    sender = thread_detail.get("from", "").lower()
    subject = thread_detail.get("subject", "").lower()

    if any(ns in sender for ns in _NOISE_SENDERS):
        return True
    if any(kw in subject for kw in _NOISE_SUBJECT_KEYWORDS):
        return True
    return False


# ---------------------------------------------------------------------------
# Lecture des threads
# ---------------------------------------------------------------------------

def _get_thread_detail(client: httpx.Client, headers: dict, thread_id: str) -> dict:
    """Récupère le détail d'un thread : sujet, expéditeur, extrait, labels."""
    resp = client.get(
        f"{GMAIL_API_BASE}/threads/{thread_id}",
        headers=headers,
        params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
    )
    resp.raise_for_status()
    data = resp.json()

    messages = data.get("messages", [])
    if not messages:
        return {}

    first_msg = messages[0]
    headers_list = first_msg.get("payload", {}).get("headers", [])
    headers_map = {h["name"]: h["value"] for h in headers_list}

    label_ids = set()
    for msg in messages:
        label_ids.update(msg.get("labelIds", []))

    snippet = first_msg.get("snippet", "")

    return {
        "id": thread_id,
        "subject": headers_map.get("Subject", "(sans sujet)"),
        "from": headers_map.get("From", ""),
        "date": headers_map.get("Date", ""),
        "snippet": snippet[:200] if snippet else "",
        "unread": "UNREAD" in label_ids,
        "starred": "STARRED" in label_ids,
        "important": "IMPORTANT" in label_ids,
        "message_count": len(messages),
    }


def get_gmail_threads(
    days_back: int = 2,
    max_results: int = 8,
    unread_only: bool = True,
) -> dict[str, Any]:
    try:
        token = _get_token()
    except Exception as exc:
        return {"threads": [], "error": f"Auth error: {exc}"}

    headers = {"Authorization": f"Bearer {token}"}

    # Filtre : inbox des N derniers jours
    after_ts = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())
    query = f"in:inbox after:{after_ts}"
    if unread_only:
        query += " is:unread"

    threads: list[dict] = []
    errors: list[str] = []

    try:
        with httpx.Client(timeout=30) as client:
            # Liste des threads
            resp = client.get(
                f"{GMAIL_API_BASE}/threads",
                headers=headers,
                params={
                    "q": query,
                    "maxResults": max_results,
                },
            )
            resp.raise_for_status()
            thread_list = resp.json().get("threads", [])

            # Détail de chaque thread
            for t in thread_list:
                try:
                    detail = _get_thread_detail(client, headers, t["id"])
                    if detail and not _is_noise(detail):
                        threads.append(detail)
                except Exception as exc:
                    errors.append(f"Thread {t['id']}: {exc}")

    except Exception as exc:
        return {"threads": [], "error": str(exc)}

    # Priorité : starred > important > unread
    threads.sort(key=lambda t: (
        not t.get("starred", False),
        not t.get("important", False),
        not t.get("unread", False),
    ))

    return {
        "threads": threads,
        "error": "; ".join(errors) if errors else None,
    }

# ---------------------------------------------------------------------------
# Envoi d'email (digest)
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    try:
        token = _get_token()
    except Exception as exc:
        return {"success": False, "error": f"Auth error: {exc}"}

    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{GMAIL_API_BASE}/messages/send",
                headers={"Authorization": f"Bearer {token}"},
                json={"raw": raw},
            )
            resp.raise_for_status()
            return {"success": True, "message_id": resp.json().get("id")}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"Erreur Gmail {exc.response.status_code}: {exc.response.text}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

# ---------------------------------------------------------------------------
# Dispatchers
# ---------------------------------------------------------------------------

def run(tool_input: dict[str, Any]) -> dict[str, Any]:
    return get_gmail_threads(
        days_back=tool_input.get("days_back", 2),
        max_results=tool_input.get("max_results", 15),
        unread_only=tool_input.get("unread_only", False),
    )


def run_send(tool_input: dict[str, Any]) -> dict[str, Any]:
    return send_email(
        to=tool_input["to"],
        subject=tool_input["subject"],
        body=tool_input["body"],
    )
