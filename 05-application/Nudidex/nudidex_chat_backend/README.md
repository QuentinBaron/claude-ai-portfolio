# NudiChat Backend

Flask + SSE backend pour le chat IA du Nudidex. Déployé sur Railway.

## Déploiement Railway

### 1. Créer le service

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Sélectionner `quentinbaron/claude-ai-portfolio`
3. **Root Directory** : `05-application/Nudidex/nudidex_chat_backend`
4. Railway détecte automatiquement le `Procfile`

### 2. Variable d'environnement

Dans Railway → Variables → Add :

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. URL publique

Railway génère une URL type `https://nudidex-chat-production.up.railway.app`.

Copier cette URL dans `nudis_template_v2.html` :

```js
var NUDIDEX_CHAT_URL = 'https://TON-SERVICE.up.railway.app/chat';
```

## Développement local

```bash
cd nudidex_chat_backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python app.py
# → http://localhost:5000
```

Test rapide :

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Quelle est la différence entre Chromodoris et Hypselodoris ?"}'
```

## Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | Chat SSE streaming |

### POST /chat — corps JSON

```json
{
  "message": "Question de l'utilisateur",
  "species": [
    { "n": "Chromodoris annae", "o": "Doridida", "f": "Chromodorididae", "t": "30mm" }
  ],
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

`species` : jusqu'à 5 espèces candidates injectées en contexte système (optionnel).  
`history` : jusqu'à 6 derniers messages pour le suivi de conversation (optionnel).

### Réponse SSE

```
data: {"text": "Chrome"}
data: {"text": "odoris"}
data: [DONE]
```

En cas d'erreur : `data: {"error": "message"}`

## Modèle

`claude-haiku-4-5-20251001` — ~$0.001/requête avec contexte 5 espèces.
