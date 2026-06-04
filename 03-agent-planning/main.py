"""
Agent Planning Matinal — point d'entrée.

Lit les tâches Trello, les événements Google Calendar et les emails Gmail,
puis demande à Claude de produire un plan de journée priorisé.

Usage :
    python main.py                          # mode interactif (CLI)
    python main.py --focus bon              # mode launcher (pas d'input())
    python main.py --focus moyen --constraints "réunion 14h" --extra "appel médecin"

Variables d'environnement requises :
    ANTHROPIC_API_KEY
    TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID
    GOOGLE_CREDENTIALS_FILE
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic

# Fallback credentials Google : si la variable d'env est absente ou pointe vers
# un fichier inexistant, on cherche google_credentials.json dans le même dossier.
_creds_env = os.environ.get("GOOGLE_CREDENTIALS_FILE", "")
if not _creds_env or not Path(_creds_env).exists():
    _creds_local = Path(__file__).parent / "google_credentials.json"
    if _creds_local.exists():
        os.environ["GOOGLE_CREDENTIALS_FILE"] = str(_creds_local)

from prompts.system import SYSTEM_PROMPT
from tools import calendar, gmail, trello

# Fichier de persistance entre les deux phases
TODAY_PLAN_FILE = Path(__file__).parent / "today_plan.json"

# ---------------------------------------------------------------------------
# Registre des outils — phase PLAN uniquement (pas de write en phase 1)
# ---------------------------------------------------------------------------

TOOLS = [
    trello.TOOL_DEFINITION,
    calendar.TOOL_DEFINITION,
    gmail.TOOL_DEFINITION,
]

TOOL_RUNNERS = {
    "get_trello_tasks": trello.run,
    "get_calendar_events": calendar.run,
    "get_gmail_threads": gmail.run,
}

# ---------------------------------------------------------------------------
# Input utilisateur au lancement
# ---------------------------------------------------------------------------

FOCUS_OPTIONS = {
    "1": "faible",
    "2": "moyen",
    "3": "bon",
    "4": "élevé",
}


def get_user_input() -> dict:
    """Demande à l'utilisateur son niveau de focus et ses contraintes du jour."""
    print("\n" + "=" * 60)
    print("  AGENT PLANNING MATINAL")
    print("=" * 60)

    print("\nNiveau de focus aujourd'hui ?")
    print("  1 — Faible   2 — Moyen   3 — Bon   4 — Élevé")
    while True:
        choice = input("→ ").strip()
        if choice in FOCUS_OPTIONS:
            focus = FOCUS_OPTIONS[choice]
            break
        print("Saisis 1, 2, 3 ou 4.")

    print("\nContraintes particulières du jour ? (Entrée pour aucune)")
    constraints = input("→ ").strip()

    print("\nTâches hors Trello à intégrer ? (Entrée pour aucune)")
    extra_tasks = input("→ ").strip()

    return {
        "focus": focus,
        "constraints": constraints or None,
        "extra_tasks": extra_tasks or None,
    }


# ---------------------------------------------------------------------------
# Construction du message utilisateur
# ---------------------------------------------------------------------------

