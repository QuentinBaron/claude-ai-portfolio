"""NudiChat Backend — Flask + Server-Sent Events
Déploiement : Railway (voir README.md)
"""
import os
import json
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import anthropic

app = Flask(__name__)

CORS(app, origins=[
    "https://quentinbaron.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "null",  # file:// local dev
])

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_BASE = """Tu es NudiChat, l'assistant du Nudidex — base de données des nudibranches de Polynésie Française (423 espèces indexées).

Tu aides les plongeurs, naturalistes et scientifiques à :
- Identifier des nudibranches depuis des observations de terrain
- Comprendre la taxonomie et la biologie des espèces
- Distinguer des espèces similaires (critères discriminants morphologiques)
- Interpréter des descriptions et termes anatomiques (notoum, cerates, rhinophores, branchies, etc.)

Ton style : précis et scientifique, mais accessible. Priorité au contexte espèces fourni.
Si tu n'es pas certain d'une identification, dis-le clairement. Ne confonds pas des espèces similaires.
Réponds en français par défaut, en anglais si la question est en anglais."""


def build_system_prompt(species_context: list) -> str:
    if not species_context:
        return SYSTEM_BASE

    lines = [SYSTEM_BASE, "\n\n## Espèces en contexte (Polynésie Française — données Nudidex)\n"]
    for sp in species_context[:5]:
        line = f"\n**{sp.get('n', '?')}** (slug: `{sp.get('s', '')}`)"
        if sp.get("o"):
            line += f" | Ordre : {sp['o']}"
        if sp.get("f"):
            line += f" | Famille : {sp['f']}"
        if sp.get("t"):
            line += f" | Taille : {sp['t']}"
        if sp.get("l"):
            line += f" | Localisation : {sp['l']}"
        if sp.get("d"):
            line += f"\n  Description : {sp['d'][:400]}"
        lines.append(line)

    return "".join(lines)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "nudidex-chat"})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    species_context = data.get("species") or []
    history = data.get("history") or []  # [{role, content}, ...]

    # Reconstruit les messages avec historique (max 3 turns = 6 messages)
    messages = []
    for msg in history[-6:]:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    def generate():
        try:
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=build_system_prompt(species_context),
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'error': 'API key invalide — vérifier ANTHROPIC_API_KEY'})}\n\n"
        except anthropic.RateLimitError:
            yield f"data: {json.dumps({'error': 'Limite de requêtes atteinte, réessaie dans quelques secondes.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
