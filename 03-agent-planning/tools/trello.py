"""
Trello tool — Agent Planning Matinal.

Lit les cartes du sprint courant et du backlog TASKS.
Peut ajouter le label TODAY (rouge) aux cartes sélectionnées.

Variables d'environnement requises :
  TRELLO_API_KEY
  TRELLO_TOKEN
  TRELLO_BOARD_ID
"""

import os
import re
from datetime import date
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TRELLO_BASE = "https://api.trello.com/1"
TODAY_LABEL_ID = "69e12cf7a20af31e0472d93f"  # label rouge "TODAY" du board

# ---------------------------------------------------------------------------
# Définitions des outils Anthropic (passés dans tools=[...])
# ---------------------------------------------------------------------------

TOOL_DEFINITION: dict[str, Any] = {
    "name": "get_trello_tasks",
    "description": (
        "Lit les cartes du sprint courant et du backlog TASKS sur Trello. "
        "Détecte automatiquement le sprint actif selon la date du jour. "
        "Retourne pour chaque carte : nom, liste d'origine, labels (epic/thème), "
        "et métadonnées [P|T|CL|S] parsées depuis la description."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "include_backlog": {
                "type": "boolean",
                "description": "Inclure les cartes du backlog TASKS (défaut : true).",
            }
        },
        "required": [],
    },
}

ADD_LABEL_TOOL_DEFINITION: dict[str, Any] = {
    "name": "add_today_label",
    "description": (
        "Ajoute le label rouge TODAY sur une carte Trello pour marquer "
        "les tâches sélectionnées pour la journée. "
        "Ne déplace pas la carte — elle reste dans sa liste."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "card_id": {
                "type": "string",
                "description": "L'identifiant Trello de la carte (champ 'id').",
            }
        },
        "required": ["card_id"],
    },
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _auth() -> dict[str, str]:
    return {
        "key": os.environ["TRELLO_API_KEY"],
        "token": os.environ["TRELLO_TOKEN"],
    }

# ---------------------------------------------------------------------------
# Parsing des dates de sprint
# Formats supportés :
#   "SPRINT 6 - 17→23.05"        → même mois
#   "SPRINT 3 - 26.04→02.05"     → croise un mois
# ---------------------------------------------------------------------------

def _parse_sprint_dates(name: str, year: int | None = None) -> tuple[date, date] | None:
    if year is None:
        year = date.today().year

    # Format DD.MM→DD.MM (croise un mois)
    m = re.search(r"(\d{1,2})\.(\d{2})→(\d{1,2})\.(\d{2})", name)
    if m:
        sd, sm, ed, em = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        start = date(year, sm, sd)
        end_year = year + 1 if em < sm else year
        end = date(end_year, em, ed)
        return start, end

    # Format DD→DD.MM (même mois)
    m = re.search(r"(\d{1,2})→(\d{1,2})\.(\d{2})", name)
    if m:
        sd, ed, month = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(year, month, sd), date(year, month, ed)

    return None


def _find_current_sprint(lists: list[dict]) -> dict | None:
    """Retourne la liste dont les dates encadrent aujourd'hui."""
    today = date.today()
    candidates = []
    for lst in lists:
        if not lst["name"].upper().startswith("SPRINT"):
            continue
        parsed = _parse_sprint_dates(lst["name"])
        if parsed and parsed[0] <= today <= parsed[1]:
            candidates.append((parsed[0], lst))
    if not candidates:
        return None
    # Si plusieurs matchent (peu probable), prendre le plus récent
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]

# ---------------------------------------------------------------------------
# Parsing des métadonnées [P|T|CL|S]
# Exemple dans la description : "[P0|Deep|Low|M]"
# ---------------------------------------------------------------------------

META_RE = re.compile(
    r"\[(?P<priority>P\d)"
    r"\s*\|\s*(?P<type>[^|]+?)"
    r"\s*\|\s*(?P<cl>[^|]+?)"
    r"\s*\|\s*(?P<size>[^\]]+?)\]",
    re.IGNORECASE,
)


def _parse_metadata(description: str | None) -> dict[str, str] | None:
    if not description:
        return None
    m = META_RE.search(description)
    if not m:
        return None
    return {
        "priority": m.group("priority").strip().upper(),
        "type": m.group("type").strip(),
        "cognitive_load": m.group("cl").strip(),
        "size": m.group("size").strip().upper(),
    }

# ---------------------------------------------------------------------------
# Lecture des cartes
# ---------------------------------------------------------------------------