def build_user_message(user_input: dict) -> str:
    tz = ZoneInfo("Europe/Paris")
    now = datetime.now(tz)

    # Jour en français
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    today_str = f"{jours[now.weekday()]} {now.day} {mois[now.month - 1]} {now.year}"

    lines = [
        f"Nous sommes le {today_str}. Il est {now.strftime('%H:%M')}.",
        f"Niveau de focus déclaré : **{user_input['focus']}**.",
    ]

    if user_input["constraints"]:
        lines.append(f"Contraintes du jour : {user_input['constraints']}")

    if user_input["extra_tasks"]:
        lines.append(f"Tâches hors Trello à intégrer : {user_input['extra_tasks']}")

    lines.append(
        "\nProduis mon planning de la journée en suivant ta séquence d'exécution : "
        "lis d'abord Trello, Calendar et Gmail, puis génère le plan, "
        "applique les labels TODAY, et envoie-moi le digest par email à qb.baron@gmail.com."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Boucle agentique
# ---------------------------------------------------------------------------

def run_agent(user_input: dict) -> str:
    client = anthropic.Anthropic()

    user_message = build_user_message(user_input)
    messages: list[dict] = [{"role": "user", "content": user_message}]

    # Mise en cache du prompt système (économie de tokens sur les relances)
    system_with_cache = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    print(f"\n[agent] Démarrage — focus {user_input['focus']}\n")

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=system_with_cache,
            tools=TOOLS,
            messages=messages,
        )

        # Ajouter la réponse complète à l'historique (préserve les blocs tool_use)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = next(
                (block.text for block in response.content if block.type == "text"),
                "",
            )
            return final_text

        if response.stop_reason != "tool_use":
            return f"[agent] Stop inattendu : {response.stop_reason}"

        # Exécuter chaque outil demandé par Claude
        tool_results: list[dict] = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input
            print(f"[tool] {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")

            runner = TOOL_RUNNERS.get(tool_name)
            if runner is None:
                result = {"error": f"Outil inconnu : {tool_name}"}
            else:
                try:
                    result = runner(tool_input)
                except Exception as exc:  # noqa: BLE001
                    result = {"error": str(exc)}

            preview = json.dumps(result, ensure_ascii=False)[:150]
            print(f"       → {preview}…\n")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

        # Renvoyer les résultats à Claude
        messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def apply_plan() -> None:
    """Phase 2 : applique les labels TODAY et envoie l'email — sans Claude."""
    if not TODAY_PLAN_FILE.exists():
        print("[apply] Aucun plan trouvé. Lance d'abord le planning.")
        return

    data = json.loads(TODAY_PLAN_FILE.read_text(encoding="utf-8"))
    card_ids: list[str] = data.get("cards_to_label", [])
    plan_text: str = data.get("plan_text", "")
    subject: str = data.get("email_subject", "[Planning] Digest matinal")

    print(f"[apply] Application des labels TODAY sur {len(card_ids)} carte(s)...")
    for card_id in card_ids:
        result = trello.add_today_label(card_id)
        status = "✅" if result.get("success") else "❌"
        print(f"  {status} {card_id}")

    print("[apply] Envoi de l'email...")
    result = gmail.send_email(
        to="qb.baron@gmail.com",
        subject=subject,
        body=plan_text,
    )
    if result.get("success"):
        print("[apply] Email envoyé.")
    else:
        print(f"[apply] Erreur email : {result.get('error')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Planning Matinal")
    parser.add_argument("--focus", type=str, choices=["faible", "moyen", "bon", "élevé"], default=None)
    parser.add_argument("--constraints", type=str, default=None)
    parser.add_argument("--extra", type=str, default=None)
    parser.add_argument("--mode", type=str, choices=["plan", "apply"], default="plan")
    args = parser.parse_args()

    if args.mode == "apply":
        apply_plan()
        return

    if args.focus:
        user_input = {
            "focus": args.focus,
            "constraints": args.constraints or None,
            "extra_tasks": args.extra or None,
        }
    else:
        user_input = get_user_input()

    plan = run_agent(user_input)

    # Extraire CARDS_TO_LABEL de la dernière ligne
    cards_to_label: list[str] = []
    lines = plan.splitlines()
    clean_lines = []
    for line in lines:
        m = re.match(r"^CARDS_TO_LABEL:(.*)$", line.strip())
        if m:
            raw = m.group(1).strip()
            cards_to_label = [c.strip() for c in raw.split(",") if c.strip()]
        else:
            clean_lines.append(line)
    plan_clean = "\n".join(clean_lines).strip()

    # Construire le sujet de l'email
    tz = ZoneInfo("Europe/Paris")
    now = datetime.now(tz)
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month - 1]}"
    focus = user_input.get("focus", "")
    subject = f"[Planning] {date_str} — Focus {focus}"

    # Sauvegarder pour la phase apply
    TODAY_PLAN_FILE.write_text(
        json.dumps({
            "cards_to_label": cards_to_label,
            "plan_text": plan_clean,
            "email_subject": subject,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("  PLANNING DU JOUR")
    print("=" * 60)
    print(plan_clean)
    if cards_to_label:
        print(f"\n[plan] {len(cards_to_label)} carte(s) prête(s) pour label TODAY.")
    else:
        print("\n[plan] Aucune carte à labelliser détectée.")


if __name__ == "__main__":
    main()