def _fetch_cards(client: httpx.Client, list_id: str) -> list[dict]:
    resp = client.get(
        f"{TRELLO_BASE}/lists/{list_id}/cards",
        params={**_auth(), "fields": "id,name,desc,labels,url,due,idList,dueComplete"},
    )
    resp.raise_for_status()
    return resp.json()


def _simplify_card(card: dict, list_name: str) -> dict | None:
    # Ignorer les cartes marquées comme achevées (coche verte sur Trello)
    if card.get("dueComplete", False):
        return None

    label_names = [lbl.get("name") or lbl.get("color", "") for lbl in card.get("labels", [])]
    has_today = any(lbl.get("id") == TODAY_LABEL_ID for lbl in card.get("labels", []))
    metadata = _parse_metadata(card.get("desc"))

    result = {
        "id": card["id"],
        "name": card["name"],
        "list": list_name,
        "labels": label_names,
        "has_today": has_today,
        "url": card.get("url"),
    }
    if metadata:
        result["meta"] = metadata
    else:
        result["meta"] = None
        result["desc_excerpt"] = (card.get("desc") or "")[:200]

    return result


def _find_past_sprints(lists: list[dict], current_sprint_id: str, max_sprints: int = 2) -> list[dict]:
    """Retourne les N sprints précédents ayant des dates parsées."""
    today = date.today()
    past = []
    for lst in lists:
        if lst["id"] == current_sprint_id:
            continue
        if not lst["name"].upper().startswith("SPRINT"):
            continue
        parsed = _parse_sprint_dates(lst["name"])
        if parsed and parsed[1] < today:  # sprint terminé
            past.append((parsed[1], lst))
    past.sort(key=lambda x: x[0], reverse=True)
    return [lst for _, lst in past[:max_sprints]]


def get_trello_tasks(include_backlog: bool = True) -> dict[str, Any]:
    board_id = os.environ.get("TRELLO_BOARD_ID", "")
    if not board_id:
        return {"sprint": None, "cards": [], "error": "TRELLO_BOARD_ID non configuré"}

    try:
        with httpx.Client(timeout=15) as client:
            # Récupérer toutes les listes du board
            lists_resp = client.get(
                f"{TRELLO_BASE}/boards/{board_id}/lists",
                params={**_auth(), "fields": "id,name"},
            )
            lists_resp.raise_for_status()
            all_lists = lists_resp.json()

            # Trouver le sprint courant
            sprint_list = _find_current_sprint(all_lists)
            if sprint_list is None:
                return {
                    "sprint": None,
                    "cards": [],
                    "error": "Aucun sprint actif trouvé pour la date du jour.",
                }

            # Trouver le backlog TASKS
            tasks_list = next(
                (lst for lst in all_lists if lst["name"].upper().startswith("TASKS")),
                None,
            )

            cards = []

            # Cartes des anciens sprints non achevées (reporte automatique)
            past_sprints = _find_past_sprints(all_lists, sprint_list["id"], max_sprints=2)
            for past in past_sprints:
                past_cards = _fetch_cards(client, past["id"])
                for card in past_cards:
                    simplified = _simplify_card(card, f"⚠️ Reporté ({past['name']})")
                    if simplified:
                        cards.append(simplified)

            # Cartes du sprint courant
            sprint_cards = _fetch_cards(client, sprint_list["id"])
            for card in sprint_cards:
                simplified = _simplify_card(card, sprint_list["name"])
                if simplified:
                    cards.append(simplified)

            # Backlog TASKS
            if include_backlog and tasks_list:
                backlog_cards = _fetch_cards(client, tasks_list["id"])
                for card in backlog_cards:
                    simplified = _simplify_card(card, tasks_list["name"])
                    if simplified:
                        cards.append(simplified)

            return {
                "sprint": sprint_list["name"],
                "cards": cards,
                "error": None,
            }

    except httpx.HTTPStatusError as exc:
        return {"sprint": None, "cards": [], "error": f"Erreur Trello {exc.response.status_code}"}
    except Exception as exc:  # noqa: BLE001
        return {"sprint": None, "cards": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Ajout du label TODAY
# ---------------------------------------------------------------------------

def add_today_label(card_id: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{TRELLO_BASE}/cards/{card_id}/idLabels",
                params={**_auth(), "value": TODAY_LABEL_ID},
            )
            resp.raise_for_status()
            return {"success": True, "card_id": card_id}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"Erreur Trello {exc.response.status_code}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Dispatchers appelés par main.py
# ---------------------------------------------------------------------------

def run(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Dispatcher pour get_trello_tasks."""
    return get_trello_tasks(
        include_backlog=tool_input.get("include_backlog", True)
    )


def run_add_label(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Dispatcher pour add_today_label."""
    return add_today_label(card_id=tool_input["card_id"])
